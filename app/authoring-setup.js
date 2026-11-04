import {finishStartup,startupFailed} from './startup.js';
const token=new URLSearchParams(location.search).get('token'),headers={'X-Studio-Token':token};
const $=id=>document.getElementById(id),message=value=>{$('message').textContent=value;};
async function api(route,body){const r=await fetch('/api/'+route,{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok||data.error)throw Error(data.error||'Setup failed.');return data;}
function action(fn){return async()=>{try{await fn();}catch(e){message(e.message);}finally{$('download').disabled=$('open').disabled=false;}};}
$('download').onclick=action(async()=>{const data=await api('authoring-setup',{});const name='PictoPlus-USA-SD-Loader.zip';if(window.chrome?.webview)window.chrome.webview.postMessage({type:'savePackage',file:data.file,name});else{const r=await fetch('/api/export/'+encodeURIComponent(data.file),{headers});if(!r.ok)throw Error('Download failed.');const a=document.createElement('a');a.href=URL.createObjectURL(await r.blob());a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}message('Copy the loader to SD and launch the USA game to create a setup file if one is missing.');});
$('open').onclick=()=>$('file').click();
$('file').onchange=action(async()=>{const file=$('file').files[0];if(!file)return;$('open').disabled=$('download').disabled=true;message('Checking your setup file…');$('progress').hidden=false;const r=await fetch('/api/import-authoring',{method:'POST',headers:{...headers,'Content-Type':'application/octet-stream'},body:file});const data=await r.json();if(!r.ok||data.error)throw Error(data.error||'Import failed.');for(;;){const res=await fetch('/api/job/'+data.job,{headers});const job=await res.json();if(job.error)throw Error(job.error);if(job.done){message('Setup complete. Opening the editor…');location.href='/?token='+encodeURIComponent(token);return;}if(job.progress){message(job.progress.stage);$('progress').max=job.progress.total;$('progress').value=job.progress.completed;}await new Promise(resolve=>setTimeout(resolve,250));}});

$('return').href='/?token='+encodeURIComponent(token);
api('authoring-status',{}).then(status=>{$('readyNote').hidden=!status.ready;}).catch(()=>{});

finishStartup().catch(startupFailed);
