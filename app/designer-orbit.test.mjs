import assert from 'node:assert/strict';
import * as THREE from './vendor/package/build/three.module.js';
import {designerBounds,keepCentredOrbit} from './designer-orbit.js';
const geometry=new THREE.BoxGeometry(.97,.97,.97),doc={dimensions:[10,10,10],cells:[{xyz:[1,1,2],shape:0},{xyz:[1,4,2],shape:0}]};
const bounds=designerBounds(THREE,doc,()=>geometry),centre=bounds.getCenter(new THREE.Vector3());
assert.deepEqual(centre.toArray(),[-3.5,3,-2.5]);assert.notDeepEqual(centre.toArray(),[0,5,0]);
const camera=new THREE.PerspectiveCamera(),controls={target:centre.clone()};const offset=new THREE.Vector3(13,5,17);camera.position.copy(centre).add(offset);camera.lookAt(centre);
assert.ok(controls.target.distanceTo(centre)<1e-10);assert.ok(camera.position.clone().sub(centre).distanceTo(offset)<1e-10);
for(const angle of [0,.8,2,4]){const orbited=offset.clone().applyAxisAngle(new THREE.Vector3(0,1,0),angle).add(controls.target);camera.position.copy(orbited);camera.lookAt(controls.target);camera.updateMatrixWorld();const screen=centre.clone().project(camera);assert.ok(Math.abs(screen.x)<1e-10&&Math.abs(screen.y)<1e-10);}
assert.deepEqual(designerBounds(THREE,{dimensions:[6,4,8],cells:[]},()=>geometry).getCenter(new THREE.Vector3()).toArray(),[0,2,0]);
console.log('PASS: object-centred fitting keeps the pivot fixed throughout an orbit; empty builds retain their grid centre.');

// Exercise the real viewer control, including its damped pan and rotation state.
const {readFileSync}=await import('node:fs');
const controlSource=readFileSync(new URL('./vendor/package/examples/jsm/controls/OrbitControls.js',import.meta.url),'utf8').replace("from 'three'",`from '${new URL('./vendor/package/build/three.module.js',import.meta.url).href}'`);
const {OrbitControls}=await import('data:text/javascript;base64,'+Buffer.from(controlSource).toString('base64'));
for(const damping of [false,true]){
 const cam=new THREE.PerspectiveCamera(38,1.6,.05,200);cam.position.copy(centre).add(offset);cam.lookAt(centre);
 const orbit=new OrbitControls(cam,null);orbit.target.copy(centre);orbit.enableDamping=damping;orbit.dampingFactor=.12;orbit.update();
 keepCentredOrbit(THREE,orbit,()=>centre);
 const settle=()=>{for(let i=0;i<220;i++)orbit.update();cam.updateMatrixWorld();};
 const turn=()=>{orbit._rotateLeft(.4);orbit._rotateUp(.16);settle();};
 turn();assert.ok(orbit.target.distanceTo(centre)<1e-8);
 const q=cam.quaternion.clone(),radius=cam.position.distanceTo(orbit.target);
 orbit._panOffset.set(2,-.7,.5);settle();
 assert.ok(q.angleTo(cam.quaternion)<1e-7,'Pan must not change orientation');
 assert.ok(Math.abs(radius-cam.position.distanceTo(orbit.target))<1e-8,'Pan must not change zoom');
 const screen=centre.clone().project(cam),distance=cam.position.distanceTo(centre);
 for(let i=0;i<4;i++){turn();assert.ok(centre.clone().project(cam).distanceTo(screen)<1e-7,'Panned centre must stay fixed on screen while orbiting');assert.ok(Math.abs(cam.position.distanceTo(centre)-distance)<1e-7,'Camera must orbit the geometric centre after pan');}
 orbit._scale=.8;settle();assert.ok(cam.position.distanceTo(orbit.target)<radius,'Zoom still works after pan/orbit');
}
console.log('PASS: real OrbitControls preserves object-centred rotation after pan, with damping, orientation and zoom.');
