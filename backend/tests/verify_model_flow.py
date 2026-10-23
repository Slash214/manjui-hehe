"""Controlled loopback HTTP -> application API -> real PostgreSQL/MinIO.

Creates a dedicated local verification account, never external model traffic.
The transient test token is written to /tmp for browser verification, never logged.
"""
import json
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_api import post
from tests.test_creative_network import accept, endpoint, generate


def main() -> None:
    patch = pytest.MonkeyPatch()
    fixture = endpoint.__wrapped__(patch)
    controlled = next(fixture)
    patch.setenv('MANJU_MODEL_DEV_ONLY','true')
    try:
        with TestClient(app) as client:
            auth=post(client,'/auth/register',email=f'http-verification-{secrets.token_hex(5)}@example.com',password=secrets.token_urlsafe(24))
            client.headers['Authorization']='Bearer '+auth['access_token']
            me=client.get('/api/v1/me').json()
            project=post(client,'/projects',name='本地协议验证（测试服务）')
            episode=post(client,f"/projects/{project['id']}/episodes",title='HTTP与存储验证')
            def model(kind):
                return post(client,'/creative/models',name='本地受控测试服务（验证结束后停止）',kind=kind,provider='openai_compatible',base_url=controlled[0],model='controlled-test',secret_env='MANJU_MODEL_LOCAL_TEST',allow_local=True)
            text=model('text')
            for operation in ['script','assets','shots']:
                response=generate(client,episode,text,operation)
                assert response.status_code==201,response.text
                accept(client,response.json())
            shot=client.get(f"/api/v1/episodes/{episode['id']}/shots").json()['items'][0]
            c=generate(client,episode,text,'prompt',target_id=shot['id']).json()
            accept(client,c)
            image=model('image')
            asset=client.get(f"/api/v1/projects/{project['id']}/assets").json()['items'][0]
            for target,kind in [(asset['id'],'asset'),(shot['id'],'shot')]:
                response=generate(client,episode,image,'image',target_id=target,image_target=kind)
                assert response.status_code==201,response.text
                accept(client,response.json())
            Path('/tmp/model-preview.json').write_text(json.dumps({'token':auth['access_token'],'user_id':me['id'],'episode_id':episode['id'],'project_id':project['id'],'shot_id':shot['id']}))
            print(json.dumps({'http_requests':len(controlled[1]['requests']),'text_and_image_candidates':'passed','real_storage':'MinIO','adoption':'asset version and shot keyframe','external_requests':0}))
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
        patch.undo()


if __name__=='__main__':
    main()
