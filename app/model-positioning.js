// Imported files often put their origin at a foot/corner. A centred parent
// gives mouse rotation, axis buttons and the gizmo the same physical pivot.
export function centredModel(THREE,object){object.updateMatrixWorld(true);const centre=new THREE.Box3().setFromObject(object).getCenter(new THREE.Vector3()),pivot=new THREE.Group(),offset=new THREE.Group();offset.position.copy(centre).negate();offset.add(object);pivot.add(offset);return pivot;}
export function originalPosition(object){return {position:object.position.clone(),quaternion:object.quaternion.clone(),scale:object.scale.clone()};}
export function resetPosition(object,original){object.position.copy(original.position);object.quaternion.copy(original.quaternion);object.scale.copy(original.scale);object.updateMatrixWorld(true);}
