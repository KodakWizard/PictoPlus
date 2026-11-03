import assert from 'node:assert/strict';
import {finishStartup,startupFailed} from './startup.js';
for(const native of [true,false]){
 let fontReady,imageReady,notified=false,frames=0,removed=false;
 const fonts=new Promise(r=>fontReady=r),image=new Promise(r=>imageReady=r),messages=[];
 globalThis.document={fonts:{ready:fonts},querySelectorAll:()=>[{decode:()=>image}],documentElement:{dataset:{}},getElementById:()=>({remove(){removed=true;}})};
 globalThis.window=native?{chrome:{webview:{postMessage(value){notified=true;messages.push(value);}}}}:{};
 globalThis.requestAnimationFrame=fn=>{frames++;fn();};
 const pending=finishStartup();assert.equal(notified,false);fontReady();await Promise.resolve();assert.equal(removed,false);
 imageReady();await pending;assert.equal(removed,true);assert.equal(document.documentElement.dataset.startup,'ready');
 assert.equal(frames,native?0:2);if(native)assert.equal(messages[0].type,'uiReady');
}
const surface={textContent:''},errors=[];document.getElementById=()=>surface;window.chrome={webview:{postMessage:value=>errors.push(value)}};
startupFailed(Error('Missing required file'));assert.match(surface.textContent,/Missing required file/);assert.equal(errors[0].type,'uiFailed');
console.log('PASS: readiness waits for fonts/images and reports failures; host has no fixed-delay or hidden-frame dependency.');

const {readFileSync}=await import('node:fs');const {runInNewContext}=await import('node:vm');
const studio=readFileSync(new URL('./studio.js',import.meta.url),'utf8');
const load=studio.slice(studio.indexOf('function loadDocument('),studio.indexOf('function syncForm('));
let builds=0,checks=0;const nodes=new Map();
const context={clearTimeout:()=>{},saveTimer:null,difficultyTimer:null,difficultyRevision:0,editRevision:0,localStorage:{removeItem:()=>{}},clone:structuredClone,$:id=>{if(!nodes.has(id))nodes.set(id,{value:0,classList:{remove:()=>{}}});return nodes.get(id);},syncForm:()=>{},inspector:()=>builds++,fitCamera:()=>{},updateHistory:()=>{},setValidation:()=>{},setPage:()=>{},updatePlacementHint:()=>{},checkPuzzle:()=>checks++};
runInNewContext(load+';loadDocument({dimensions:[6,6,6],cells:[]},false);',context);assert.equal(builds,1);assert.equal(checks,0);
runInNewContext('loadDocument({dimensions:[6,6,6],cells:[]});',context);assert.equal(builds,2);assert.equal(checks,1);
console.log('PASS: loading a document builds once and first-screen validation can be deferred.');
