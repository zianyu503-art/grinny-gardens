import * as THREE from 'three';
import { spawn } from './assets.js';
import { audio } from './audio.js';

const RANGE = 20, SPEED = 42;

/** Two launchable claws worn on the forearms (GrabPack-style). */
export class ClawPack {
  constructor(camera, game) {
    this.camera = camera;
    this.game = game;
    this.enabled = false;
    const vm = (this.view = spawn('clawpack'));
    vm.rotation.y = Math.PI; // model faces +Z, the camera looks down -Z
    vm.position.set(0, -0.3, -0.36);
    vm.scale.setScalar(0.5);
    vm.visible = false;
    vm.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.renderOrder = 10; } });
    camera.add(vm);
    this.ray = new THREE.Raycaster();
    this.ray.far = RANGE;
    // after the 180° turn the model's right part sits on screen-left
    this.hands = [this.makeHand('HeadR', 0x2a7aff), this.makeHand('HeadL', 0xff3a2a)];
  }

  makeHand(partName, color) {
    const head = this.view.getObjectByName(partName);
    const rest = head.position.clone();
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([rest, rest]),
      new THREE.LineBasicMaterial({ color: 0x222222 }));
    line.frustumCulled = false;
    this.view.add(line);
    const glow = new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), new THREE.MeshBasicMaterial({ color: 0x5ab8ff }));
    glow.visible = false;
    head.add(glow);
    const light = new THREE.PointLight(0x5ab8ff, 0, 2.5, 2);
    head.add(light);
    return { head, rest, line, glow, light, state: 'idle', t: 0, target: new THREE.Vector3(), hit: null, carry: null,
      charged: 0, hum: null };
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
    for (let i = 0; i < 2; i++) {
      const h = this.hands[i];
      if (h.charged > 0) {
        h.charged -= dt;
        if (h.charged <= 0) this.discharge(i);
      }
      const on = h.charged > 0;
      h.glow.visible = on;
      h.light.intensity = on ? 1.2 + Math.random() * 0.6 : 0;

      const worldTarget = this.view.worldToLocal(h.target.clone());
      if (h.state === 'out') {
        h.t += (dt * SPEED) / Math.max(1, h.dist);
        if (h.t >= 1) {
          h.t = 1; h.state = 'hold'; h.holdT = 0.22;
          audio.clawGrab();
          this.game.onClawHit(i, h.hit, h.target.clone(), h);
        }
      } else if (h.state === 'hold') {
        h.holdT -= dt;
        if (h.holdT <= 0) h.state = 'back';
      } else if (h.state === 'back') {
        h.t -= (dt * SPEED * 1.3) / Math.max(1, h.dist);
        if (h.t <= 0) {
          h.t = 0; h.state = 'idle';
          if (h.carry) { const c = h.carry; h.carry = null; this.game.onClawReturn(i, c); }
        }
      }
      // ease the claw head between its rest pose and the target
      const k = h.state === 'idle' ? 0 : h.t;
      h.head.position.lerpVectors(h.rest, worldTarget, k);
      if (h.carry) h.carry.position.copy(h.head.getWorldPosition(new THREE.Vector3()));
      const pos = h.line.geometry.attributes.position;
      pos.setXYZ(0, h.rest.x, h.rest.y, h.rest.z + 0.06);
      pos.setXYZ(1, h.head.position.x, h.head.position.y, h.head.position.z);
      pos.needsUpdate = true;
      h.line.visible = h.state !== 'idle';
    }
    // gentle sway
    this.view.position.y = -0.3 + Math.sin(performance.now() / 700) * 0.004;
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
