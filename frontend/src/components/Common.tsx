import { ReactNode, useState } from 'react';
import { Alert, App, Button } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { all, api, Entity } from '../api/client';

export function useList<T = Entity>(path: string) {
  return useQuery({queryKey: [path], queryFn: () => all<T>(path)});
}
export function useObject<T = Entity>(path: string) {
  return useQuery({queryKey: [path], queryFn: () => api<T>(path), enabled: !!path});
}
export function Action({children, run, disabled = false}: {children: ReactNode; run: () => Promise<unknown>; disabled?: boolean}) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const query = useQueryClient();
  return <span><Button disabled={busy || disabled} loading={busy} onClick={async () => {setBusy(true); setError(''); try {await run(); await query.invalidateQueries();} catch(e) {setError(e instanceof Error ? e.message : '操作失败，请重试。');} finally {setBusy(false);}}}>{children}</Button>{error && <Alert className="action-error" role="alert" type="error" title={error} showIcon/>}</span>;
}
export function Add({path, data = {}, label, field = 'name'}: {path: string; data?: Record<string, unknown>; label: string; field?: string}) {
  const [name, setName] = useState('');
  return <div className="add"><input aria-label={label} placeholder={label} value={name} onChange={e => setName(e.target.value)}/><Action disabled={!name.trim()} run={async () => {await api(path, 'POST', {...data, [field]: name}); setName('');}}>新建</Action></div>;
}
export function Delete({entity, path}: {entity: Entity; path: string}) {
  const { modal } = App.useApp();
  return <Action run={async () => {const confirmed = await modal.confirm({title:'删除此内容？',content:'历史版本将保留。',okText:'确认删除',cancelText:'取消',okButtonProps:{danger:true},autoFocusButton:'cancel'});if(confirmed) await api(`${path}?base_version=${entity.content_version ?? entity.version}`, 'DELETE');}}>删除</Action>;
}
export function Move({items, index, path}: {items: Entity[]; index: number; path: string}) {
  async function move(delta: number) {
    const next = [...items]; [next[index], next[index+delta]] = [next[index+delta], next[index]];
    return api(path, 'POST', {items: Object.fromEntries(next.map(x => [x.id, x.content_version ?? x.version]))});
  }
  return <span className="actions"><Action disabled={index === 0} run={() => move(-1)}>上移</Action><Action disabled={index === items.length-1} run={() => move(1)}>下移</Action></span>;
}
export function LoadError({error}: {error: unknown}) {return error ? <p className="error" role="alert">{error instanceof Error ? error.message : '加载失败，请刷新。'}</p> : null;}
