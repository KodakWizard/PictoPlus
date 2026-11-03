import assert from 'node:assert/strict';
import {freePlacement,zeroSweepCells} from './placement.js';
// Every cell in a 10-cube volume must be reachable by a mouse ray plus depth,
// including floating and interior cells in an otherwise empty design.
const d=[10,10,10],origin=[18,17,19];let tested=0;
for(let x=0;x<10;x++)for(let y=0;y<10;y++)for(let z=0;z<10;z++){
 const target=[x+.5-5,y+.5,z+.5-5],delta=target.map((v,a)=>v-origin[a]),length=Math.hypot(...delta),dir=delta.map(v=>v/length);
 let near=0,far=Infinity;for(let a=0;a<3;a++){const min=a===1?0:-5,max=a===1?10:5;near=Math.max(near,(max-origin[a])/dir[a]);far=Math.min(far,(min-origin[a])/dir[a]);}
 assert.deepEqual(freePlacement(origin,dir,d,(length-near)/(far-near)),[x,y,z]);tested++;
}
assert.equal(freePlacement([18,17,19],[1,0,0],d,.5),null);
const solution=[{xyz:[1,1,1],shape:0}],masks=[Array(9).fill(0),Array(9).fill(0),Array(9).fill(0)];
assert.equal(zeroSweepCells([3,3,3],solution,masks,true).length,27,'Hidden zero clues do not clear cells');
masks[0][0]=1;assert.equal(zeroSweepCells([3,3,3],solution,masks,true).length,24);
assert.equal(zeroSweepCells([3,3,3],solution,null,true).length,1);
assert.equal(zeroSweepCells([3,3,3],solution,null,false).length,27);
console.log('PASS: '+tested+' free-placement cells, off-volume ray, visible/hidden zero sweeps');
