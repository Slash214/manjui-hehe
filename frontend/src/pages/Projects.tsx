import { Modal } from 'antd';
import {api} from '../api/client';
import {Action} from '../components/Common';
import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { Add, Delete, LoadError, useList, useObject } from '../components/Common';
import { Editor } from '../components/Editor';
import { Assets } from './Assets';

export function Projects() {
  const projects = useList('/projects');
  const [open,setOpen]=useState(false),[rights,setRights]=useState(false),[name,setName]=useState(''),[style,setStyle]=useState(''),[aspect,setAspect]=useState('9:16');
  return <main className="page"><div className="eyebrow">创作空间</div><h1>我的作品</h1><p></p><LoadError error={projects.error}/>
    <button className="primary" onClick={()=>setOpen(true)}>新建项目</button><Modal title="新建项目" open={open} footer={null} onCancel={()=>setOpen(false)}><label>作品名称<input value={name} onChange={e=>setName(e.target.value)}/></label><label>全局画风<textarea value={style} onChange={e=>setStyle(e.target.value)}/></label><label>画幅<select value={aspect} onChange={e=>setAspect(e.target.value)}><option value="9:16">9:16 竖屏</option><option value="16:9">16:9 横屏</option></select></label><label className="inline"><input type="checkbox" checked={rights} onChange={e=>setRights(e.target.checked)}/>我确认拥有所输入内容的使用权</label><Action disabled={!rights||!name.trim()} run={async()=>{await api('/projects','POST',{name,style_prompt:style,aspect_ratio:aspect,resolution:aspect==='9:16'?'1080x1920':'1920x1080'});setOpen(false);setName('');}}>创建项目</Action></Modal>
    <section className="panel"><h2>项目列表</h2>{projects.data?.length === 0 && <p className="empty">还没有作品。请先确认内容使用权，再创建第一个项目。</p>}{projects.data?.map(project => <div className="list-row" key={project.id}><div><Link to={`/projects/${project.id}`}>{String(project.name)}</Link><small>{String(project.aspect_ratio)} / {String(project.fps)} fps</small></div><Delete entity={project} path={`/projects/${project.id}`}/></div>)}</section>
  </main>;
}
export function ProjectPage() {
  const {id = ''} = useParams(); const project = useObject(`/projects/${id}`), episodes = useList(`/projects/${id}/episodes`);
  const [tab, setTab] = useState('episodes');
  if (!project.data) return <LoadError error={project.error}/>;
  return <main className="page"><Link to="/">← 所有项目</Link><h1>{String(project.data.name)}</h1><nav>{[['episodes','单集'],['assets','资产库'],['settings','项目设置']].map(([key,label]) => <button className={tab===key?'active':''} key={key} onClick={() => setTab(key)}>{label}</button>)}</nav>
    {tab==='episodes' && <section className="panel"><h2>单集列表</h2><Add path={`/projects/${id}/episodes`} label="单集标题" field="title" data={{episode_no:(episodes.data?.length ?? 0)+1}}/><LoadError error={episodes.error}/>{episodes.data?.map(ep => <div className="list-row" key={ep.id}><Link to={`/episodes/${ep.id}/story`}>第 {String(ep.episode_no)} 集 / {String(ep.title)}</Link><Delete entity={ep} path={`/episodes/${ep.id}`}/></div>)}</section>}
    {tab==='assets' && <Assets projectId={id}/>}
    {tab==='settings' && <section className="panel"><h2>作品设置</h2><Link to="/settings/models">文本与生图模型设置</Link><Editor key={project.data.id} entity={project.data} path={`/projects/${id}`} fields={[{key:'name',label:'作品名称'},{key:'description',label:'简介',type:'textarea'},{key:'style_prompt',label:'全局画风',type:'textarea'},{key:'aspect_ratio',label:'画幅',type:'select',options:[{value:'9:16',label:'9:16 竖屏'},{value:'16:9',label:'16:9 横屏'}]},{key:'resolution',label:'分辨率',type:'select',options:[{value:'1080x1920',label:'1080 × 1920'},{value:'1920x1080',label:'1920 × 1080'}]},{key:'fps',label:'帧率',type:'number'}]}/></section>}
  </main>;
}
