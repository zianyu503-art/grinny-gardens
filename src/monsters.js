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
/** Only moves while nobody is looking at it with a light. */
export class Horse extends Monster {
  constructor(game, x, z, rot) {
    super(game, 'horse', x, z, 0.55);
    this.obj.rotation.y = rot;
    this.frozen = true;
    this.stepT = 0;
    this.wasMoving = false;
    this.baseY = 0;
  }

  update(dt) {
    super.update(dt);
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
