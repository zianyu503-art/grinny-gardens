import * as THREE from 'three';
import { spawn } from './assets.js';
import { audio } from './audio.js';

const tmp = new THREE.Vector3();

class Monster {
  constructor(game, model, x, z, radius = 0.5) {
    this.game = game;
    this.obj = spawn(model);
    this.obj.position.set(x, 0, z);
    game.scene.add(this.obj);
    this.radius = radius;
    this.path = null;
    this.repath = 0;
    this.active = false;
    this.t = Math.random() * 10;
    const clips = this.obj.userData.animations || [];
    if (clips.length) {
      this.mixer = new THREE.AnimationMixer(this.obj);
      this.actions = Object.fromEntries(clips.map((c) => [c.name, this.mixer.clipAction(c)]));
    }
    this.current = null;
  }

  get pos() { return this.obj.position; }
  set visible(v) { this.obj.visible = v; }
  get visible() { return this.obj.visible; }

  play(name, fade = 0.3, timeScale = 1) {
    if (!this.actions) return;
    const a = this.actions[name];
    a.timeScale = timeScale;
    if (this.current === a) return;
    a.reset().setEffectiveWeight(1).fadeIn(fade).play();
    if (this.current) this.current.fadeOut(fade);
    this.current = a;
  }

  playOnce(name, timeScale = 1) {
    const a = this.actions?.[name];
    if (!a) return;
    a.setLoop(THREE.LoopOnce, 1);
    a.clampWhenFinished = true;
    this.play(name, 0.1, timeScale);
  }

  distTo(p) { return Math.hypot(p.x - this.pos.x, p.z - this.pos.z); }

  face(x, z, dt, rate = 8) {
    const want = Math.atan2(x - this.pos.x, z - this.pos.z);
    let d = want - this.obj.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.obj.rotation.y += d * Math.min(1, dt * rate);
  }

  /** Walk toward (x, z) using A*; returns true when arrived. */
  goTo(x, z, speed, dt, repathEvery = 0.5) {
    const ph = this.game.physics;
    this.repath -= dt;
    if (!this.path || this.repath <= 0 || this.goal?.x !== x || this.goal?.z !== z) {
      if (this.repath <= 0 || !this.path) {
        this.path = ph.path(this.pos.x, this.pos.z, x, z) || [{ x, z }];
        this.goal = { x, z };
        this.repath = repathEvery;
      }
    }
    let step = speed * dt;
    while (step > 0 && this.path.length) {
      const wp = this.path[0];
      const dx = wp.x - this.pos.x, dz = wp.z - this.pos.z;
      const d = Math.hypot(dx, dz);
      if (d < 0.05) { this.path.shift(); continue; }
      const s = Math.min(step, d);
      this.pos.x += (dx / d) * s; this.pos.z += (dz / d) * s;
      this.face(wp.x, wp.z, dt);
      step -= s;
      if (s === d) this.path.shift();
    }
    const r = ph.resolve(this.pos.x, this.pos.z, this.radius);
    this.pos.x = r.x; this.pos.z = r.z;
    return Math.hypot(x - this.pos.x, z - this.pos.z) < 0.6;
  }

  update(dt) { this.mixer?.update(dt); }
}

// ------------------------------------------------------------------------- bone horse
const SHATTER_TIME = 5;   // seconds until a shattered horse has pulled itself back together
const MEND_TIME = 1.2;    // the last part of it, when the pieces fly back
let shardSet = null;      // the horse mesh cut into chunks, in horse-root space (shared by all horses)

