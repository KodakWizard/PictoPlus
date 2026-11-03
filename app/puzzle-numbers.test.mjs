import assert from 'node:assert/strict';
import * as THREE from './vendor/package/build/three.module.js';
import {buildPuzzleNumbers} from './puzzle-numbers.js';
const context={fillText(){},beginPath(){},arc(){},stroke(){},strokeRect(){}};
globalThis.window={document:{createElement(){return {getContext(){return context;}};}}};
const document={dimensions:[1,1,1],cells:[{xyz:[0,0,0],shape:0}]};
const group=buildPuzzleNumbers({THREE,document,visibleCells:document.cells,zeroRemoved:false,signature:()=>1});
assert.equal(group.children.length,6);
for(const face of group.children){
 const centred=face.position.clone().sub(new THREE.Vector3(0,.5,0));
 const distance=Math.max(Math.abs(centred.x),Math.abs(centred.y),Math.abs(centred.z));
 assert.ok(distance>.485&&distance<.5,'Number artwork must sit outside its .97-unit cube face');
 assert.equal(face.material.depthWrite,false);
}
console.log('Number planes remain outside every cube face.');
