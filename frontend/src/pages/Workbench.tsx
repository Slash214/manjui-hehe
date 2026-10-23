import { Creative } from './Creative';
import { Navigate, Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { useEffect } from 'react';
import { useObject, useList, LoadError } from '../components/Common';
import { useWorkbench } from '../stores/workbench';
import { Story } from './Story';
import { MissingAssets } from '../components/MissingAssets';
import { Assets } from './Assets';
import { Director } from './Director';

export function Workbench() {
  const {id=''}=useParams();const location=useLocation();const [params,setParams]=useSearchParams();
  const shots=useList(`/episodes/${id}/shots`);
  const episode=useObject(`/episodes/${id}`);const project=useObject(episode.data?`/projects/${episode.data.project_id}`:'');
  const pending=useWorkbench(s=>s.pending);const values=Object.values(pending);
  const entry=location.pathname.split('/').at(-1);const key=`shot:${localStorage.getItem('userId')}:${id}`;
  useEffect(()=>{const shot=params.get('shot');if(shot)localStorage.setItem(key,shot);else{const stored=localStorage.getItem(key);if(stored)setParams({shot:stored},{replace:true});}},[id,key,params,setParams]);
  if(entry==='creative')return <Navigate replace to={`/episodes/${id}/story${location.search}`}/>;
  if(!episode.data)return <LoadError error={episode.error}/>;
  return <div className="workbench"><header className="workbench-header"><div className="breadcrumb"><Link to={`/projects/${episode.data.project_id}`}>{String(project.data?.name??'项目')}</Link><span>/</span><strong>{String(episode.data.title)}</strong><span className="phase-badge">创作中</span></div><div className="save-summary" role="status"><span>待确认 {shots.data?.filter(s=>s.review_status==='needs_review').length??0}</span><span className={values.length?'status-dot pending-dot':'status-dot'}/>{values.length?values.some(v=>v.includes('冲突'))?'存在版本冲突':values.some(v=>v==='保存中')?'保存中':'有未保存内容':'已保存'}</div></header><div className="workspace-nav"><nav>{[['story','故事','01'],['assets','资产','02'],['director','导演','03'],['final','成片','04']].map(([path,label,num])=><Link className={entry===path?'active':''} key={path} to={`/episodes/${id}/${path}${location.search}`}><span>{num}</span>{label}</Link>)}</nav><Link to="/settings/models">模型设置</Link></div>
    {entry!=='final'&&<details className="ai-workspace"><summary>{entry==='story'?'AI 编剧与对白':entry==='assets'?'AI 资产与参考图':'AI 分镜与画面'}</summary><Creative key={entry} entry={entry} embedded/></details>}
    {entry==='story'?<Story episode={episode.data}/>:entry==='assets'?<div className="asset-workspace"><MissingAssets episodeId={id} projectId={String(episode.data.project_id)}/><Assets projectId={String(episode.data.project_id)}/></div>:entry==='director'?<Director episode={episode.data}/>:<div className="final-empty"><div className="final-icon">▤</div><div className="eyebrow">成片工作区</div><h1>每个镜头，终将成为故事。</h1><p><br/>时间线、配音与导出将在后续阶段开放。</p><Link className="button primary" to={`/episodes/${id}/director${location.search}`}>继续编排镜头 →</Link><div className="track-placeholder"><span>视频轨</span><span>对白轨</span><span>音乐轨</span><span>音效轨</span></div></div>}
    <nav className="next-step"><Link to={`/episodes/${id}/assets${location.search}`}>补充资产</Link><Link to={`/episodes/${id}/director${location.search}`}>编排镜头</Link><Link to={`/episodes/${id}/final${location.search}`}>查看成片进度</Link></nav>
  </div>;
}
