export type Entity = { id: string; version: number; [key: string]: unknown };
export type Shot = Entity & { content_version: number; action_desc: string; scene_id: string | null; order_no: number; est_duration_ms: number; refs: {asset_version_id: string}[]; lines: {line_id: string}[] };
export type Scene = Entity & { title: string; lines: Entity[] };
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
export async function api<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const form = data instanceof FormData;
  const response = await fetch(`/api/v1${path}`, { method, headers: {
    ...(form ? {} : {'Content-Type': 'application/json'}),
    Authorization: `Bearer ${localStorage.getItem('token') ?? ''}`,
  }, body: data === undefined ? undefined : form ? data : JSON.stringify(data) });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body.code, body.message ?? '请求失败，请重试。');
  return body as T;
}
export async function all<T>(path: string): Promise<T[]> {
  const result: T[] = [];
  let total = 1;
  while (result.length < total) {
    const page = await api<{items: T[]; total: number}>(`${path}?offset=${result.length}&limit=100`);
    result.push(...page.items); total = page.total;
    if (!page.items.length) break;
  }
  return result;
}
