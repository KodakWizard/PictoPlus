// The same authenticated import endpoint as first-run setup; no navigation or
// reload, so importing from Help preserves the current design and workspace.
export async function importSetupFile(file,token,onProgress){
 const headers={'X-Studio-Token':token};
 const response=await fetch('/api/import-authoring',{method:'POST',headers:{...headers,'Content-Type':'application/octet-stream'},body:file});
 let result=await response.json();
 if(!response.ok||result.error)throw Error(result.error||'Setup file could not be imported.');
 while(result.job){
  await new Promise(resolve=>setTimeout(resolve,250));
  const reply=await fetch('/api/job/'+result.job,{headers}),update=await reply.json();
  if(!reply.ok||update.error)throw Error(update.error||'Setup file could not be imported.');
  if(update.progress)onProgress?.(update.progress);
  if(update.done)return update.result;
 }
 return result;
}