function horseShards(root) {
  if (shardSet) return shardSet;
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert();
  const cells = new Map();
  const C = 0.38;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry.toNonIndexed();
    g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    const pos = g.attributes.position, nor = g.attributes.normal, uv = g.attributes.uv;
    for (let t = 0; t < pos.count; t += 3) {
      const cx = (pos.getX(t) + pos.getX(t + 1) + pos.getX(t + 2)) / 3;
      const cy = (pos.getY(t) + pos.getY(t + 1) + pos.getY(t + 2)) / 3;
      const cz = (pos.getZ(t) + pos.getZ(t + 1) + pos.getZ(t + 2)) / 3;
      const key = `${Math.floor(cx / C)},${Math.floor(cy / C)},${Math.floor(cz / C)}`;
      let c = cells.get(key);
      if (!c) cells.set(key, (c = { p: [], n: [], uv: [], mat: o.material }));
      for (let k = t; k < t + 3; k++) {
        c.p.push(pos.getX(k), pos.getY(k), pos.getZ(k));
        if (nor) c.n.push(nor.getX(k), nor.getY(k), nor.getZ(k));
        if (uv) c.uv.push(uv.getX(k), uv.getY(k));
      }
    }
  });
  shardSet = [...cells.values()].filter((c) => c.p.length >= 9 * 3).map((c) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(c.p, 3));
    if (c.n.length) g.setAttribute('normal', new THREE.Float32BufferAttribute(c.n, 3));
    if (c.uv.length) g.setAttribute('uv', new THREE.Float32BufferAttribute(c.uv, 2));
    g.computeBoundingBox();
    const home = g.boundingBox.getCenter(new THREE.Vector3());
    g.translate(-home.x, -home.y, -home.z);
    return { geo: g, mat: c.mat, home };
  });
  return shardSet;
}

/** Only moves while nobody is looking at it with a light. A claw hit shatters it for a few seconds. */
export class Horse extends Monster {
  constructor(game, x, z, rot) {
    super(game, 'horse', x, z, 0.55);
    this.obj.rotation.y = rot;
    this.frozen = true;
    this.stepT = 0;
    this.wasMoving = false;
    this.baseY = 0;
    this.broken = 0;
    this.shards = null;
  }

  /** Burst into pieces, flung away from `from` (the claw's hit point). */
  shatter(from) {
    if (this.broken > 0) return;
    const set = horseShards(this.obj);
    this.obj.updateMatrixWorld(true);
    const m = this.obj.matrixWorld;
    this.broken = SHATTER_TIME;
    this.obj.visible = false;
    this.path = null;
    const rt = this.game.level.rayTargets, i = rt.indexOf(this.obj);
    if (i >= 0) rt.splice(i, 1);
    const q = new THREE.Quaternion().setFromRotationMatrix(m);
    this.shards = set.map((s) => {
      const mesh = new THREE.Mesh(s.geo, s.mat);
      mesh.position.copy(s.home).applyMatrix4(m);
      mesh.quaternion.copy(q);
      this.game.scene.add(mesh);
      const away = tmp.copy(mesh.position).sub(from).setY(0).normalize();
      const vel = new THREE.Vector3(away.x * (2 + Math.random() * 3) + (Math.random() - 0.5) * 2, 2 + Math.random() * 3.5,
        away.z * (2 + Math.random() * 3) + (Math.random() - 0.5) * 2);
      const spin = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(14);
      return { mesh, vel, spin, rest: null, from: null, fromQ: null };
    });
    audio.boneShatter(this.pos);
    this.game.noiseAt(this.pos.x, this.pos.z, 18);
  }

  /** Put the horse back together at once (respawn / zone reset). */
  mend() {
    if (!this.shards) return;
    for (const s of this.shards) s.mesh.removeFromParent();
    this.shards = null;
    this.broken = 0;
    this.obj.visible = true;
    const rt = this.game.level.rayTargets;
    if (!rt.includes(this.obj)) rt.push(this.obj);
  }

