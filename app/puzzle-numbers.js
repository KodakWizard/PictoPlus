// Number artwork is rendered on real cube faces, so it rotates and occludes.
export function buildPuzzleNumbers({THREE,document,visibleCells,masks,zeroRemoved,signature}){
 const group=new THREE.Group(),d=document.dimensions,visible=new Set(visibleCells.map(c=>c.xyz.join(','))),solution=new Map(document.cells.map(c=>[c.xyz.join(','),c.shape===0?1:2]));
 const planes=[[0,1,2],[0,2,1],[2,1,0]],materials=new Map(),geometry=new THREE.PlaneGeometry(.94,.94);
 function material(counts,groups){
  const key=counts.join(',')+'|'+groups.join(',');if(materials.has(key))return materials.get(key);
  const canvas=window.document.createElement('canvas');canvas.width=canvas.height=256;const ctx=canvas.getContext('2d');
  const shown=counts.map((count,i)=>({count,i,groups:groups[i]})).filter(r=>r.count||(!counts[0]&&!counts[1]&&r.i===0));
  ctx.textAlign='center';ctx.textBaseline='middle';ctx.lineWidth=6;
  shown.forEach((row,index)=>{const x=shown.length===1?128:67+index*122,y=130,radius=shown.length===1?92:54,font=shown.length===1?(row.count>=10?110:134):(row.count>=10?82:108);ctx.fillStyle=ctx.strokeStyle=row.i?'#cb761c':'#247fb7';ctx.font=`700 ${font}px "Segoe UI",sans-serif`;ctx.fillText(String(row.count),x,y+4);if(row.groups===2){ctx.beginPath();ctx.arc(x,y,radius,0,Math.PI*2);ctx.stroke();}else if(row.groups>=3)ctx.strokeRect(x-radius,y-radius,radius*2,radius*2);});
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
  const result=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});materials.set(key,result);return result;
 }
 for(let plane=0;plane<3;plane++){
  const [a,b,axis]=planes[plane];
  for(let v=0;v<d[b];v++)for(let u=0;u<d[a];u++){
   if(masks?.[plane]&&!masks[plane][u+v*d[a]])continue;
   const values=[],remaining=[];
   for(let n=0;n<d[axis];n++){const p=[0,0,0];p[a]=u;p[b]=v;p[axis]=n;values.push(solution.get(p.join(','))||0);if(visible.has(p.join(',')))remaining.push(n);}
   if(!remaining.length||(zeroRemoved&&values.every(n=>n===0)))continue;
   const counts=[1,2].map(colour=>values.filter(v=>v===colour).length),groups=[1,2].map(colour=>signature(values,colour));
   for(const side of [-1,1]){
    // Cubes span .015 to .985 within a cell. Keep number planes outside
    // those faces; an inset plane fights the cube depth buffer and vanishes.
    const p=[0,0,0];p[a]=u+.5;p[b]=v+.5;p[axis]=side<0?remaining[0]+.008:remaining.at(-1)+.992;
    const face=new THREE.Mesh(geometry,material(counts,groups));face.userData.puzzleNumber=true;
    if(axis===0)face.rotation.y=side*Math.PI/2;else if(axis===1)face.rotation.x=-side*Math.PI/2;else if(side<0)face.rotation.y=Math.PI;
    face.position.set(p[0]-d[0]/2,p[1],p[2]-d[2]/2);group.add(face);
   }
  }
 }
 return group;
}
