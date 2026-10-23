import {useObject,LoadError} from './Common';
export function FileImage({id,alt}:{id:string;alt:string}){
  const file=useObject<{url:string}>(`/files/${id}/url`);
  return file.data?<img className="generated-image" src={file.data.url} alt={alt}/>:<LoadError error={file.error}/>;
}