  updateShards(dt) {
    const prev = this.broken;
    this.broken -= dt;
    if (this.broken <= 0) { this.mend(); audio.creak(this.pos, 0.7); return; }
    const set = horseShards(this.obj);
    if (prev > MEND_TIME && this.broken <= MEND_TIME) {
      audio.boneMend(this.pos);
      this.obj.updateMatrixWorld(true);
      this.shards.forEach((s) => { s.from = s.mesh.position.clone(); s.fromQ = s.mesh.quaternion.clone(); });
    }
    const m = this.obj.matrixWorld, q = new THREE.Quaternion().setFromRotationMatrix(m);
    this.shards.forEach((s, i) => {
      const mesh = s.mesh;
      if (this.broken > MEND_TIME) {
        // tumble and bounce on the ground
        s.vel.y -= 14 * dt;
        mesh.position.addScaledVector(s.vel, dt);
        if (mesh.position.y < 0.08) {
          mesh.position.y = 0.08;
          s.vel.y *= -0.3; s.vel.x *= 0.6; s.vel.z *= 0.6; s.spin.multiplyScalar(0.6);
        }
        mesh.rotation.x += s.spin.x * dt; mesh.rotation.y += s.spin.y * dt; mesh.rotation.z += s.spin.z * dt;
        // a twitch now and then, like it is trying to get up
        if (Math.random() < dt * 0.6) { s.vel.y += 1.5; s.spin.set(Math.random() - 0.5, 0, Math.random() - 0.5).multiplyScalar(10); }
      } else {
        // pulled back into shape, the far pieces first
        const k = 1 - this.broken / MEND_TIME;
        const e = Math.min(1, Math.max(0, k * 1.4 - (i % 5) * 0.08));
        const ease = e * e * (3 - 2 * e);
        const target = tmp.copy(set[i].home).applyMatrix4(m);
        mesh.position.lerpVectors(s.from, target, ease);
        mesh.position.y += Math.sin(ease * Math.PI) * 0.6;
        mesh.quaternion.slerpQuaternions(s.fromQ, q, ease);
      }
    });
  }

  update(dt) {
    super.update(dt);
    if (this.broken > 0) { this.updateShards(dt); return; }
    if (!this.active) return;
    const g = this.game, p = g.player.pos;
    const head = tmp.set(this.pos.x, 1.6, this.pos.z);
    const seen = g.inView(head, 0.9) && g.physics.lineClear(p.x, p.z, this.pos.x, this.pos.z);
    const lit = seen && g.litByFlashlight(head);
    this.frozen = lit;
    this.seen = seen;
    if (lit) {
      if (this.wasMoving) { this.wasMoving = false; audio.creak(this.pos, 0.6); }
      return;
    }
    this.wasMoving = true;
    const speed = g.player.flashOn ? 2.5 : 3.6;
    this.goTo(p.x, p.z, speed, dt, 0.4);
    this.t += dt;
    // jerky hop along the ground, pole scraping
    this.obj.position.y = Math.abs(Math.sin(this.t * 7)) * 0.18;
    this.obj.rotation.z = Math.sin(this.t * 3.5) * 0.08;
    this.stepT -= dt;
    if (this.stepT <= 0) { audio.horseStep(this.pos); this.stepT = 0.22 + Math.random() * 0.1; }
    if (this.distTo(p) < 1.25) g.caught(this, '骨馬只在你看不見牠們的時候移動。用手電筒照住牠們。');
  }
}

// ------------------------------------------------------------------------- Hornman
/** Blind. Hunts by sound. */
export class Hornman extends Monster {
  constructor(game, waypoints) {
    const start = waypoints[0];
    super(game, 'hornman', start.x, start.z, 0.45);
    this.waypoints = waypoints;
    this.wp = 1;
    this.state = 'patrol';
    this.timer = 0;
    this.honkT = 4;
    this.stepT = 0;
    this.target = null;
    this.play('Walk', 0.1, 0.8);
  }

  reset() {
    const s = this.waypoints[0];
    this.pos.set(s.x, 0, s.z);
    this.state = 'patrol'; this.wp = 1; this.path = null; this.target = null;
  }

  hear(x, z, radius) {
    const d = Math.hypot(x - this.pos.x, z - this.pos.z);
    const clear = this.game.physics.lineClear(x, z, this.pos.x, this.pos.z);
    if (d < radius * (clear ? 1 : 0.6)) {
      const first = this.state !== 'hunt';
      this.state = 'hunt';
      this.target = { x, z };
      this.path = null;
      if (first) { audio.horn(this.pos, 0.9); this.honkT = 3; }
      return true;
    }
    return false;
  }

