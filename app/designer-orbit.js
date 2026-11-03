// Use the complete object, not its build-space midpoint or visible slice.
export function designerBounds(THREE,document,geometryForShape,sourceBounds=null){
 if(sourceBounds&&!sourceBounds.isEmpty())return sourceBounds.clone();
 const bounds=new THREE.Box3(),offset=new THREE.Vector3(),min=new THREE.Vector3(),max=new THREE.Vector3(),d=document.dimensions;
 for(const cell of document.cells){const geometry=geometryForShape(cell.shape);if(!geometry.boundingBox)geometry.computeBoundingBox();offset.set(cell.xyz[0]+.5-d[0]/2,cell.xyz[1]+.5,cell.xyz[2]+.5-d[2]/2);bounds.expandByPoint(min.copy(geometry.boundingBox.min).add(offset));bounds.expandByPoint(max.copy(geometry.boundingBox.max).add(offset));}
 if(bounds.isEmpty())bounds.set(new THREE.Vector3(-d[0]/2,0,-d[2]/2),new THREE.Vector3(d[0]/2,d[1],d[2]/2));
 return bounds;
}

// OrbitControls pans its target. Carry that screen offset with camera rotation,
// so orbiting still rotates the camera around the object's geometric centre.
// Pan/zoom/damping remain owned by the existing control.
export function keepCentredOrbit(THREE,controls,centreForObject){
 const update=controls.update.bind(controls),before=new THREE.Quaternion(),rotation=new THREE.Quaternion(),pan=new THREE.Vector3(),shift=new THREE.Vector3();
 controls.update=function(...args){
  before.copy(this.object.quaternion);
  const changed=update(...args),centre=centreForObject();
  if(!centre)return changed;
  rotation.copy(this.object.quaternion).multiply(before.invert());
  pan.copy(this.target).sub(centre);
  shift.copy(pan).applyQuaternion(rotation).sub(pan);
  this.target.add(shift);this.object.position.add(shift);
  this.object.updateMatrixWorld();
  return changed;
 };
}
