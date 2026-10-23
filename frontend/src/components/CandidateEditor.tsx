import {useState} from 'react';
import {Action} from './Common';
import {api,Entity} from '../api/client';
const labels:Record<string,string>={text:'文字',title:'场次名称',name:'资产名称',description:'描述',action_desc:'镜头动作',blocking_desc:'站位与视线',est_duration_ms:'预计时长（毫秒）'};
export function CandidateEditor({candidate,onSaved}:{candidate:Entity & {output_json:Record<string,unknown>};onSaved:(value:Entity)=>void}){
  const [draft,setDraft]=useState(candidate.output_json);
  function change(path:(string|number)[],value:string|number){
    const next=structuredClone(draft);let node:Record<string|number,unknown>=next;
    for(const part of path.slice(0,-1))node=node[part] as Record<string|number,unknown>;
    node[path[path.length-1]]=value;setDraft(next);
  }
  function fields(value:unknown,path:(string|number)[]=[]):React.ReactNode{
    if(Array.isArray(value))return value.map((item,index)=><div key={index}>{fields(item,[...path,index])}</div>);
    if(value&&typeof value==='object')return Object.entries(value).map(([key,item])=>{
      const next=[...path,key];
      if(labels[key]&&(typeof item==='string'||typeof item==='number'))return <label key={key}>{labels[key]}{typeof item==='number'?<input type="number" value={item} onChange={e=>change(next,Number(e.target.value))}/>:<textarea value={item} onChange={e=>change(next,e.target.value)}/>}</label>;
      return <div key={key}>{fields(item,next)}</div>;
    });
    return null;
  }
  return <details><summary>编辑候选</summary>{fields(draft)}<Action run={async()=>{const saved=await api<Entity>(`/creative/candidates/${candidate.id}/revise`,'POST',{base_version:candidate.version,output:draft});onSaved(saved);}}>保存为新候选</Action></details>;
}
