import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from './api/client';
import { Projects, ProjectPage } from './pages/Projects';
import { Workbench } from './pages/Workbench';
import { useWorkbench } from './stores/workbench';
import './style.css';
import { UiProvider } from './components/UiProvider';
import { ModelSettings } from './pages/ModelSettings';

const query = new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:false}}});
function App() {
  const [token,setToken]=useState(localStorage.getItem('token')??'');const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const pending=useWorkbench(s=>s.pending);
  useEffect(()=>{
    function unload(event:BeforeUnloadEvent){if(Object.keys(useWorkbench.getState().pending).length){event.preventDefault();event.returnValue='';}}
    function navigate(event:MouseEvent){const link=(event.target as HTMLElement).closest('a');if(link&&Object.keys(useWorkbench.getState().pending).length&&!window.confirm('仍有未保存内容，确认离开？草稿保留在当前页签。')){event.preventDefault();event.stopPropagation();}}
    const updated=()=>{void query.invalidateQueries();};
    window.addEventListener('beforeunload',unload);document.addEventListener('click',navigate,true);window.addEventListener('data-updated',updated);
    return()=>{window.removeEventListener('beforeunload',unload);document.removeEventListener('click',navigate,true);window.removeEventListener('data-updated',updated);};
  },[]);
  async function login(register:boolean){setBusy(true);setError('');try{const result=await api<{access_token:string}>(`/auth/${register?'register':'login'}`,'POST',{email,password});localStorage.setItem('token',result.access_token);const me=await api<{id:string}>('/me');localStorage.setItem('userId',me.id);setToken(result.access_token);query.clear();}catch(e){setError(e instanceof Error?e.message:'登录失败');}finally{setBusy(false);}}
  if(!token)return <main className="login"><div className="login-brand"><span className="brand-icon">幕</span><div className="eyebrow">MANJU STUDIO</div><h1>让故事<br/>逐镜成形。</h1><p>从文字到镜头的创作空间</p></div><section className="login-form"><h2>进入创作工作台</h2><p className="muted">邮箱与密码登录 / 内容仅属于你的账号</p><form onSubmit={e=>{e.preventDefault();void login(false);}}><label>邮箱<input type="email" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)}/></label><label>密码<input type="password" autoComplete="current-password" minLength={8} required value={password} onChange={e=>setPassword(e.target.value)}/></label>{error&&<p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy} type="submit">{busy?'处理中…':'登录工作台'}</button><button disabled={busy||!email||password.length<8} type="button" onClick={()=>void login(true)}>创建账号</button></form><small>阶段 1 / 基础创作与版本管理</small></section></main>;
  return <><div className="appbar"><Link className="brand" to="/"><span className="brand-icon">幕</span>漫剧 <span>STUDIO</span></Link><div className="appbar-right"><span className="muted">个人创作空间</span><button onClick={()=>{if(Object.keys(pending).length&&!window.confirm('有未保存内容，确认退出？'))return;localStorage.removeItem('token');query.clear();setToken('');}}>退出登录</button></div></div><Routes><Route path="/" element={<Projects/>}/><Route path="/projects/:id" element={<ProjectPage/>}/><Route path="/settings/models" element={<ModelSettings/>}/><Route path="/projects" element={<Projects/>}/><Route path="/episodes/:id/:entry" element={<Workbench/>}/><Route path="*" element={<p className="empty">页面不存在，<Link to="/">返回项目列表</Link></p>}/></Routes></>;
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={query}><UiProvider><BrowserRouter><App/></BrowserRouter></UiProvider></QueryClientProvider></React.StrictMode>);
