import { useObject } from './Common';
export function VersionReference({id}: {id: string}) {
  const version = useObject(`/asset-versions/${id}`);
  return <span>{version.data ? <>{String(version.data.asset_name)} / v{String(version.data.version_no)}{Boolean(version.data.has_new_current)&&<small>有其他当前版本</small>}</> : id.slice(0,8)}</span>;
}
