// Signal actual first-screen readiness to the desktop host. No timer-based splash.
export async function finishStartup(){
 if(document.fonts)await document.fonts.ready;
 await Promise.all([...document.querySelectorAll('img.pictoplus-logo,#mascot,.shape-choice img')].map(image=>image.decode()));
 // The native host keeps its loading surface above the live browser until
 // this signal. Standalone browsers also wait for their first paint.
 if(!window.chrome?.webview)await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 document.documentElement.dataset.startup='ready';
 document.getElementById('startupLoading')?.remove();
 performance.mark('pictoplus-screen-ready');
 window.chrome?.webview?.postMessage({type:'uiReady',milliseconds:Math.round(performance.now())});
}

export function startupFailed(error){
 const message='Unable to open PictoPlus: '+error.message;
 const loading=document.getElementById('startupLoading');if(loading)loading.textContent=message;
 window.chrome?.webview?.postMessage({type:'uiFailed',message});
}
