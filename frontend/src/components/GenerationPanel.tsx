import { useEffect, useRef, useState } from 'react';
import { Drawer } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, Entity } from '../api/client';
import { Action, LoadError, useObject } from './Common';

type Workflow = Entity & {kind:string;provider:string;name:string};
type Task = Entity & {status:string;kind:string;progress:number|null;error_message:string|null;snapshot_json:unknown};
type Candidate = Entity & {kind:string;file_id:string;meta_json:{provider:string}};
const statuses:Record<string,string>={queued:'排队中',running:'生成中',succeeded:'成功',failed:'失败',canceled:'已取消'};

export function GenerationMedia({fileId,video=false,alt='候选画面'}:{fileId:string;video?:boolean;alt?:string}) {
  const file=useObject<{url:string}>(`/files/${fileId}/url`);
  return file.data ? video ? <video className="generation-media" controls src={file.data.url} aria-label="候选视频"/> : <img className="generation-media" src={file.data.url} alt={alt}/> : <LoadError error={file.error}/>;
}

export function GenerationPanel({target,asset=false,projectId,onAdopt}:{target:Entity;asset?:boolean;projectId:string;onAdopt?:()=>void}) {
  const path=`/${asset?'asset-versions':'shots'}/${target.id}`;
  const workflows=useObject<Workflow[]>('/workflows');
  const tasks=useQuery({queryKey:[`${path}/tasks`],queryFn:()=>api<Task[]>(`${path}/tasks`),refetchInterval:2500});
  const candidates=useQuery({queryKey:[`${path}/candidates`],queryFn:()=>api<Candidate[]>(`${path}/candidates`),refetchInterval:2500});
  const [kind,setKind]=useState(target.use_keyframe===false?'video':'keyframe'),[workflowId,setWorkflowId]=useState(''),[selected,setSelected]=useState<string[]>([]),[detail,setDetail]=useState<Task|null>(null),[autoNext,setAutoNext]=useState(true);
  const query=useQueryClient(); const request=useRef<{body:string;key:string}|null>(null);
  const options=workflows.data?.filter(w=>w.kind===kind)??[];
  const workflow=options.find(w=>w.id===workflowId)??options[0];
  const items=candidates.data?.filter(c=>c.kind===kind)??[];
  const adoptedId=String(target[`adopted_${kind}_candidate_id`]??'');
  const shown=selected.map(id=>items.find(c=>c.id===id)).filter((c):c is Candidate=>!!c);
  if(!shown.length){const current=items.find(c=>c.id===adoptedId)??items[0];if(current)shown.push(current);}
  useEffect(()=>{
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    async function connect(){
      try{
        const response=await fetch(`/api/v1/projects/${projectId}/events`,{headers:{Authorization:`Bearer ${localStorage.getItem('token')??''}`},signal:abort.signal});
        if(!response.ok||!response.body)throw new Error('events unavailable');
        void query.invalidateQueries({queryKey:[`${path}/tasks`]});void query.invalidateQueries({queryKey:[`${path}/candidates`]});
        const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
        while(!abort.signal.aborted){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let split;
          while((split=buffer.indexOf('\n\n'))>=0){const event=buffer.slice(0,split);buffer=buffer.slice(split+2);if(event.includes('event: task.updated')){void query.invalidateQueries({queryKey:[`${path}/tasks`]});void query.invalidateQueries({queryKey:[`${path}/candidates`]});}}
        }
      }catch{ /* polling remains available while the authenticated SSE stream reconnects */ }
      if(!abort.signal.aborted)timer=setTimeout(()=>void connect(),3000);
    }
    void connect();return()=>{abort.abort();clearTimeout(timer);};
  },[projectId,path,query]);
  async function generate(){
    if(!workflow)throw new Error('请先配置工作流。');
    const body=JSON.stringify({kind,workflow_id:workflow.id});
    if(request.current?.body!==body)request.current={body,key:crypto.randomUUID()};
    await api(`${path}/generate`,'POST',{...JSON.parse(body),idempotency_key:request.current.key});request.current=null;
  }
  return <section className="generation-panel"><div className="viewer-toolbar"><div className="tabs">{(asset?['keyframe']:['keyframe','video']).map(value=><button key={value} className={kind===value?'active':''} onClick={()=>{setKind(value);setSelected([]);setWorkflowId('');}}>{value==='keyframe'?'关键画面':'视频'}</button>)}</div><span className="muted">{workflow?.provider==='mock'?'MOCK 测试模式':'ComfyUI'}</span></div>
    <div className={`generation-preview ${shown.length===2?'comparison':''}`}>{shown.length?shown.map(c=><figure key={c.id}><GenerationMedia fileId={c.file_id} video={c.kind==='video'}/><figcaption>{c.id===adoptedId?<span className="tag">✓ 已采用</span>:<span>候选</span>}{c.meta_json.provider==='mock'&&<span className="muted"> MOCK</span>}</figcaption></figure>):<div className="frame-guides"><h2>暂无{kind==='keyframe'?'关键画面':'视频'}</h2></div>}</div>
    <div className="generation-controls"><label>工作流<select value={workflow?.id??''} onChange={e=>setWorkflowId(e.target.value)}>{options.map(w=><option key={w.id} value={w.id}>{w.name} / v{String(w.version)}</option>)}</select></label><Action disabled={!workflow||(kind==='video'&&!!target.use_keyframe&&!target.adopted_keyframe_candidate_id)} run={generate}>生成{kind==='keyframe'?'关键画面':'视频'}</Action>{kind==='video'&&!!target.use_keyframe&&!target.adopted_keyframe_candidate_id&&<p className="muted">请先采用关键画面。</p>}</div>
    <LoadError error={workflows.error??tasks.error??candidates.error}/><div className="candidate-heading"><h3>候选</h3><span className="muted">选择最多两项对比</span></div><div className="generation-candidates">{items.map((c,index)=><article key={c.id}><label><input type="checkbox" checked={selected.includes(c.id)} onChange={e=>setSelected(e.target.checked?[...selected.slice(-1),c.id]:selected.filter(id=>id!==c.id))}/>候选 {items.length-index}</label>{c.id===adoptedId?<span className="tag">✓ 已采用</span>:<Action run={async()=>{await api(`${path}/adopt`,'POST',{candidate_id:c.id,base_version:asset?target.version:target.content_version});if(autoNext)onAdopt?.();}}>采用</Action>}</article>)}</div>
    {!asset&&<label className="binding"><input type="checkbox" checked={autoNext} onChange={e=>setAutoNext(e.target.checked)}/>采用后选中下一镜</label>}
    <details className="generation-tasks"><summary>任务记录 ({tasks.data?.length??0})</summary>{tasks.data?.map(task=><article key={task.id}><button className="task-status" onClick={()=>setDetail(task)}>{statuses[task.status]} {task.progress===null?'':`${Math.round(task.progress*100)}%`}</button><span>{task.kind==='keyframe'?'关键画面':'视频'}</span>{task.error_message&&<p className="error">{task.error_message}</p>}{['queued','running'].includes(task.status)&&<Action run={()=>api(`/tasks/${task.id}/cancel`,'POST')}>取消任务</Action>}{['failed','canceled'].includes(task.status)&&<Action run={()=>api(`/tasks/${task.id}/retry`,'POST',{idempotency_key:crypto.randomUUID()})}>手动重试</Action>}</article>)}</details>
    <Drawer open={!!detail} onClose={()=>setDetail(null)} title="任务快照" width={520}>{detail&&<><p>{statuses[detail.status]}</p><p className="muted">重试会消耗额外算力。默认复用此快照。</p><pre className="snapshot-json">{JSON.stringify(detail.snapshot_json,null,2)}</pre></>}</Drawer>
  </section>;
}
