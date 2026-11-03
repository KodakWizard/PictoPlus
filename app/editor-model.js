// Resize from either end without discarding an occupied layer.
export function resizeBuildSpace(document,axis,side,amount){
 if(![0,1,2].includes(axis)||![-1,1].includes(side)||!Number.isInteger(amount))throw Error('Invalid build-space change.');
 const next=structuredClone(document),size=document.dimensions[axis]+amount,label='XYZ'[axis]+(side<0?'−':'+');
 if(size<1||size>10)throw Error('Build space must stay between 1 and 10 blocks on each axis.');
 if(amount<0&&document.cells.some(c=>side<0?c.xyz[axis]<-amount:c.xyz[axis]>=size))throw Error(label+' contains blocks. Move or erase them before removing that layer.');
 next.dimensions[axis]=size;
 const shift=side<0?amount:0;
 for(const cell of next.cells)cell.xyz[axis]+=shift;
 if(next.imported_model){
  next.imported_model.triangles=next.imported_model.triangles.map(t=>t.map(p=>p.map((v,a)=>v+(a===axis?shift:0))));
  next.imported_model.fit_dimensions=[...next.dimensions];
 }
 delete next.clues;return next;
}
