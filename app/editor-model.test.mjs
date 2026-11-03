import assert from 'node:assert/strict';
import {resizeBuildSpace} from './editor-model.js';
const original={dimensions:[3,3,3],cells:[{xyz:[1,1,1],shape:1}],clues:{},imported_model:{triangles:[[[1,1,1],[2,1,1],[1,2,1]]],fit_dimensions:[3,3,3]}};
for(let axis=0;axis<3;axis++)for(const side of [-1,1]){
 const grown=resizeBuildSpace(original,axis,side,1);
 assert.equal(grown.dimensions[axis],4);
 assert.equal(grown.cells[0].xyz[axis],side<0?2:1);
 assert.equal(grown.imported_model.triangles[0][0][axis],side<0?2:1);
 assert.equal(grown.clues,undefined);
 const restored=resizeBuildSpace(grown,axis,side,-1);
 assert.deepEqual(restored.cells,original.cells);
 assert.deepEqual(restored.imported_model.triangles,original.imported_model.triangles);
}
assert.deepEqual(original.cells[0].xyz,[1,1,1]);
assert.throws(()=>resizeBuildSpace({...original,cells:[{xyz:[0,1,1],shape:0}]},0,-1,-1),/contains blocks/);
assert.throws(()=>resizeBuildSpace({...original,cells:[{xyz:[2,1,1],shape:0}]},0,1,-1),/contains blocks/);
console.log('PASS: six-end resizing preserves blocks and attached model alignment; occupied layers are protected');
