import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, api, Entity } from '../api/client';
import { useWorkbench } from '../stores/workbench';

export type Field = {key: string; label: string; type?: 'text'|'number'|'textarea'|'checkbox'|'select'|'json'; options?: {value: string; label: string}[]};
export function Editor({entity, path, fields}: {entity: Entity; path: string; fields: Field[]}) {
  const query = useQueryClient();
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [base, setBase] = useState(Number(entity.content_version ?? entity.version));
  const [status, setStatus] = useState('已保存');
  const [blocked, setBlocked] = useState(false);
  const busy = useRef(false);
  const lastServerVersion = useRef(Number(entity.content_version ?? entity.version));
  const revision = useRef(0);
  const draftRef = useRef(draft); draftRef.current = draft;
  const mark = useWorkbench(s => s.mark), clear = useWorkbench(s => s.clear);
  const storageKey = `draft:${localStorage.getItem('userId')}:${path}`;
  useEffect(() => {
    const value = sessionStorage.getItem(storageKey);
    if (value) { try { const saved = JSON.parse(value); setDraft(saved.draft); setBase(saved.base); mark(path, '待保存'); } catch { sessionStorage.removeItem(storageKey); } }
    return () => clear(path);
  }, [path, storageKey, mark, clear]);
  const dirty = Object.keys(draft).length > 0;
  useEffect(() => {
    const serverVersion = Number(entity.content_version ?? entity.version);
    if (serverVersion !== lastServerVersion.current && !dirty && !busy.current) setBase(serverVersion);
    lastServerVersion.current = serverVersion;
  }, [entity.content_version, entity.version, dirty]);
  function value(key: string) { return Object.hasOwn(draft, key) ? draft[key] : entity[key]; }
  async function save() {
    if (busy.current || !Object.keys(draftRef.current).length) return;
    busy.current = true;
    const sent = {...draftRef.current}, rev = revision.current;
    setStatus('保存中'); mark(path, '保存中');
    try {
      for (const field of fields.filter(field => field.type === 'json')) {
        if (!Object.hasOwn(sent, field.key)) continue;
        let parsed: unknown;
        try { parsed = JSON.parse(String(sent[field.key])); } catch { throw new Error('参数格式无效，请输入 JSON 对象后重试。'); }
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('参数必须是 JSON 对象。');
        sent[field.key] = parsed;
      }
      const updated = await api<Entity>(path, 'PATCH', {...sent, base_version: base});
      const nextBase = Number(updated.content_version ?? updated.version);
      setBase(nextBase);
      if (revision.current === rev) { setDraft({}); sessionStorage.removeItem(storageKey); clear(path); setStatus('已保存'); }
      else { sessionStorage.setItem(storageKey, JSON.stringify({draft: draftRef.current, base: nextBase})); }
      await query.invalidateQueries();
    } catch (error) {
      const message = error instanceof ApiError && error.status === 409 ? '版本冲突：其他页签已保存。请复制本地内容，再载入最新版本。' : error instanceof Error ? error.message : '保存失败，点击重试';
      setStatus(message); mark(path, message); setBlocked(true);
    } finally { busy.current = false; }
  }
  useEffect(() => {
    if (!dirty || blocked) return;
    const timer = window.setTimeout(() => {void save();}, 800);
    return () => window.clearTimeout(timer);
  });
  function change(key: string, value: unknown) {
    revision.current += 1;
    const next = {...draftRef.current, [key]: value, ...(key === 'prompt_text' ? {prompt_overridden: true} : {})};
    setDraft(next); mark(path, '待保存');
    sessionStorage.setItem(storageKey, JSON.stringify({draft: next, base}));
  }
  async function reload() {
    if (!window.confirm('本地修改会被放弃，确认载入最新版本？')) return;
    const fresh = await api<Entity>(path);
    setDraft({}); setBase(Number(fresh.content_version ?? fresh.version)); setBlocked(false);
    sessionStorage.removeItem(storageKey); clear(path); setStatus('已保存'); await query.invalidateQueries();
  }
  return <section className="editor"><div className={blocked ? 'error' : 'save-state'} role="status">{status}</div>
    {fields.map(field => field.type === 'json' ? <details key={field.key}><summary>高级参数</summary><label>{field.label}<textarea value={typeof value(field.key) === 'string' ? String(value(field.key)) : JSON.stringify(value(field.key), null, 2)} onChange={e => change(field.key, e.target.value)}/></label></details> : <label key={field.key}>{field.label}
      {field.type === 'textarea' ? <textarea value={String(value(field.key) ?? '')} onChange={e => change(field.key, e.target.value)}/>
      : field.type === 'checkbox' ? <input type="checkbox" checked={Boolean(value(field.key))} onChange={e => change(field.key, e.target.checked)}/>
      : field.type === 'select' ? <select value={String(value(field.key) ?? '')} onChange={e => change(field.key, e.target.value || null)}>{field.options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
      : <input type={field.type ?? 'text'} value={String(value(field.key) ?? '')} onChange={e => change(field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}/>}
    </label>)}
    {blocked && <div className="actions"><button onClick={() => {setBlocked(false); void save();}}>重试保存</button><button onClick={() => void reload()}>载入最新版本</button></div>}
  </section>;
}
