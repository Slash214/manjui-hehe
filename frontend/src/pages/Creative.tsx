import { CandidateEditor } from '../components/CandidateEditor';
import { FileImage } from '../components/FileImage';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Action, LoadError, useList, useObject } from '../components/Common';
import { api, Entity, Scene } from '../api/client';

const operations: Record<string,string>={script:'剧本草稿',dialogue:'对白改写',assets:'资产提取',shots:'镜头规划',prompt:'镜头提示词',image:'生成关键画面'};
const statuses:Record<string,string>={planning_adapted:'规划规则已适配',registered:'仅登记',registered_model_specific:'专用模型规划已登记',disabled_requires_provider_setup:'需服务配置',disabled_pending_security_review:'执行安全审查待完成',blocked_source_unavailable:'来源不可访问',pending_source_confirmation:'待确认来源'};
function CandidateContent({value}:{value:Record<string,unknown>}){
  const text=value.text??value.prompt;
  if(typeof text==='string')return <p className="creative-result">{text}</p>;
  const items=(value.scenes??value.assets??value.shots) as Record<string,unknown>[]|undefined;
  return <div className="creative-result">{items?.map((item,index)=><article key={index}><h3>{String(item.title??item.name??`镜头 ${index+1}`)}</h3>{typeof item.description==='string'&&<p>{item.description}</p>}{typeof item.action_desc==='string'&&<p>{item.action_desc}</p>}{typeof item.blocking_desc==='string'&&<p>{item.blocking_desc}</p>}{typeof item.est_duration_ms==='number'&&<small>预计 {item.est_duration_ms/1000} 秒</small>}{Array.isArray(item.lines)&&item.lines.map((line:{text:string},i:number)=><p key={i}>{line.text}</p>)}</article>)}</div>;
}
type Candidate=Entity & {operation:string;approval_state:string;output_json:Record<string,unknown>;input_json:{snapshot:{lines:Entity[];shots:Entity[]};target_id:string|null};provenance_json:{mock:boolean;sourceRepo:string;sourceCommit:string;sourcePaths:string[];license:string}};
export function Creative({entry='story',embedded=false}:{entry?:string;embedded?:boolean}){
  const {id=''}=useParams();const [params]=useSearchParams();
  const models=useList('/creative/models'), skills=useList('/creative/skills'), candidates=useList<Candidate>(`/episodes/${id}/creative/candidates`);
  const script=useObject<{scenes:Scene[]}>(`/episodes/${id}/script`), shots=useList(`/episodes/${id}/shots`);
  const [operation,setOperation]=useState(entry==='assets'?'assets':entry==='director'?'shots':'script'),[modelId,setModelId]=useState(''),[instruction,setInstruction]=useState(''),[target,setTarget]=useState(params.get('shot')??'');
  const [selected,setSelected]=useState<Candidate|null>(null);
  const status=useObject<{network_enabled:boolean}>('/creative/status');
  const episode=useObject(`/episodes/${id}`), assets=useList(episode.data?`/projects/${episode.data.project_id}/assets`:'/projects');
  const [testMode,setTestMode]=useState(false),[actual,setActual]=useState(false),[imageTarget]=useState(entry==='director'?'shot':'asset');
  const selectedModel=models.data?.find(m=>m.id===modelId);
  const isReal=selectedModel?.provider==='openai_compatible';
  const choices=models.data?.filter(m=>m.kind===(operation==='image'?'image':'text')&&(testMode||m.provider!=='mock'))??[];
  const targets=operation==='dialogue'?script.data?.scenes.flatMap(s=>s.lines)??[]:operation==='image'&&imageTarget==='asset'?assets.data??[]:shots.data??[];
  const allowed=entry==='assets'?['assets','image']:entry==='director'?['shots','prompt','image']:['script','dialogue'];
  const current=candidates.data?.find(c=>c.id===selected?.id)??selected;
  const previous=current?.input_json.snapshot[current.operation==='dialogue'?'lines':'shots'].find(v=>v.id===current.input_json.target_id);
  return <section className={embedded?"creative-page":"page creative-page"}>{!embedded&&<div className="creative-heading"><div><Link to={`/episodes/${id}/director${params.size?'?'+params.toString():''}`}>返回导演工作台</Link><h1>AI 创作</h1></div><span className="phase-badge">{status.data?.network_enabled?'实际调用已启用':'服务端调用开关未开启'}</span></div>}
    <div className="creative-grid"><section className="panel"><h2>创作操作</h2><label>操作<select aria-label="操作" value={operation} onChange={e=>{setOperation(e.target.value);setModelId('');setTarget('');}}>{Object.entries(operations).filter(([key])=>allowed.includes(key)).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
      <label>模型<select aria-label="模型" value={modelId} onChange={e=>{setModelId(e.target.value);setActual(false);}}><option value="">选择模型配置</option>{choices.map(m=><option key={m.id} value={m.id}>{String(m.name)}{m.provider==='mock'?' / 测试演示':m.credential_configured?' / 已配置':' / 密钥未配置'}</option>)}</select></label>
      {operation==='image'&&<p>{imageTarget==='asset'?'资产参考图':'镜头关键画面'}</p>}{['dialogue','prompt','image'].includes(operation)&&<label>目标<select aria-label="目标" value={target} onChange={e=>setTarget(e.target.value)}><option value="">选择本集内容</option>{targets.map(t=><option value={t.id} key={t.id}>{String(t.text??t.action_desc??t.name).slice(0,70)}</option>)}</select></label>}
      <label>创作要求<textarea rows={5} value={instruction} onChange={e=>setInstruction(e.target.value)} maxLength={5000}/></label>
      <label className="inline"><input type="checkbox" checked={testMode} onChange={e=>{setTestMode(e.target.checked);setModelId('');}}/>显示测试模型</label>
      {isReal&&<label className="inline"><input type="checkbox" checked={actual} onChange={e=>setActual(e.target.checked)}/>实际调用此模型，发送本次输入并可能产生费用</label>}
      {!status.data?.network_enabled&&<p className="muted">在项目 .env 设置 MANJU_MODEL_NETWORK_ENABLED=true 并重建 API 后可实际调用。配置说明见 docs/MODEL-SETUP.md。</p>}
      {operation==='image'&&<p className="muted">当前支持文本生图，不发送参考图，不支持图片编辑。候选需明确采用。</p>}
      <Action disabled={!modelId||!instruction.trim()||(['dialogue','prompt','image'].includes(operation)&&!target)||(isReal&&(!actual||!selectedModel?.credential_configured||!status.data?.network_enabled))} run={async()=>{const c=await api<Candidate>(`/episodes/${id}/creative/candidates`,'POST',{operation,model_config_id:modelId,instruction,target_id:target||null,image_target:imageTarget,actual_call:actual});setSelected(c);setActual(false);}}>生成创作候选</Action>
      <LoadError error={candidates.error??models.error}/><h2>候选历史</h2><div className="creative-history">{candidates.data?.filter(c=>allowed.includes(c.operation)).map(c=><button className={current?.id===c.id?'active':''} key={c.id} onClick={()=>setSelected(c)}>{operations[c.operation]} / {c.approval_state==='adopted'?'已采用':'待选择'} <small>{c.provenance_json.mock?'测试演示':'模型结果'}</small></button>)}</div>
    </section><section className="panel"><h2>候选预览</h2>{current?<><span className="phase-badge">{current.provenance_json.mock?'演示结果':'模型结果'}</span>{previous&&<><h3>原内容</h3><p>{String(current.operation==='dialogue'?previous.text:previous.prompt_text)}</p></>}<h3>{['script','assets','shots'].includes(current.operation)?'采用后追加以下内容':'候选内容'}</h3><CandidateContent value={current.output_json}/>{typeof current.output_json.file_id==='string'&&<FileImage id={current.output_json.file_id} alt="生成画面候选"/>}
      {current.operation==='image'&&!current.output_json.file_id?<p className="muted">未生成图片文件，不可作为真实画面采用。</p>:<Action disabled={current.approval_state!=='pending'} run={()=>api(`/creative/candidates/${current.id}/adopt`,'POST',{base_version:current.version})}>{current.approval_state==='adopted'?'已采用':'采用此候选'}</Action>}
      {current.operation!=='image'&&current.approval_state==='pending'&&<CandidateEditor key={current.id} candidate={current} onSaved={c=>setSelected(c as Candidate)}/>}<details><summary>来源与版本</summary><a href={current.provenance_json.sourceRepo} target="_blank" rel="noreferrer">来源仓库</a><p>{current.provenance_json.license}</p><code>{current.provenance_json.sourceCommit}</code></details></>:<p className="empty">选择创作操作，生成后在这里检查候选。</p>}</section></div>
    <Link to="/settings/models">模型设置</Link>
    <details className="panel"><summary>技能来源与接入状态</summary>{skills.data?.map(s=><div className="list-row" key={s.id}><span>{s.id} / {String(s.license)}</span><small>{statuses[String(s.status)]??String(s.status)}</small></div>)}</details>
  </section>;
}
