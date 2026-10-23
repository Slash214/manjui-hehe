# ruff: noqa: F811
import json

import httpx
import pytest

from app.creative.providers import OpenAICompatible
from app.services.content import Problem
from tests.test_api import client, post  # noqa: F401


def setup(client):
    project = post(client, "/projects", name="创作测试")
    episode = post(client, f"/projects/{project['id']}/episodes", title="第一集")
    model = post(client, "/creative/models", name="演示文本", kind="text", provider="mock")
    return project, episode, model


def candidate(client, episode, model, operation, **extra):
    return post(client, f"/episodes/{episode['id']}/creative/candidates",
                model_config_id=model['id'], operation=operation, instruction="掌柜放下碗，沉默片刻。", **extra)


def adopt(client, item):
    return client.post(f"/api/v1/creative/candidates/{item['id']}/adopt", json={"base_version": item['version']})


def test_candidates_are_explicit_and_conflict_safe(client):
    project, ep, model = setup(client)
    c = candidate(client, ep, model, "script")
    assert client.get(f"/api/v1/episodes/{ep['id']}/script").json()['scenes'] == []
    assert c['provenance_json']['mock'] is True
    assert adopt(client, c).is_success
    assert adopt(client, c).status_code == 409
    scenes = client.get(f"/api/v1/episodes/{ep['id']}/script").json()['scenes']
    line = scenes[0]['lines'][0]
    c = candidate(client, ep, model, "dialogue", target_id=line['id'])
    assert adopt(client, c).is_success
    c = candidate(client, ep, model, "assets")
    assert adopt(client, c).is_success
    assert len(client.get(f"/api/v1/projects/{project['id']}/assets").json()['items']) == 1
    c = candidate(client, ep, model, "shots")
    assert adopt(client, c).is_success
    shot = client.get(f"/api/v1/episodes/{ep['id']}/shots").json()['items'][0]
    c = candidate(client, ep, model, "prompt", target_id=shot['id'])
    assert adopt(client, c).is_success
    changed = candidate(client, ep, model, "prompt", target_id=shot['id'])
    current = client.get(f"/api/v1/shots/{shot['id']}").json()
    assert client.patch(f"/api/v1/shots/{shot['id']}", json={"base_version":current['content_version'],"action_desc":"新动作"}).is_success
    assert adopt(client, changed).status_code == 409
    saved = client.get(f"/api/v1/episodes/{ep['id']}/creative/candidates").json()['items'][0]
    assert saved['output_json'] == changed['output_json']
    assert saved['approval_state'] == 'pending'


def test_model_security_ownership_and_image_boundary(client, monkeypatch):
    _, ep, _model = setup(client)
    for bad in ({"api_key":"do-not-accept"}, {"secret_env":"PATH"}, {"base_url":"http://169.254.169.254"}):
        r = client.post('/api/v1/creative/models', json={"name":"bad","kind":"text","provider":"openai_compatible","model":"test",**bad})
        assert r.status_code == 422
    config = post(client, '/creative/models', name='未配置', kind='text', provider='openai_compatible', base_url='https://example.com/v1', model='test',secret_env='MANJU_MODEL_TEST_ONLY')
    body={"model_config_id":config['id'],"operation":"script","instruction":"剧本"}
    assert client.post(f"/api/v1/episodes/{ep['id']}/creative/candidates",json=body).status_code == 503
    monkeypatch.setenv('MANJU_MODEL_TEST_ONLY','secret-never-returned')
    assert 'secret-never-returned' not in client.get('/api/v1/creative/models').text
    assert client.post(f"/api/v1/episodes/{ep['id']}/creative/candidates",json={**body,'actual_call':True}).status_code == 403
    image=post(client,'/creative/models',name='图片演示',kind='image',provider='mock')
    c=candidate(client,ep,image,'image')
    assert c['output_json']['media_created'] is False
    assert adopt(client,c).status_code==422
    assert client.post(f"/api/v1/episodes/{ep['id']}/creative/candidates",json={**body,'extra':'reject'}).status_code==422
    second=post(client,'/auth/register',email='other@example.com',password='password123')
    client.headers['Authorization']='Bearer '+second['access_token']
    assert client.get(f"/api/v1/episodes/{ep['id']}/creative/candidates").status_code==404
    assert adopt(client,c).status_code==404
    assert client.get('/api/v1/creative/models').json()['items']==[]


def test_protocol_mapping_output_validation_and_errors():
    seen=[]
    def handler(request):
        seen.append(json.loads(request.content))
        if request.url.path.endswith('images/generations'):
            return httpx.Response(200,json={'data':[{'b64_json':'test-placeholder'}]})
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"text":"有效结果"}'}}]})
    provider=OpenAICompatible('https://example.com/v1','test-model','mock-token',httpx.MockTransport(handler))
    assert provider.generate('prompt','test',{})=={'text':'有效结果'}
    assert 'data' in provider.generate_image('test')
    assert seen[0]['model']=='test-model' and seen[1]['n']==1
    bad=OpenAICompatible('https://example.com/v1','model','token',httpx.MockTransport(lambda _:httpx.Response(200,json={'choices':[{'message':{'content':'{"text":"x","unexpected":true}'}}]})))
    with pytest.raises(Problem) as error:
        bad.generate('prompt','test',{})
    assert error.value.code=='INVALID_MODEL_OUTPUT'
    fail=OpenAICompatible('https://example.com/v1','model','token',httpx.MockTransport(lambda _:httpx.Response(401,json={'error':'private detail'})))
    with pytest.raises(Problem) as error:
        fail.generate('prompt','test',{})
    assert error.value.code=='PROVIDER_ERROR'
