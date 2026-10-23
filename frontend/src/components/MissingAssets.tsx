import { useState } from 'react';
import { api, Entity, Scene } from '../api/client';
import { Action, useList, useObject } from './Common';

export function MissingAssets({episodeId, projectId}:{episodeId:string;projectId:string}) {
  const script=useObject<{scenes:Scene[]}>(`/episodes/${episodeId}/script`);
  const assets=useList(`/projects/${projectId}/assets`);
  const missing=(script.data?.scenes??[]).flatMap(scene=>[
    ...(!scene.location_asset_id?[{entity:scene,path:`/scenes/${scene.id}`,field:'location_asset_id',type:'location',label:scene.title}]:[]),
    ...scene.lines.filter(line=>line.line_type==='dialogue'&&!line.character_asset_id).map(line=>({entity:line,path:`/lines/${line.id}`,field:'character_asset_id',type:'character',label:String(line.text)})),
  ]);
  return missing.length>0?<details className="missing-assets"><summary>本集待关联资产 {missing.length} 项</summary>{missing.map(item=><MissingRow key={item.entity.id} {...item} assets={assets.data??[]} projectId={projectId}/>)}</details>:null;
}
function MissingRow({entity,path,field,type,label,assets,projectId}:{entity:Entity;path:string;field:string;type:string;label:string;assets:Entity[];projectId:string}) {
  const [selected,setSelected]=useState(''),[name,setName]=useState('');
  async function bind(id:string){return api(path,'PATCH',{base_version:entity.version,[field]:id});}
  return <div className="missing-row"><span>{label||'未填写对白'}</span><label>复用{type==='location'?'地点':'角色'}<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">选择已有资产</option>{assets.filter(a=>a.asset_type===type).map(a=><option value={a.id} key={a.id}>{String(a.name)}</option>)}</select></label><Action disabled={!selected} run={()=>bind(selected)}>关联</Action><label>新资产名称<input value={name} onChange={e=>setName(e.target.value)}/></label><Action disabled={!name.trim()} run={async()=>{const asset=await api<Entity>(`/projects/${projectId}/assets`,'POST',{name,asset_type:type});await bind(asset.id);}}>新建并关联</Action></div>;
}
