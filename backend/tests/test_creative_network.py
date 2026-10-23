# ruff: noqa: F811
import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

import pytest
from PIL import Image

from app.main import app
from app.providers.storage import MinioStorage, storage
from tests.test_api import client, post  # noqa: F401


@pytest.fixture
def endpoint(monkeypatch):
    state = {"requests": [], "status": 200, "mode": "valid"}
    output = BytesIO()
    Image.new('RGB', (32, 32), 'navy').save(output, format='PNG')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['requests'].append(body)
            if state['mode']=='timeout':
                time.sleep(1.5)
            self.send_response(state['status'])
            self.send_header('Content-Type','application/json')
            if state['mode']=='oversized':
                self.send_header('Content-Length',str(100*1024*1024))
            self.end_headers()
            if state['mode']=='oversized':
                return
            if self.path.endswith('images/generations'):
                data={'data':[{'b64_json':base64.b64encode(output.getvalue()).decode()}]}
                if state['mode']=='bad_base64':
                    data={'data':[{'b64_json':'%%%'}]}
                if state['mode']=='private_url':
                    data={'data':[{'url':'https://127.0.0.1/private'}]}
                if state['mode']=='bad_dimensions':
                    large=BytesIO()
                    Image.new('RGB',(8193,1)).save(large,format='PNG')
                    data={'data':[{'b64_json':base64.b64encode(large.getvalue()).decode()}]}
            else:
                system=body['messages'][0]['content']
                if '"scenes"' in system:
                    result={'scenes':[{'title':'真实协议返回的场次','lines':[{'text':'别急，先尝一口。','line_type':'dialogue'}]}]}
                elif '"assets"' in system:
                    result={'assets':[{'name':'掌柜','asset_type':'character','description':'克制的表情'}]}
                elif '"shots"' in system:
                    result={'shots':[{'action_desc':'掌柜放下碗','blocking_desc':'柜台前，面向来客','est_duration_ms':4000}]}
                else:
                    result={'text':'近景，掌柜放下碗，暖色侧光'}
                if state['mode']=='schema':
                    result={'unexpected':'bad'}
                data={'choices':[{'message':{'content':json.dumps(result,ensure_ascii=False)}}]}
            try:
                self.wfile.write(json.dumps(data).encode())
            except (BrokenPipeError,ConnectionResetError):
                pass

    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    authority=f'127.0.0.1:{server.server_port}'
    monkeypatch.setenv('MANJU_MODEL_NETWORK_ENABLED','true')
    monkeypatch.setenv('MANJU_MODEL_DEV_AUTHORITIES',authority)
    monkeypatch.setenv('MANJU_MODEL_LOCAL_TEST','local-test-only-not-a-provider-key')
    monkeypatch.setenv('MANJU_MODEL_TIMEOUT_SEC','1')
    yield 'http://'+authority+'/v1',state
    server.shutdown()
    server.server_close()


def arrange(client, endpoint, kind='text'):
    project=post(client,'/projects',name='HTTP协议验证')
    ep=post(client,f"/projects/{project['id']}/episodes",title='第一集')
    model=post(client,'/creative/models',name='本地受控HTTP',kind=kind,provider='openai_compatible',
               model='controlled-test',base_url=endpoint[0],allow_local=True,secret_env='MANJU_MODEL_LOCAL_TEST')
    return project,ep,model


def generate(client,ep,model,operation,**extra):
    return client.post(f"/api/v1/episodes/{ep['id']}/creative/candidates",json={
        'model_config_id':model['id'],'operation':operation,'instruction':'请根据本集内容创作',
        'actual_call':True,**extra})


def accept(client,c):
    response=client.post(f"/api/v1/creative/candidates/{c['id']}/adopt",json={'base_version':c['version']})
    assert response.is_success,response.text


def test_real_transport_templates_and_adoption(client,endpoint):
    _,ep,model=arrange(client,endpoint)
    for operation,source in [('script','screenwriting'),('assets','manju'),('shots','manju')]:
        response=generate(client,ep,model,operation)
        assert response.status_code==201,response.text
        candidate=response.json()
        assert candidate['provenance_json']['mock'] is False
        assert candidate['provenance_json']['id']==source
        if operation=='script':
            revised=client.post(f"/api/v1/creative/candidates/{candidate['id']}/revise",json={
                'base_version':candidate['version'],'output':{'scenes':[{'title':'人工调整','lines':[{'text':'请坐。','line_type':'dialogue'}]}]}})
            assert revised.status_code==201,revised.text
            assert revised.json()['id']!=candidate['id']
            assert candidate['output_json']['scenes'][0]['title']=='真实协议返回的场次'
            candidate=revised.json()
        accept(client,candidate)
    shot=client.get(f"/api/v1/episodes/{ep['id']}/shots").json()['items'][0]
    candidate=generate(client,ep,model,'prompt',target_id=shot['id']).json()
    assert candidate['provenance_json']['id']=='visual'
    accept(client,candidate)
    line=client.get(f"/api/v1/episodes/{ep['id']}/script").json()['scenes'][0]['lines'][0]
    response=generate(client,ep,model,'dialogue',target_id=line['id'])
    assert response.status_code==201,response.text
    accept(client,response.json())
    requests=endpoint[1]['requests']
    assert len(requests)==5
    assert all(r['model']=='controlled-test' and r['response_format']=={'type':'json_object'} for r in requests)
    assert '阻力' in requests[0]['messages'][0]['content']
    assert '实体身份' in requests[1]['messages'][0]['content']
    assert '站位' in requests[2]['messages'][0]['content']
    assert '参考图编号' in requests[3]['messages'][0]['content']
    assert 'snapshot' not in requests[0]['messages'][1]['content']  # payload carries actual input object
    assert 'episode' in requests[0]['messages'][1]['content']


