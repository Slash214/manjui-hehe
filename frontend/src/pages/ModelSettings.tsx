import {useNavigate} from 'react-router-dom';
import {useState} from 'react';
import {Action,useList} from '../components/Common';
import {api} from '../api/client';
export function ModelSettings(){
 const navigate=useNavigate();
 const models=useList('/creative/models');
 const [kind,setKind]=useState('text'),[provider,setProvider]=useState('openai_compatible'),[name,setName]=useState(''),[base,setBase]=useState(''),[model,setModel]=useState(''),[env,setEnv]=useState(''),[local,setLocal]=useState(false),[testMode,setTestMode]=useState(false);
 return <main className="page"><button onClick={()=>navigate(-1)}>返回</button><h1>模型设置</h1><label className="inline"><input type="checkbox" checked={testMode} onChange={e=>{setTestMode(e.target.checked);setProvider('openai_compatible');}}/>显示测试配置</label>
    <details className="panel" open><summary>模型配置</summary><div className="creative-config"><label>用途<select value={kind} onChange={e=>setKind(e.target.value)}><option value="text">文本模型</option><option value="image">生图模型</option></select></label><label>配置名称<input value={name} onChange={e=>setName(e.target.value)}/></label><label>协议<select aria-label="协议" value={provider} onChange={e=>setProvider(e.target.value)}>{testMode&&<option value="mock">测试 mock</option>}<option value="openai_compatible">OpenAI 兼容协议</option></select></label>{provider!=='mock'&&<><label>API 基础地址<input value={base} onChange={e=>setBase(e.target.value)} placeholder="https://provider.example/v1"/></label><label>模型标识<input value={model} onChange={e=>setModel(e.target.value)}/></label><label>服务端环境变量名<input value={env} onChange={e=>setEnv(e.target.value)} placeholder="MANJU_MODEL_TEXT_KEY"/></label><label className="inline"><input type="checkbox" checked={local} onChange={e=>setLocal(e.target.checked)}/>明确允许本地端点</label><p className="muted">只填写变量名，不填写 API 密钥。在服务端配置对应变量并开启调用开关。</p></>}<Action disabled={!name.trim()} run={async()=>{await api('/creative/models','POST',{name,kind,provider,base_url:provider==='mock'?'':base,model:provider==='mock'?'':model,secret_env:provider==='mock'?'':env,allow_local:local});setName('');}}>保存模型配置</Action></div>
      {models.data?.map(m=><div className="list-row" key={m.id}><span>{String(m.name)} / {m.kind==='text'?'文本':'图片'}</span><small>{m.provider==='mock'?'演示 mock':m.credential_configured?(m.live_enabled?'可实际调用':'密钥已配置 / 开关未开启'):'密钥未配置'}</small></div>)}</details>
<p>配置步骤：docs/MODEL-SETUP.md。密钥只在服务端设置，不填写在此页面。</p></main>;
}