  update(dt) {
    super.update(dt);
    if (!this.active) return;
    const g = this.game, p = g.player.pos;
    if (g.player.noise > 0) this.hear(p.x, p.z, g.player.noise);
    const d = this.distTo(p);
    if (this.state === 'patrol') {
      const w = this.waypoints[this.wp];
      this.play('Walk', 0.4, 0.8);
      if (this.goTo(w.x, w.z, 1.3, dt, 1.0)) {
        this.state = 'listen'; this.timer = 2.5 + Math.random() * 2;
        this.wp = (this.wp + 1 + Math.floor(Math.random() * (this.waypoints.length - 1))) % this.waypoints.length;
      }
    } else if (this.state === 'hunt') {
      this.play('Walk', 0.3, 1.7);
      if (this.goTo(this.target.x, this.target.z, 2.9, dt, 0.4)) {
        this.state = 'listen'; this.timer = 4;
      }
    } else if (this.state === 'listen') {
      this.play('Listen', 0.5, 1);
      this.timer -= dt;
      if (this.timer <= 0) this.state = 'patrol';
    }
    this.stepT -= dt;
    if (this.state !== 'listen' && this.stepT <= 0) {
      audio.horseStep(this.pos);
      this.stepT = this.state === 'hunt' ? 0.38 : 0.7;
    }
    this.honkT -= dt;
    if (this.honkT <= 0) { audio.horn(this.pos, 0.55); this.honkT = 5 + Math.random() * 6; }
    const loud = g.player.noise > 1.7;
    if (d < 1.15 || (d < 2.6 && loud)) g.caught(this, '喇叭先生看不見，只聽得到。按 C 蹲下慢慢走，用爪子打牆製造聲響可以引開他。');
  }
}

// ------------------------------------------------------------------------- Grinny
export class Grinny extends Monster {
  constructor(game, x, z) {
    super(game, 'grinny', x, z, 0.7);
    this.state = 'idle';
    this.stepT = 0;
    this.giggleT = 2;
    this.play('Idle', 0);
  }

  update(dt) {
    super.update(dt);
    const g = this.game, p = g.player.pos;
    if (this.state === 'chase') {
      this.play('Run', 0.2, 1.25);
      this.speed = Math.min(this.maxSpeed, (this.speed || 3) + dt * 1.5);
      this.goTo(p.x, p.z, this.speed, dt, 0.25);
      this.stepT -= dt;
      if (this.stepT <= 0) { audio.thud(this.pos, 0.9); g.player.shake(Math.max(0, 0.5 - this.distTo(p) / 30)); this.stepT = 0.36; }
      this.giggleT -= dt;
      if (this.giggleT <= 0) { audio.giggle(this.pos, 0.7); this.giggleT = 3 + Math.random() * 3; }
      if (this.distTo(p) < 1.7) g.caught(this, '一路跑，邊跑邊用爪子拉開閘門的把手。');
    } else if (this.state === 'fall') {
      this.fallV = (this.fallV || 0) + dt * 9.8;
      this.pos.y -= this.fallV * dt;
      this.obj.rotation.x += dt * 1.5;
      if (this.pos.y < -25) { this.state = 'gone'; this.visible = false; }
    }
  }
}

/** A stationary Grinny that relocates whenever the player looks away. */
export class Statue extends Monster {
  constructor(game, spots) {
    super(game, 'grinny', spots[0].x, spots[0].z, 0.7);
    this.spots = spots;
    this.i = 0;
    this.play('Idle', 0, 0.15);
    this.cool = 0;
  }

  update(dt) {
    super.update(dt);
    if (!this.active) return;
    const g = this.game, p = g.player.pos;
    this.face(p.x, p.z, dt, 50);
    this.cool -= dt;
    const seen = g.inView(tmp.set(this.pos.x, 2.4, this.pos.z), 1.0);
    if (!seen && this.cool <= 0 && this.distTo(p) > 7) {
      this.i = (this.i + 1 + Math.floor(Math.random() * (this.spots.length - 1))) % this.spots.length;
      const s = this.spots[this.i];
      this.pos.set(s.x, 0, s.z);
      this.cool = 2.5;
      if (Math.random() < 0.35) audio.giggle(this.pos, 0.25);
    }
  }
}