def test_image_transport_storage_versions_and_keyframe(client,endpoint):
    if os.getenv('TEST_REAL_STORAGE')=='true':
        app.dependency_overrides[storage]=MinioStorage
    project,ep,model=arrange(client,endpoint,'image')
    asset=post(client,f"/projects/{project['id']}/assets",name='掌柜',asset_type='character')
    old=post(client,f"/assets/{asset['id']}/versions",base_version=1,description='原版本')
    first=generate(client,ep,model,'image',target_id=asset['id'],image_target='asset')
    assert first.status_code==201,first.text
    c=first.json()
    assert c['output_json']['file_id'] and not c['output_json']['mock']
    assert client.get(f"/api/v1/assets/{asset['id']}").json()['current_version_id']==old['id']
    accept(client,c)
    versions=client.get(f"/api/v1/assets/{asset['id']}/versions").json()['items']
    assert len(versions)==2 and versions[0]['reference_file_id'] is None
    link=client.get(f"/api/v1/files/{c['output_json']['file_id']}/url")
    assert link.status_code==200 and link.json()['expires_in']==3600
    shot=post(client,f"/episodes/{ep['id']}/shots",action_desc='掌柜放碗')
    second=generate(client,ep,model,'image',target_id=shot['id'],image_target='shot').json()
    accept(client,second)
    current=client.get(f"/api/v1/shots/{shot['id']}").json()
    assert current['creative_keyframe_candidate_id']==second['id']
    stale=generate(client,ep,model,'image',target_id=shot['id'],image_target='shot').json()
    client.patch(f"/api/v1/shots/{shot['id']}",json={'base_version':current['content_version'],'action_desc':'改动'})
    assert client.post(f"/api/v1/creative/candidates/{stale['id']}/adopt",json={'base_version':1}).status_code==409
    other=post(client,'/projects',name='另一项目')
    foreign=post(client,f"/projects/{other['id']}/assets",name='不属于本集',asset_type='character')
    before=len(endpoint[1]['requests'])
    assert generate(client,ep,model,'image',target_id=foreign['id']).status_code==422
    assert len(endpoint[1]['requests'])==before


@pytest.mark.parametrize('status,mode,code',[(401,'valid','MODEL_AUTH'),(429,'valid','MODEL_RATE_LIMIT'),
    (500,'valid','PROVIDER_ERROR'),(302,'valid','MODEL_REDIRECT'),(200,'schema','INVALID_MODEL_OUTPUT'),
    (200,'timeout','MODEL_TIMEOUT'),(200,'oversized','RESPONSE_TOO_LARGE')])
def test_http_failures_no_retries(client,endpoint,status,mode,code):
    _,ep,model=arrange(client,endpoint)
    endpoint[1].update(status=status,mode=mode)
    response=generate(client,ep,model,'script')
    assert response.json()['code']==code,response.text
    assert len(endpoint[1]['requests'])==1
    assert client.get(f"/api/v1/episodes/{ep['id']}/creative/candidates").json()['items']==[]


@pytest.mark.parametrize('mode,code',[('bad_base64','INVALID_IMAGE'),('private_url','UNSAFE_ENDPOINT'),('oversized','RESPONSE_TOO_LARGE'),('bad_dimensions','INVALID_IMAGE')])
def test_image_rejections(client,endpoint,mode,code):
    project,ep,model=arrange(client,endpoint,'image')
    asset=post(client,f"/projects/{project['id']}/assets",name='目标',asset_type='location')
    endpoint[1]['mode']=mode
    response=generate(client,ep,model,'image',target_id=asset['id'])
    assert response.json()['code']==code,response.text
    assert len(endpoint[1]['requests'])==1


@pytest.mark.parametrize('ips',[['169.254.169.254'],['10.0.0.1'],['224.0.0.1'],['::1'],['8.8.8.8','127.0.0.1']])
def test_dns_targets_rejected_before_connect(monkeypatch,ips):
    from app.creative import network
    from app.services.content import Problem
    monkeypatch.setattr(network,'addresses',lambda *_:ips)
    with pytest.raises(Problem) as error:
        network.request_bytes('https://provider.example/v1')
    assert error.value.code=='UNSAFE_ENDPOINT'
