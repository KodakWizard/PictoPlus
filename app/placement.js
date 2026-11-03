// Mouse rays select a depth inside the entire build volume, without a floor hit.
export function freePlacement(origin,direction,d,depth){
 const min=[-d[0]/2,0,-d[2]/2],max=[d[0]/2,d[1],d[2]/2];let near=0,far=Infinity;
 for(let a=0;a<3;a++){const o=origin[a],v=direction[a];if(Math.abs(v)<1e-9){if(o<min[a]||o>max[a])return null;continue;}let first=(min[a]-o)/v,last=(max[a]-o)/v;if(first>last)[first,last]=[last,first];near=Math.max(near,first);far=Math.min(far,last);}
 if(far<near)return null;const t=near+(far-near)*Math.max(.001,Math.min(.999,depth));return origin.map((v,a)=>Math.max(0,Math.min(d[a]-1,Math.floor(v+direction[a]*t+(a===1?0:d[a]/2)))));
}
export function zeroSweepCells(d,solution,masks,enabled){
 const removed=new Set(),occupied=new Set(solution.map(c=>c.xyz.join(',')));
 if(enabled)for(const [plane,[a,b,axis]] of [[0,[0,1,2]],[1,[0,2,1]],[2,[2,1,0]]])for(let v=0;v<d[b];v++)for(let u=0;u<d[a];u++){if(masks?.[plane]&&!masks[plane][u+v*d[a]])continue;const line=[];for(let n=0;n<d[axis];n++){const p=[0,0,0];p[a]=u;p[b]=v;p[axis]=n;line.push(p.join(','));}if(line.every(p=>!occupied.has(p)))line.forEach(p=>removed.add(p));}
 const cells=[];for(let x=0;x<d[0];x++)for(let y=0;y<d[1];y++)for(let z=0;z<d[2];z++)if(!removed.has([x,y,z].join(',')))cells.push({xyz:[x,y,z],shape:0});return cells;
}
