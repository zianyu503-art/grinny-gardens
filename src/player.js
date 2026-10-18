import * as THREE from 'three';
import { audio } from './audio.js';

const EYE = 1.62, EYE_CROUCH = 1.0;

export class Player {
  constructor(camera, scene) {
    this.camera = camera;
    camera.rotation.order = 'YXZ';
    scene.add(camera);
    this.pos = new THREE.Vector3();
    this.yaw = 0; this.pitch = 0;
    this.radius = 0.35;
    this.eye = EYE;
    this.crouched = false;
    this.stamina = 100;
    this.staminaLock = 0;
    this.battery = 100;
    this.flashOn = true;
    this.noise = 0;
    this.speed = 0;
    this.bob = 0;
    this.stepDist = 0;
    this.shakeAmt = 0;
    this.frozen = false;
    this.lookTarget = null;
    this.adrenaline = false;
    this.surface = 'ground';

    const fl = (this.flashlight = new THREE.SpotLight(0xffe2b8, 45, 40, 0.46, 0.55, 1.0));
    fl.castShadow = true;
    fl.shadow.mapSize.set(1024, 1024);
    fl.shadow.camera.near = 0.2;
    fl.shadow.bias = -0.0004;
    fl.position.set(0.18, -0.12, 0.05);
    fl.target.position.set(0, -0.05, -1);
    camera.add(fl, fl.target);
    // faint fill so the player always sees a little around them
    this.fill = new THREE.PointLight(0xa0a8c0, 1.2, 6, 2);
    camera.add(this.fill);
  }

  place(x, z, yaw = 0) {
    this.pos.set(x, 0, z);
    this.yaw = yaw; this.pitch = 0;
    this.lookTarget = null;
    this.syncCamera(0);
  }

  get forward() { return new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw)); }

  shake(a) { this.shakeAmt = Math.max(this.shakeAmt, a); }

  /** Smoothly turn the head to look at a world point (cinematics). */
  look(target, speed = 3) { this.lookTarget = { target, speed }; }

  update(dt, input, physics) {
    // ---------------------------------------------------- look
    const m = input.consumeMouse();
    if (this.lookTarget) {
      const p = this.lookTarget.target;
      const dx = p.x - this.pos.x, dz = p.z - this.pos.z;
      const wantYaw = Math.atan2(-dx, -dz);
      const wantPitch = Math.atan2(p.y - (this.pos.y + this.eye), Math.hypot(dx, dz));
      let d = wantYaw - this.yaw;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      const k = Math.min(1, dt * this.lookTarget.speed);
      this.yaw += d * k;
      this.pitch += (wantPitch - this.pitch) * k;
    } else if (!this.frozen) {
      this.yaw -= m.x * 0.0022;
      this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch - m.y * 0.0022));
    }

    // ---------------------------------------------------- move
    let mx = 0, mz = 0;
    if (!this.frozen) {
      if (input.down('KeyW')) mz -= 1;
      if (input.down('KeyS')) mz += 1;
      if (input.down('KeyA')) mx -= 1;
      if (input.down('KeyD')) mx += 1;
      if (input.axis.active) { mx = input.axis.x; mz = input.axis.z; }
      if (input.hit('KeyC') || input.hit('ControlLeft')) this.crouched = !this.crouched;
      if (input.hit('KeyF')) this.toggleFlash();
    }
    const stick = Math.min(1, Math.hypot(mx, mz));
    const moving = stick > 0.12;
    if (!moving) { mx = 0; mz = 0; }
    // touch: pushing the stick to the rim (forward) sprints
    const wantSprint = input.down('ShiftLeft') || input.down('ShiftRight') || (input.axis.active && stick > 0.93);
    const canSprint = wantSprint && moving && this.staminaLock <= 0 && mz <= 0;
    if (canSprint) this.crouched = false;
    let speed = this.crouched ? 1.45 : canSprint ? 5.9 : 2.9;
    if (input.axis.active && !canSprint) speed *= Math.max(0.35, stick);
    if (canSprint) {
      this.stamina -= dt * (this.adrenaline ? 7 : 20);
      if (this.stamina <= 0) { this.stamina = 0; this.staminaLock = 2.5; }
    } else {
      this.staminaLock -= dt;
      if (this.staminaLock <= 0) this.stamina = Math.min(100, this.stamina + dt * (moving ? 10 : 18));
    }
    if (moving) {
      const len = Math.hypot(mx, mz);
      mx /= len; mz /= len;
      const s = Math.sin(this.yaw), c = Math.cos(this.yaw);
      const vx = (mx * c + mz * s) * speed, vz = (-mx * s + mz * c) * speed;
      const before = this.pos.clone();
      const r = physics.resolve(this.pos.x + vx * dt, this.pos.z + vz * dt, this.radius);
      this.pos.x = r.x; this.pos.z = r.z;
      const moved = this.pos.distanceTo(before);
      this.speed = moved / Math.max(dt, 1e-4);
      this.stepDist += moved;
      const stride = canSprint ? 1.9 : this.crouched ? 0.9 : 1.35;
      if (this.stepDist > stride) {
        this.stepDist = 0;
        audio.footstep(canSprint ? 0.5 : this.crouched ? 0.08 : 0.25, this.surface);
      }
      this.bob += dt * (canSprint ? 13 : this.crouched ? 6 : 8.5);
    } else {
      this.speed = 0;
    }
    // how far the player can be heard (metres)
    this.noise = !moving ? 0 : canSprint ? 14 : this.crouched ? 1.6 : 6;
    this.sprinting = canSprint;

    // ---------------------------------------------------- flashlight battery
    if (this.flashOn) {
      this.battery -= dt * 0.5;
      if (this.battery <= 0) { this.battery = 0; this.flashOn = false; audio.clawGrab(); }
    }
    let flicker = 1;
    if (this.flashOn && this.battery < 15 && Math.random() < 0.08) flicker = Math.random() * 0.4;
    if (this.flickerOverride !== undefined) flicker = this.flickerOverride;
    this.flashlight.intensity = this.flashOn ? 45 * flicker * (0.6 + 0.4 * Math.min(1, this.battery / 30)) : 0;

    this.eye += ((this.crouched ? EYE_CROUCH : EYE) - this.eye) * Math.min(1, dt * 10);
    this.syncCamera(dt);
  }

  toggleFlash() {
    if (this.battery <= 0) { this.flashOn = false; return; }
    this.flashOn = !this.flashOn;
    audio.clawGrab();
  }

  syncCamera(dt) {
    const bobY = Math.sin(this.bob) * 0.045 * Math.min(1, this.speed / 3);
    const bobX = Math.cos(this.bob * 0.5) * 0.03 * Math.min(1, this.speed / 3);
    this.shakeAmt = Math.max(0, this.shakeAmt - dt * 1.5);
    const sh = this.shakeAmt;
    this.camera.position.set(
      this.pos.x + bobX + (Math.random() - 0.5) * sh * 0.1,
      this.pos.y + this.eye + bobY + (Math.random() - 0.5) * sh * 0.1,
      this.pos.z + (Math.random() - 0.5) * sh * 0.1);
    this.camera.rotation.set(this.pitch + (Math.random() - 0.5) * sh * 0.03, this.yaw, (Math.random() - 0.5) * sh * 0.02);
  }
}
