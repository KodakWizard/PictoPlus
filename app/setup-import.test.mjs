import assert from 'node:assert/strict';
import {importSetupFile} from './setup-import.js';
for(const name of ['PictoPlus-Setup.pictosetup','authoring.pictoauthoring']){
 const file={name},calls=[],progress=[];let replies=[{job:'test'},{progress:{stage:'Checking setup files'}},{done:true,result:{ready:true,message:'Setup complete.'}}];
 globalThis.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>replies.shift()};};
 assert.equal((await importSetupFile(file,'local-token',p=>progress.push(p.stage))).ready,true);
 assert.equal(calls[0][1].body,file);assert.equal(calls[0][1].headers['X-Studio-Token'],'local-token');
 assert.equal(calls[0][1].headers['Content-Type'],'application/octet-stream');
 assert.deepEqual(progress,['Checking setup files']);assert.equal(calls[1][0],'/api/job/test');
}
for(const failure of ['upload','job']){
 let n=0;globalThis.fetch=async()=>failure==='job'&&++n===1?{ok:true,json:async()=>({job:'failed'})}:{ok:false,json:async()=>({error:'Damaged setup file.'})};
 await assert.rejects(()=>importSetupFile({},'token'),/Damaged setup file/);
}
console.log('PASS: Help setup imports new/legacy selections, sends authentication, reports progress and surfaces failures.');

const {readFileSync}=await import('node:fs');const {runInNewContext}=await import('node:vm');
const source=readFileSync(new URL('./studio.js',import.meta.url),'utf8').split('function setupPolish(){')[1].split(" const sidebar=")[0];
let picked=0,imported=0;const chosen={name:'PictoPlus-Setup.pictosetup'},elements={faqImportSetup:{},setupFile:{value:'previous',files:[chosen],click(){picked++;}},setupImportStatus:{}};
runInNewContext(source,{$:id=>elements[id],token:'local-token',handle:fn=>fn,toast:()=>{},importSetupFile:async file=>{assert.equal(file,chosen);imported++;return {message:'Setup complete.'};}});
elements.faqImportSetup.onclick();assert.equal(picked,1);assert.equal(elements.setupFile.value,'');
await elements.setupFile.onchange();assert.equal(imported,1);assert.equal(elements.faqImportSetup.disabled,false);assert.equal(elements.setupImportStatus.textContent,'Setup complete.');
console.log('PASS: actual Help button handler opens picker and imports the selected file.');
