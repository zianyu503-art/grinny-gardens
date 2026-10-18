import * as THREE from 'three';
import { spawn } from './assets.js';
import { audio } from './audio.js';

const RANGE = 20, SPEED = 42;
const HAND_SCALE = 0.15;               // source model is ~1.5 units tall -> ~17 cm on screen
const DOWN_TO_FORWARD = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
const FWD = new THREE.Vector3(0, 0, -1);
const UP = new THREE.Vector3(0, 1, 0);

/**
 * Two launchable claw hands (the player's own ClawPack.blend model, GrabPack-style).
 * The blue hand sits lower-left on screen (left mouse), the red one lower-right (right mouse).
 */
export class ClawPack {
  constructor(camera, game) {
    this.camera = camera;
    this.game = game;
    this.enabled = false;
    this.view = new THREE.Group();
    this.view.visible = false;
    camera.add(this.view);
    this.ray = new THREE.Raycaster();
    this.ray.far = RANGE;
    const src = spawn('clawhands');
    this.hands = [
      this.makeHand(src, 'L', new THREE.Vector3(-0.21, -0.19, -0.4), 0x5ab8ff),
      this.makeHand(src, 'R', new THREE.Vector3(0.21, -0.19, -0.4), 0xff6a4a),
    ];
  }

  makeHand(src, side, rest, glowColor) {
    const head = new THREE.Group();
    const body = src.getObjectByName('Hand' + side).clone();
    const origin = body.position.clone();
    body.position.set(0, 0, 0);
    head.add(body);
    // each finger pivots on its top hinge; opening swings it outward from the hand's axis
    const jaws = [];
    for (let k = 0; k < 3; k++) {
      const j = src.getObjectByName(`Jaw${side}${k}`);
      if (!j) continue;
      const pivot = new THREE.Group();
      pivot.position.copy(j.position).sub(origin);
      const mesh = j.clone();
      mesh.position.set(0, 0, 0);
      pivot.add(mesh);
      const radial = new THREE.Vector3(pivot.position.x, 0, pivot.position.z).normalize();
      pivot.userData.axis = new THREE.Vector3().crossVectors(radial, UP).normalize();
      head.add(pivot);
      jaws.push(pivot);
    }
    head.scale.setScalar(HAND_SCALE);
    head.quaternion.copy(DOWN_TO_FORWARD);
    head.position.copy(rest);
    head.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; o.renderOrder = 10; } });
    this.view.add(head);

    // rubber cable from behind the shoulder to the back of the hand
    const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.007, 0.007, 1, 6, 1, true).translate(0, 0.5, 0),
      new THREE.MeshStandardMaterial({ color: 0x0b0c0d, roughness: 0.55, metalness: 0.1 }));
    cable.frustumCulled = false;
    this.view.add(cable);
    const anchor = new THREE.Vector3(rest.x * 1.6, -0.42, 0.15);

    const glow = new THREE.PointLight(glowColor, 0, 1.6, 2);
    glow.position.set(0, -0.6, 0);
    head.add(glow);
    // at rest the claw leans in toward the crosshair and up, so its side and fingers read on screen
    const restDir = new THREE.Vector3(-rest.x * 2.2, 0.75, -1).normalize();
    return { head, rest, restDir, jaws, cable, anchor, glow, state: 'idle', t: 0, open: 0.15, target: new THREE.Vector3(),
      hit: null, carry: null, charged: 0, hum: null, kick: 0, dir: restDir.clone() };
  }

  show(on) { this.enabled = on; this.view.visible = on; }

  /** What the crosshair points at (for the HUD). */
  aim(targets) {
    this.ray.setFromCamera({ x: 0, y: 0 }, this.camera);
    const hits = this.ray.intersectObjects(targets, true);
    const first = hits[0] ? { point: hits[0].point, interact: findInteract(hits[0].object), distance: hits[0].distance } : null;
    if (first?.interact) return first;
    // aim assist: snap to an interactable close to the crosshair that is not hidden behind the first hit
    const cam = this.camera.getWorldPosition(new THREE.Vector3());
    let best = null, bestScore = 0.12;
    for (const t of targets) {
      const it = t.userData.interact;
      if (!it || !t.visible || !t.parent) continue;
      const c = it.aimPoint || (it._box ||= new THREE.Box3()).setFromObject(t).getCenter(new THREE.Vector3());
      const d = c.distanceTo(cam);
      if (d > RANGE || (first && d > first.distance + 0.8)) continue;
      const ndc = c.clone().project(this.camera);
      if (ndc.z > 1) continue;
      const score = Math.hypot(ndc.x, ndc.y * this.camera.aspect ** -1);
      if (score < bestScore) { bestScore = score; best = { point: c, interact: it, distance: d }; }
    }
    return best || first;
  }

  fire(index, targets) {
    const h = this.hands[index];
    if (!this.enabled || h.state !== 'idle') return;
    const a = this.aim(targets);
    const dir = this.camera.getWorldDirection(new THREE.Vector3());
    h.target.copy(a ? a.point : this.camera.getWorldPosition(new THREE.Vector3()).addScaledVector(dir, RANGE));
    h.hit = a;
    h.state = 'out'; h.t = 0;
    h.dist = a ? a.distance : RANGE;
    h.kick = 1;
    audio.clawFire();
  }

  charge(index, seconds = 14) {
    const h = this.hands[index];
    h.charged = seconds;
    if (!h.hum) h.hum = audio.hum();
  }

  discharge(index) {
    const h = this.hands[index];
    h.charged = 0;
    h.hum?.(); h.hum = null;
  }

  update(dt) {
    const now = performance.now() / 1000;
    for (let i = 0; i < 2; i++) {
      const h = this.hands[i];
      if (h.charged > 0) {
        h.charged -= dt;
        if (h.charged <= 0) this.discharge(i);
      }
      h.glow.intensity = h.charged > 0 ? 1.4 + Math.random() * 0.8 : 0;

      const local = this.view.worldToLocal(h.target.clone());
      let wantOpen = 0.12 + Math.sin(now * 1.3 + i) * 0.03;
      if (h.state === 'out') {
        h.t += (dt * SPEED) / Math.max(1, h.dist);
        wantOpen = 0.75;
        if (h.t >= 1) {
          h.t = 1; h.state = 'hold'; h.holdT = 0.22;
          audio.clawGrab();
          this.game.onClawHit(i, h.hit, h.target.clone(), h);
        }
      } else if (h.state === 'hold') {
        wantOpen = -0.08;
        h.holdT -= dt;
        if (h.holdT <= 0) h.state = 'back';
      } else if (h.state === 'back') {
        wantOpen = h.carry ? -0.08 : 0.05;
        h.t -= (dt * SPEED * 1.3) / Math.max(1, h.dist);
        if (h.t <= 0) {
          h.t = 0; h.state = 'idle';
          if (h.carry) { const c = h.carry; h.carry = null; this.game.onClawReturn(i, c); }
        }
      }
      // fingers
      h.open += (wantOpen - h.open) * Math.min(1, dt * 14);
      for (const j of h.jaws) j.quaternion.setFromAxisAngle(j.userData.axis, h.open);

      // position: idle bob + recoil, or flying toward the target
      h.kick = Math.max(0, h.kick - dt * 5);
      const idle = h.rest.clone();
      idle.y += Math.sin(now * 1.7 + i * 1.3) * 0.004;
      idle.z += h.kick * 0.05;
      const k = h.state === 'idle' ? 0 : h.t;
      h.head.position.lerpVectors(idle, local, k);
      // point the jaws at what they fly toward, settle back when idle
      if (h.state !== 'idle') h.dir.copy(local).sub(h.rest).normalize();
      else h.dir.lerp(h.restDir, Math.min(1, dt * 8)).normalize();
      h.head.quaternion.setFromUnitVectors(FWD, h.dir).multiply(DOWN_TO_FORWARD);
      if (h.carry) h.carry.position.copy(h.head.getWorldPosition(new THREE.Vector3()));

      // cable: anchor behind the shoulder -> back of the hand
      const back = h.head.position.clone().addScaledVector(h.dir, -0.01);
      const span = back.clone().sub(h.anchor);
      h.cable.position.copy(h.anchor);
      h.cable.scale.set(1, span.length(), 1);
      h.cable.quaternion.setFromUnitVectors(UP, span.normalize());
    }
  }

  state(i) { const h = this.hands[i]; return { charged: h.charged > 0, out: h.state !== 'idle' }; }
}

export function findInteract(o) {
  while (o) {
    if (o.userData.interact) return o.userData.interact;
    o = o.parent;
  }
  return null;
}
