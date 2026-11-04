import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {runInNewContext} from 'node:vm';

const studio = readFileSync(new URL('./studio.js', import.meta.url), 'utf8');
const start = studio.indexOf('async function exportSelectedFiles()');
const flow = studio.slice(start, studio.indexOf('function queueSave()', start));

for (const outcome of ['success', 'cancel', 'failure', 'browser']) {
 test(outcome, async () => {
  const nodes = new Map();
  const node = id => {
   if (!nodes.has(id)) nodes.set(id, {});
   return nodes.get(id);
  };
  const dialog = node('exportBooksDialog');
  let closed = false, library = false;
  Object.assign(dialog, {
   dataset: {}, querySelector: () => node('close'),
   close: () => {closed = true;}, addEventListener(){}, removeEventListener(){}
  });
  let resolvePosted;
  const posted = new Promise(resolve => {resolvePosted = resolve;});
  const webview = new EventTarget();
  webview.postMessage = resolvePosted;
  const run = runInNewContext(flow+'exportSelectedFiles()', {
   $:node, selectedExportBooks:()=>[{name:'Animals',id:'book'}], dirty:false,
   window: outcome === 'browser' ? {} : {chrome:{webview}}, crypto:{randomUUID:()=> 'request'},
   backgroundJob:async()=>({file:'job/Animals.pictobook'}),
   downloadLocal:async()=>{}, performance, setInterval, clearInterval,
   setPage: page => {library = page === 'library';}, toast(){}
  });
  if (outcome !== 'browser') {
   const request = await posted;
   assert.equal(node('exportStage').textContent, 'Ready to save');
   assert.equal(closed,false);
   webview.dispatchEvent(new MessageEvent('message',{data:{type:'savePackageResult',requestId:'unrelated',saved:true}}));
   await Promise.resolve();
   assert.equal(closed,false);
   webview.dispatchEvent(new MessageEvent('message',{data:{
    type:'savePackageResult',requestId:request.requestId,saved:outcome==='success',
    error:outcome==='failure'?'Could not save the export. Disk full.':null
   }}));
  }
  if (outcome === 'failure') {
   await assert.rejects(run,/Disk full/);
   assert.match(node('exportBooksStatus').textContent,/Disk full/);
  } else {
   await run;
  }
  if (outcome === 'cancel') assert.match(node('exportBooksStatus').textContent,/cancelled/);
  assert.equal(closed,outcome==='success');
  assert.equal(library,outcome==='success');
  assert.equal(node('exportSelectedBooks').disabled,false);
 });
}
