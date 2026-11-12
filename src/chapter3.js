// Chapter 3: 失物招領 (the lost-and-found under the park). Six zones, six swappable claws,
// a Ticket Man who cannot be killed, a flicker boss, child shadows, and an unfinished ending.
import * as THREE from 'three';
import { spawn, loadJSON, animator, has } from './assets.js';
import { audio } from './audio.js';
import { Game } from './game.js';
import { Level } from './level.js';
import { Monster } from './monsters.js';
import { Giggler } from './chapter2.js';
import { Physics } from './physics.js';
import { INTRO3, MEI_NOTE, PA3, TAPES3, HINTS3, DIRECTOR3, DIRECTOR3_BROKEN, ENDING3 } from './story.js';
import { dust } from './atmosphere.js';

export const ZONES = ['hub', 'bumper', 'tower', 'mirror', 'radio', 'power'];
const CLAWS = ['scissors', 'magnet', 'grapple', 'flash', 'horn', 'charge'];
const CLAW_NAME = { scissors: '剪刀爪', magnet: '磁力爪', grapple: '鉤索爪', flash: '閃光爪', horn: '喇叭爪', charge: '帶電爪' };
const CLAW_SHORT = { scissors: '剪', magnet: '磁', grapple: '鉤', flash: '閃', horn: '喇', charge: '電' };
const CLAW_MARKER = { scissors: ['hub', 'claw_scissors'], magnet: ['bumper', 'claw_magnet'], grapple: ['tower', 'claw_grapple'],
  flash: ['mirror', 'claw_flash'], horn: ['radio', 'claw_horn'], charge: ['power', 'claw_charge'] };
// interior boxes in Blender metres [x0, x1, y0, y1] (outer zones include their corridor)
const BOX = { hub: [-30, 30, -30, 30], bumper: [-40, 40, 30, 122], tower: [30, 112, -35, 35], mirror: [-40, 40, -112, -30],
  radio: [-102, -30, -30, 30], power: [42, 122, 35, 125] };
const ENTRY = { hub: [0, -22, 0], bumper: [0, 45, 0], tower: [45, 0, -Math.PI / 2], mirror: [0, -45, Math.PI], radio: [-45, 0, Math.PI / 2], power: [77, 48, 0] };
const HUB_DOOR = { bumper: [0, 27, Math.PI], tower: [27, 0, Math.PI / 2], mirror: [0, -27, 0], radio: [-27, 0, -Math.PI / 2] };
const SAVE_KEY = 'smile_ch3_v1';
const PIT_X = 91.5;
const tmp = new THREE.Vector3();
const tmp2 = new THREE.Vector3();
const toWorld = (x, y, z = 0) => new THREE.Vector3(x, z, -y);
const $ = (id) => document.getElementById(id);
const hidden = new THREE.MeshBasicMaterial({ visible: false });

let DATA = null;

/** Fetch the zone JSON (colliders, lights, markers). A missing file just leaves that zone empty. */
export async function loadChapter3() {
  const out = {};
  await Promise.all(ZONES.map(async (z) => {
    try { out[z] = await loadJSON(`ch3/zone_${z}.json`); } catch (e) { console.warn('zone data missing', z, e.message); out[z] = { zone: z, colliders: [], lights: [], markers: {} }; }
  }));
  DATA = out;
}

/** glTF loading strips dots from node names ('hand.L' -> 'handL'), so match loosely. */
function bones(obj, re) {
  const out = [];
  obj.traverse((o) => { if (re.test(o.name)) out.push(o); });
  return out;
}

function zoneAt(bx, by) {
  if (Math.abs(bx) <= 30 && Math.abs(by) <= 30) return 'hub';
  if (by > 35 && bx > 42) return 'power';
  if (bx > 30 && by >= -35 && by <= 35) return 'tower';
  if (by > 30 && Math.abs(bx) <= 42) return 'bumper';
  if (by < -30) return 'mirror';
  if (bx < -30) return 'radio';
  return 'hub';
}

function tapeTexture(text) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 48;
  const x = c.getContext('2d');
  x.fillStyle = '#9c1c14'; x.fillRect(0, 0, 256, 48);
  x.fillStyle = '#e8dcc0'; x.font = 'bold 30px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(`${text}　${text}`, 128, 26);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping;
  return t;
}

/** A dark gradient room with a few bright panels, baked to an environment map so mirrors and metal have something to reflect. */
function makeEnvironment(renderer) {
  const s = new THREE.Scene();
  const geo = new THREE.SphereGeometry(20, 24, 12);
  const col = [];
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const k = (p.getY(i) / 20 + 1) / 2;
    const c = new THREE.Color().lerpColors(new THREE.Color(0x0e0b0a), new THREE.Color(0x2c3a40), k);
    col.push(c.r, c.g, c.b);
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  s.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
  for (let i = 0; i < 6; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(5, 2), new THREE.MeshBasicMaterial({ color: i % 2 ? 0xffd8a0 : 0xbcd4ff, side: THREE.DoubleSide }));
    const a = (i / 6) * Math.PI * 2;
    m.position.set(Math.cos(a) * 15, 8, Math.sin(a) * 15);
    m.lookAt(0, 0, 0);
    s.add(m);
  }
  const pm = new THREE.PMREMGenerator(renderer);
  const rt = pm.fromScene(s, 0.04);
  pm.dispose();
  return rt.texture;
}

// ------------------------------------------------------------------------- level
class Level3 extends Level {
  build() {
    const { scene } = this;
    scene.background = new THREE.Color(0x030304);
    scene.fog = new THREE.FogExp2(0x030304, 0.03);
    scene.add(new THREE.HemisphereLight(0x56627a, 0x1c1612, 1.0));
    try {
      if (this.renderer) { scene.environment = makeEnvironment(this.renderer); scene.environmentIntensity = 0.55; }
    } catch (e) { console.warn('environment map failed', e); }

    this.cols = [];        // {zone, d, c, m}: every JSON collider with its physics box and ray stand-in
    this.groups = {};
    const unitBox = new THREE.BoxGeometry(1, 1, 1);
    const addBlock = (zone) => (d) => {
      const [cx, cy, cz, sx, sy, sz, rz] = d;
      const lo = cz - sz / 2, hi = cz + sz / 2;
      if (lo > 1.9 || hi < 0.3) return;           // overhead beams or floor dressing
      const c = this.physics.boxAt(cx, -cy, sx, sy, rz);
      const m = new THREE.Mesh(unitBox, hidden);
      m.position.copy(toWorld(cx, cy, cz));
      m.scale.set(sx, sz, sy);
      m.rotation.y = rz;
      scene.add(m);
      this.rayTargets.push(m);
      this.cols.push({ zone, d, c, m });
    };
    for (const name of ZONES) {
      const g = new THREE.Group();
      g.name = `zone_${name}`;
      if (has(`ch3/zone_${name}`)) g.add(spawn(`ch3/zone_${name}`));
      scene.add(g);
      this.groups[name] = g;
      const z = DATA[name];
      z.colliders.forEach(addBlock(name));
      for (const li of z.lights) {
        const [x, y, h] = li.pos;
        this.light(x, Math.min(h, 5.5), -y, { color: li.color, intensity: li.intensity * 7.5, distance: li.range * 2.1, flicker: li.flicker ? 0.2 : 0.01 });
      }
      this.points[name] = Object.fromEntries(Object.entries(z.markers).map(([k, [x, y, h]]) => [k, toWorld(x, y, h)]));
    }
    this.physics.rebuild();
  }

  /** Colliders of a zone whose box is centred within `r` metres (Blender x, y) of a point. */
  colsNear(zone, bx, by, r, maxSize = 12) {
    return this.cols.filter((k) => k.zone === zone && Math.hypot(k.d[0] - bx, k.d[1] - by) < r && Math.max(k.d[3], k.d[4]) < maxSize);
  }

  /** The collider whose footprint contains a point (smallest wins). */
  colAt(zone, bx, by, pad = 0.4) {
    let best = null, ba = Infinity;
    for (const k of this.cols) {
      if (k.zone !== zone) continue;
      const [cx, cy, , sx, sy, , rz] = k.d;
      const w = Math.abs(Math.cos(rz)) * sx + Math.abs(Math.sin(rz)) * sy, h = Math.abs(Math.sin(rz)) * sx + Math.abs(Math.cos(rz)) * sy;
      if (Math.abs(bx - cx) <= w / 2 + pad && Math.abs(by - cy) <= h / 2 + pad && w * h < ba) { best = k; ba = w * h; }
    }
    return best;
  }

  dropCol(k) {
    this.physics.setEnabled(k.c, false);
    const i = this.rayTargets.indexOf(k.m);
    if (i >= 0) this.rayTargets.splice(i, 1);
  }
}

// ------------------------------------------------------------------------- enemies
function enemyProxy(monster, w, h, spec, parent = monster.obj, y = h / 2) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), hidden);
  m.position.y = y;
  parent.add(m);
  monster.game.level.interact(m, spec);
  return m;
}

/** The ticket inspector. Cannot be killed: stun him, rip his armour off, or run. */
class TicketMan extends Monster {
  constructor(game) {
    super(game, 'ticket', 0, 0, 0.55);
    this.bones = bones(this.obj, /^plate_/).filter((o) => o.isBone || !o.isMesh);
    this.plates = this.bones.length || 3;
    this.maxPlates = this.plates;
    this.ripped = [];
    this.state = 'patrol'; this.timer = 0; this.pts = []; this.wp = 0; this.target = null; this.lost = 0; this.stepT = 0; this.chargeT = 0;
    this.faceY = 2.7;
    this.visible = false;
    enemyProxy(this, 1.3, 2.8, { kind: 'enemy', enemy: this, label: '' });
    this.play('Idle', 0);
  }

  get speedK() { return 1 - 0.2 * (this.maxPlates - this.plates); }

  rip(point) {
    if (this.plates <= 0) return false;
    this.plates--;
    const b = this.bones.shift();
    if (b) { b.scale.setScalar(0.0001); this.ripped.push(b); }
    this.stun(2.2, 'ArmorOff');
    audio.clank(point || this.pos, 1);
    return true;
  }

  place(points, awayFrom, side) {
    this.pts = points;
    let cand = points.filter((p) => !side || side(p));
    if (!cand.length) cand = points;
    cand = cand.slice().sort((a, b) => Math.hypot(b.x - awayFrom.x, b.z - awayFrom.z) - Math.hypot(a.x - awayFrom.x, a.z - awayFrom.z));
    const s = cand[Math.min(1, cand.length - 1)] || awayFrom;
    this.pos.set(s.x, 0, s.z);
    this.state = 'patrol'; this.path = null; this.wp = Math.max(0, points.indexOf(s)); this.timer = 0;
  }

  hear(x, z, radius, lure = false) {
    if (!this.active || this.state === 'stun') return false;
    const d = Math.hypot(x - this.pos.x, z - this.pos.z);
    const clear = this.game.physics.lineClear(x, z, this.pos.x, this.pos.z);
    if (d < radius * (clear ? 1 : 0.55)) {
      if (this.state === 'chase' || this.state === 'charge') return true;
      this.state = lure ? 'lure' : 'investigate';
      this.target = { x, z };
      this.path = null;
      this.timer = 0;
      return true;
    }
    return false;
  }

  stun(sec, clip = 'Stagger') {
    if (this.state === 'stun' && this.timer > sec) return;
    this.state = 'stun'; this.timer = sec; this.path = null;
    const a = this.actions?.[clip];
    if (a) {
      a.reset().setLoop(THREE.LoopOnce, 1);
      a.clampWhenFinished = true;
      a.timeScale = 1;
      a.setEffectiveWeight(1).fadeIn(0.1).play();
      if (this.current && this.current !== a) this.current.fadeOut(0.1);
      this.current = a;
    }
  }

  reset() { this.state = 'patrol'; this.path = null; this.lost = 0; }

  update(dt) {
    super.update(dt);
    // armour that has been ripped off stays gone, whatever the animation says
    for (const b of this.ripped) b.scale.setScalar(0.0001);
    if (!this.active || !this.visible) return;
    const g = this.game, pl = g.player, p = pl.pos;
    const d = this.distTo(p);
    const k = this.speedK;
    const fwdX = Math.sin(this.obj.rotation.y), fwdZ = Math.cos(this.obj.rotation.y);
    const dot = d > 0.01 ? ((p.x - this.pos.x) * fwdX + (p.z - this.pos.z) * fwdZ) / d : 1;
    const sees = d < (pl.crouched ? 9 : 20) && dot > 0.15 && (d < 2.5 || g.physics.lineClear(this.pos.x, this.pos.z, p.x, p.z));
    if (this.state !== 'stun' && this.state !== 'charge' && this.state !== 'chase' && sees) {
      this.state = 'charge'; this.chargeT = 2.4; this.path = null;
      audio.stinger(0.7); audio.horn(this.pos, 0.9);
    }
    if (pl.noise > 0 && this.state !== 'stun') this.hear(p.x, p.z, pl.noise * 1.3);

    switch (this.state) {
      case 'patrol': {
        this.play('Move', 0.4, 0.6);
        if (this.timer > 0) { this.timer -= dt; this.play('Idle', 0.4); break; }
        const w = this.pts[this.wp];
        if (!w) break;
        if (this.goTo(w.x, w.z, 1.7 * k, dt, 1)) { this.timer = 2 + Math.random() * 2; this.wp = (this.wp + 1 + Math.floor(Math.random() * Math.max(1, this.pts.length - 1))) % this.pts.length; }
        break;
      }
      case 'investigate':
      case 'lure':
        this.play('Move', 0.3, this.state === 'lure' ? 1.1 : 0.9);
        if (this.goTo(this.target.x, this.target.z, (this.state === 'lure' ? 3.3 : 2.6) * k, dt, 0.5)) { this.state = 'search'; this.timer = 4; }
        break;
      case 'charge':
        this.play('Charge', 0.15, 1);
        this.chargeT -= dt;
        this.goTo(p.x, p.z, 6.6 * k, dt, 0.25);
        if (this.chargeT <= 0) { this.state = 'chase'; this.lost = 0; }
        break;
      case 'chase':
        this.play('Move', 0.25, 1.3);
        this.goTo(p.x, p.z, 3.7 * k, dt, 0.35);
        this.lost = sees ? 0 : this.lost + dt;
        if (this.lost > 7 || d > 34) { this.state = 'search'; this.timer = 4; this.target = { x: p.x, z: p.z }; }
        break;
      case 'search':
        this.play('Idle', 0.4);
        this.timer -= dt;
        if (this.timer <= 0) { this.state = 'patrol'; this.timer = 0; }
        break;
      case 'stun':
        this.timer -= dt;
        if (this.timer <= 0) { this.state = 'search'; this.timer = 2; this.play('Idle', 0.3); }
        break;
    }
    this.stepT -= dt;
    if (this.state !== 'stun' && this.state !== 'search' && this.stepT <= 0) {
      audio.thud(this.pos, this.state === 'charge' ? 0.9 : this.state === 'chase' ? 0.6 : 0.35);
      this.stepT = this.state === 'charge' ? 0.3 : this.state === 'chase' ? 0.45 : 0.8;
    }
    if (this.state !== 'stun' && d < 1.35) g.caught(this, '剪票人打不死。用帶電爪或閃光爪讓他停下來，磁力爪可以扯掉他的鋼甲，喇叭爪可以把他引開。');
  }
}

/** A child's shadow. Stands by its relic; once you pick the relic up it follows you until you give it back. */
class ShadowKid extends Monster {
  constructor(game, home, relicPos, id) {
    super(game, 'shadow', home.x, home.z, 0.35);
    this.id = id;
    this.relicPos = relicPos.clone();
    this.state = 'wait';
    this.faceY = 1.2;
    this.play('Idle', 0);
    this.obj.traverse((o) => { if (o.isMesh) o.frustumCulled = false; });
  }

  update(dt) {
    super.update(dt);
    if (!this.visible) return;
    const p = this.game.player.pos;
    if (this.state === 'wait') {
      this.play('Idle', 0.4);
      this.face(this.relicPos.x, this.relicPos.z, dt, 3);
    } else if (this.state === 'follow') {
      const d = this.distTo(p);
      if (d > 2.8 && d < 45) { this.play('Move', 0.3, 0.8); this.goTo(p.x, p.z, d > 6 ? 3.2 : 2.2, dt, 0.5); }
      else { this.play('Idle', 0.4); this.face(p.x, p.z, dt, 4); }
    } else if (this.state === 'releasing') {
      this.timer -= dt;
      if (this.timer <= 0) { this.visible = false; this.state = 'gone'; }
    }
  }

  release() {
    this.state = 'releasing'; this.timer = 2.6;
    this.playOnce('Release', 1);
  }
}

/** Mid-boss made of light. Teleports between lamps, blinds you, rushes you. Flash dazzles him, then charge hurts. */
class Flicker extends Monster {
  constructor(game) {
    super(game, 'flicker', 0, 0, 0.5);
    this.hp = 3;
    this.state = 'gone'; this.timer = 3; this.spots = [];
    this.faceY = 1.8;
    this.light = new THREE.PointLight(0xdfeaff, 0, 18, 1.5);
    game.scene.add(this.light);
    this.visible = false;
    enemyProxy(this, 1.2, 2.2, { kind: 'enemy', enemy: this, label: '' });
    this.play('Idle', 0);
  }

  get alive() { return this.hp > 0; }

  vanish(wait) {
    this.state = 'gone'; this.timer = wait; this.visible = false; this.light.intensity = 0;
  }

  pickSpot() {
    const p = this.game.player.pos;
    const ok = this.spots.filter((s) => { const d = Math.hypot(s.x - p.x, s.z - p.z); return d > 7 && d < 34; });
    const list = ok.length ? ok : this.spots;
    return list[Math.floor(Math.random() * list.length)];
  }

  dazzle() {
    if (!this.active || !this.alive || !['appear', 'flash', 'rush'].includes(this.state)) return false;
    this.state = 'dazzled'; this.timer = 5.5; this.path = null;
    this.play('Stun', 0.1);
    this.light.color.set(0xffffff); this.light.intensity = 20;
    audio.zap(this.pos);
    return true;
  }

  hitCharge(point) {
    if (!this.active || !this.alive) return false;
    if (this.state !== 'dazzled') { audio.clank(point, 0.7); this.game.hud.hint('閃閃會閃躲。先用閃光爪讓他暈眩，再用帶電爪打。', 5); return true; }
    this.hp--;
    audio.zap(this.pos); this.game.player.shake(0.6);
    if (this.hp <= 0) {
      this.state = 'dead'; this.timer = 3.5;
      this.playOnce('Death', 1);
      audio.scream(0.4);
      this.game.onFlickerDead();
    } else {
      this.state = 'hurt'; this.timer = 1.4;
      this.play('Stun', 0.1);
      this.game.hud.hint(`閃閃被打中了（還剩 ${this.hp} 下）`, 4);
    }
    return true;
  }

  update(dt) {
    super.update(dt);
    if (!this.active) { this.light.intensity = 0; return; }
    const g = this.game, pl = g.player, p = pl.pos;
    this.light.position.set(this.pos.x, 1.6, this.pos.z);
    const d = this.distTo(p);
    switch (this.state) {
      case 'gone': {
        this.timer -= dt;
        if (this.timer <= 0 && this.spots.length) {
          const s = this.pickSpot();
          this.pos.set(s.x, 0, s.z); this.path = null;
          this.visible = true; this.state = 'appear'; this.timer = 1.8;
          this.light.color.set(0xdfeaff); this.light.intensity = 10;
          this.play('Idle', 0.1);
          audio.stinger(0.35);
        }
        break;
      }
      case 'appear':
        this.face(p.x, p.z, dt, 6);
        this.light.intensity = 8 + Math.random() * 6;
        this.timer -= dt;
        if (this.timer <= 0) { this.state = 'flash'; this.timer = 1.0; this.playOnce('Flash', 1); audio.zap(this.pos); }
        break;
      case 'flash':
        this.face(p.x, p.z, dt, 6);
        this.light.intensity = 25 + Math.random() * 15;
        this.timer -= dt;
        if (this.timer <= 0) {
          if (g.inView(tmp.set(this.pos.x, 1.6, this.pos.z), 0.9)) g.whiteout(1.6);
          this.state = 'rush'; this.timer = 3.4;
          this.play('Move', 0.1, 1.2);
        }
        break;
      case 'rush':
        this.light.intensity = 10 + Math.random() * 8;
        this.goTo(p.x, p.z, 3.4, dt, 0.3);
        this.timer -= dt;
        if (d < 1.4) g.caught(this, '閃閃怕光。他閃光的時候，用閃光爪照他，等他暈眩再用帶電爪打。');
        else if (this.timer <= 0) this.vanish(2.5 + Math.random() * 2.5);
        break;
      case 'dazzled':
        this.timer -= dt;
        this.light.intensity = 12 + Math.random() * 10;
        if (this.timer <= 0) this.vanish(2.5);
        break;
      case 'hurt':
        this.timer -= dt;
        if (this.timer <= 0) this.vanish(4);
        break;
      case 'dead':
        this.timer -= dt;
        this.light.intensity = Math.max(0, this.timer * 5);
        if (this.timer <= 0) { this.visible = false; this.active = false; this.light.intensity = 0; }
        break;
    }
  }
}

/** The puppet on the finale door. Three beats: cut his strings, blind him, shock his chest. He never speaks again. */
class DirectorPuppet extends Monster {
  constructor(game) {
    super(game, 'director', 0, 0, 0.8);
    this.obj.scale.setScalar(0.95);
    this.faceY = 4;
    this.visible = false;
    this.phase = 0; this.stun = 0; this.wind = 0; this.cooldown = 4; this.broken = false;
    this.play('Idle', 0);
    this.light = new THREE.PointLight(0xff2a14, 0, 22, 1.4);
    game.scene.add(this.light);
    this.hands = bones(this.obj, /^hand\.?[LR]$/);
    this.chest = this.obj.getObjectByName('chest');
    this.head = this.obj.getObjectByName('head');
    this.strings = [];
    this.hands.forEach((h, i) => {
      const proxy = new THREE.Mesh(new THREE.SphereGeometry(0.9, 8, 6), hidden);
      h.add(proxy);
      const spec = { kind: 'string', puppet: this, index: i, label: '' };
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, 1, 0)]),
        new THREE.LineBasicMaterial({ color: 0xe8e0c8, transparent: true, opacity: 0.8 }));
      line.frustumCulled = false;
      game.scene.add(line);
      this.strings.push({ proxy, spec, line, cut: false });
      game.level.interact(proxy, spec);
    });
    const cp = new THREE.Mesh(new THREE.SphereGeometry(1.1, 8, 6), hidden);
    this.chest.add(cp);
    this.chestProxy = cp;
    game.level.interact(cp, { kind: 'puppetchest', puppet: this, label: '' });
  }

  restore() {
    this.phase = 1; this.stun = 0; this.wind = 0; this.cooldown = 5; this.broken = false;
    this.strings.forEach((s) => { s.cut = false; s.line.visible = true; if (!this.game.level.rayTargets.includes(s.proxy)) this.game.level.rayTargets.push(s.proxy); });
    this.obj.rotation.x = 0; this.obj.position.y = 0;
    if (this.head) this.head.scale.setScalar(1);
    this.play('Idle', 0.2);
  }

  update(dt) {
    super.update(dt);
    if (!this.visible) return;
    const g = this.game, p = g.player.pos;
    this.light.position.set(this.pos.x, 3.5, this.pos.z + 1);
    for (const s of this.strings) {
      if (s.cut || !s.line.visible) continue;
      s.proxy.getWorldPosition(tmp);
      const a = s.line.geometry.attributes.position;
      a.setXYZ(0, tmp.x, tmp.y, tmp.z); a.setXYZ(1, tmp.x, 10, tmp.z);
      a.needsUpdate = true;
    }
    if (this.broken || this.phase < 1 || g.cinematic) return;
    this.face(p.x, p.z, dt, 1.2);
    if (this.stun > 0) {
      this.stun -= dt;
      this.light.intensity = 3;
      if (this.stun <= 0) { this.play('Idle', 0.3); this.cooldown = 3; }
      return;
    }
    this.light.intensity = 6 + Math.sin(g.time * 5) * 2;
    if (this.phase < 2) return;
    if (this.wind > 0) {
      this.wind -= dt;
      this.light.intensity = 22;
      if (this.wind <= 0) {
        const d = this.distTo(p);
        if (d < 22 && g.physics.lineClear(this.pos.x, this.pos.z, p.x, p.z)) g.caught(this, '園長的人偶出手前會舉起手臂。看到他舉手的時候，用閃光爪照他的臉。');
        this.play('Idle', 0.3); this.cooldown = 5;
      }
      return;
    }
    this.cooldown -= dt;
    if (this.cooldown <= 0) {
      this.wind = 1.9;
      this.playOnce('Reach', 0.8);
      audio.stinger(0.6); audio.giggle(this.pos, 0.8);
      g.hud.hint('他舉起手了！用閃光爪照他！', 2.2);
    }
  }
}

// ------------------------------------------------------------------------- chapter flow
export class Chapter3 extends Game {
  makePhysics() { return new Physics({ minX: -108, maxX: 128, minZ: -130, maxZ: 130 }, 0.5); }

  buildLevel() {
    const level = new Level3(this.scene, this.physics);
    level.renderer = this.r.renderer;
    level.build();
    return level;
  }

  // ------------------------------------------------------------------ setup
  setupWorld() {
    const L = this.level, P = L.points;
    this.flags = { tapes: 0 };
    this.S = this.loadSave();
    this.zone = 'hub';
    this.prevZone = null;
    this.clawInv = [];
    this.hands = [null, null];
    this.items = {};
    this.seals = {};
    this.dustUpdate = dust(this.scene);
    this.flags.pack = true;
    this.claw.show(true);
    this.flashLight = new THREE.PointLight(0xfff4d0, 0, 26, 1.5);
    this.scene.add(this.flashLight);
    this.whiteEl = document.createElement('div');
    this.whiteEl.style.cssText = 'position:fixed;inset:0;background:#fff;opacity:0;pointer-events:none;z-index:6;transition:opacity .15s';
    document.body.appendChild(this.whiteEl);
    this.checkpoint = { x: ENTRY.hub[0], z: -ENTRY.hub[1], yaw: 0 };

    this.buildSeals();
    this.buildClawPickups();
    this.buildRelics();
    this.buildBumper();
    this.buildTower();
    this.buildMirror();
    this.buildRadio();
    this.buildPower();
    this.buildPickupsMisc();
    this.buildEnemies();
    this.buildClawBar();
    this.applySave();
    this.updateVisibility(true);
    this.scene.updateMatrixWorld(true); // so aim assist sees real positions before the first frame
  }

  loadSave() {
    const d = { zone: 'hub', claws: [], hands: [null, null], relics: [], cut: [], gate: false, crates: [], secrets: [], cracks: [],
      nodes: [], breakers: [], tape: false, hp: 3, done: false, finale: 0 };
    if (new URLSearchParams(location.search).get('new')) return d;
    try {
      const saved = JSON.parse(localStorage.getItem(SAVE_KEY) || '{}');
      return saved.done ? d : { ...d, ...saved }; // a finished run starts over
    } catch { return d; }
  }

  save() {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(this.S)); } catch { /* storage unavailable */ }
  }

  hiddenBox(x, y, z, w, h, d, spec, rotY = 0) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), hidden);
    m.position.set(x, y, z);
    m.rotation.y = rotY;
    this.scene.add(m);
    this.level.interact(m, spec);
    return m;
  }

  take(o) {
    if (!o) return;
    o.parent?.remove(o);
    const i = this.level.rayTargets.indexOf(o);
    if (i >= 0) this.level.rayTargets.splice(i, 1);
  }

  // ------------------------------------------------------------------ scissors targets: seals, tapes, cables
  buildSeals() {
    const P = this.level.points;
    const mk = (id, x, z, rotY, w, label, text) => {
      const g = new THREE.Group();
      g.position.set(x, 1.3, z);
      g.rotation.y = rotY;
      const mat = new THREE.MeshStandardMaterial({ map: tapeTexture(text), roughness: 0.8, side: THREE.DoubleSide });
      [[0.9, 0.06], [0, -0.05], [-0.9, 0.12]].forEach(([y, rz]) => {
        const t = new THREE.Mesh(new THREE.BoxGeometry(w + 0.2, 0.22, 0.02), mat);
        t.position.set(0, y, 0); t.rotation.z = rz; g.add(t);
      });
      const diag = new THREE.Mesh(new THREE.BoxGeometry(w * 1.2, 0.22, 0.02), mat);
      diag.rotation.z = 0.65; diag.position.z = 0.03; g.add(diag);
      this.scene.add(g);
      const col = this.physics.boxAt(x, z, rotY ? 0.5 : w + 0.4, rotY ? w + 0.4 : 0.5, 0);
      const hit = this.hiddenBox(x, 1.4, z, rotY ? 0.5 : w, 3, rotY ? w : 0.5, { kind: 'cut', id, label }, 0);
      this.seals[id] = { g, col, hit, id };
    };
    mk('seal_bumper', 0, -29.6, 0, 3.2, '封條', '封 條');
    mk('seal_tower', 29.6, 0, Math.PI / 2, 3.2, '封條', '封 條');
    mk('seal_mirror', 0, 29.6, 0, 3.2, '封條', '封 條');
    mk('seal_radio', -29.6, 0, Math.PI / 2, 3.2, '封條', '封 條');
    mk('cable_power', 77, -34.4, 0, 3.2, '電纜', '高 壓');
    this.physics.rebuild();
  }

  cutSeal(id, silent = false) {
    const s = this.seals[id];
    if (!s || s.cut) return;
    s.cut = true;
    this.scene.remove(s.g);
    this.physics.setEnabled(s.col, false);
    this.take(s.hit);
    this.physics.rebuild();
    if (!silent) {
      audio.clank(s.g.position, 0.9); audio.pickup();
      this.S.cut.push(id); this.save();
      this.hud.hint(id === 'cable_power' ? '電纜被剪斷了。通往配電廠的路開了。' : '封條被剪斷了。', 4);
      this.refreshObjective();
    }
  }

  // ------------------------------------------------------------------ claw pickups
  buildClawPickups() {
    const P = this.level.points;
    for (const id of CLAWS) {
      const [zone, key] = CLAW_MARKER[id];
      const pt = P[zone]?.[key];
      if (!pt) continue;
      const model = has(`claw_${id}`) ? spawn(`claw_${id}`) : spawn('clawhands');
      const o = new THREE.Group();
      const body = model.getObjectByName('Hand') || model.getObjectByName('HandL') || model;
      const box = new THREE.Box3().setFromObject(model);
      model.position.sub(box.getCenter(new THREE.Vector3()));
      o.add(model);
      o.scale.setScalar(0.42);
      o.position.set(pt.x, pt.y + 0.34, pt.z);
      this.scene.add(o);
      this.level.interact(o, { kind: 'pickup', label: `撿起 ${CLAW_NAME[id]}`, item: 'claw', claw: id });
      this.level.light(pt.x, pt.y + 0.9, pt.z, { color: 0xffe0a0, intensity: 1.6, distance: 5, flicker: 0.03 });
      this.items[`claw_${id}`] = o;
    }
    // the magnet claw's own prop in the bumper booth would be a second copy
    this.level.groups.bumper.getObjectByName('B_claw_magnet')?.removeFromParent();
  }

  giveClaw(id, silent = false) {
    if (this.clawInv.includes(id)) return;
    this.clawInv.push(id);
    this.take(this.items[`claw_${id}`]);
    if (!silent) {
      this.S.claws = this.clawInv.slice();
      audio.pickup(); audio.whisper();
      this.hud.hint(HINTS3.claw[id], 8);
      // a new claw goes to the hand that did not get the last one
      const h = this.lastGiven === 0 ? 1 : 0;
      this.lastGiven = h;
      this.equipClaw(h, id);
      if (this.clawInv.length === 2) this.after(8.5, () => this.hud.hint(HINTS3.swap, 7));
      this.save();
    }
    this.updateClawBar();
  }

  equipClaw(hand, id, silent = false) {
    if (id && !this.clawInv.includes(id)) return;
    if (this.claw.hands[hand].state !== 'idle') return;
    if (this.hands[hand] === 'charge' && id !== 'charge') this.claw.discharge(hand);
    this.hands[hand] = id;
    this.claw.equip(hand, id);
    if (id === 'charge') this.claw.hands[hand].charged = 1e9; // the hum starts in updateWorld, once audio is running
    this.S.hands = this.hands.slice();
    if (!silent) audio.clawGrab();
    this.updateClawBar();
  }

  cycleClaw(hand) {
    if (!this.clawInv.length) return;
    const i = this.clawInv.indexOf(this.hands[hand]);
    this.equipClaw(hand, this.clawInv[(i + 1) % this.clawInv.length]);
  }

  buildClawBar() {
    const bar = document.createElement('div');
    bar.id = 'clawBar';
    bar.style.cssText = 'position:absolute;left:50%;bottom:18px;transform:translateX(-50%);display:flex;gap:6px;font-size:13px;white-space:nowrap;pointer-events:none;text-shadow:0 0 6px #000;z-index:3';
    $('hud').appendChild(bar);
    this.clawBar = bar;
    if (this.input.touchMode) setTimeout(() => {
      for (const [h, label, right] of [[0, '換左', 260], [1, '換右', 200]]) {
        const b = document.createElement('button');
        b.className = 'tbtn small';
        b.textContent = label;
        b.style.cssText = `right:calc(${right}px + env(safe-area-inset-right));top:12px;bottom:auto`;
        b.addEventListener('touchstart', (e) => { e.preventDefault(); this.cycleClaw(h); }, { passive: false });
        const ui = document.getElementById('touchUI');
        (ui || document.body).appendChild(b);
        this.touchSwap = this.touchSwap || [];
        this.touchSwap.push(b);
      }
    }, 0);
    this.updateClawBar();
  }

  updateClawBar() {
    if (!this.clawBar) return;
    this.clawBar.innerHTML = CLAWS.map((id, i) => {
      const own = this.clawInv.includes(id);
      const l = this.hands[0] === id, r = this.hands[1] === id;
      const border = l && r ? '#c8a0ff' : l ? '#5ab8ff' : r ? '#ff6a4a' : own ? '#777' : '#333';
      return `<span style="border:2px solid ${border};padding:3px 7px;border-radius:5px;background:rgba(0,0,0,.45);opacity:${own ? 1 : 0.3}">${i + 1} ${own ? CLAW_NAME[id] : '？'}${l ? ' 左' : ''}${r ? ' 右' : ''}</span>`;
    }).join('');
    this.updateInventory();
  }

  // ------------------------------------------------------------------ relics and shadows
  buildRelics() {
    const L = this.level, P = L.points;
    this.relics = {};
    for (let n = 1; n <= 9; n++) {
      let pt = null;
      for (const z of ZONES) if (P[z]?.[`relic_${n}`]) pt = P[z][`relic_${n}`];
      if (!pt) continue;
      const o = L.add('name_tag', pt.x, pt.z, { y: pt.y + 0.04, scale: 2, rot: n });
      L.interact(o, { kind: 'pickup', label: `撿起 第 ${n} 個孩子的遺物`, item: 'relic', n });
      L.light(pt.x, pt.y + 0.7, pt.z, { color: 0xffe0b0, intensity: 1.3, distance: 3.5, flicker: 0.04 });
      // the child's shadow stands a couple of metres away, watching it
      let home = pt.clone();
      search: for (const rad of [2.4, 1.7]) for (let k = 0; k < 8; k++) {
        const a = k * Math.PI / 4 + n;
        const hx = pt.x + Math.cos(a) * rad, hz = pt.z + Math.sin(a) * rad;
        if (!this.physics.blocked(...this.physics.cellOf(hx, hz))) { home = new THREE.Vector3(hx, 0, hz); break search; }
      }
      const sh = new ShadowKid(this, home, pt, n);
      enemyProxy(sh, 1, 1.6, { kind: 'shadow', shadow: sh, n, label: '還給他（遺物）', use: () => this.giveRelic(n) });
      this.relics[n] = { obj: o, shadow: sh, zone: ZONES.find((z) => P[z]?.[`relic_${n}`]), taken: false, done: false };
    }
  }

  takeRelic(n) {
    const r = this.relics[n];
    if (!r || r.taken) return;
    r.taken = true;
    r.shadow.state = 'follow';
    audio.pickup(); audio.whisper();
    this.hud.hint('孩子的影子慢慢朝你走過來。走到他身邊，按 E 把遺物還給他。', 7);
    this.updateInventory();
  }

  giveRelic(n) {
    const r = this.relics[n];
    if (!r) return;
    if (!r.taken) { this.hud.hint('他在看著什麼東西。去找他的遺物。', 3); return; }
    if (r.done || r.shadow.state === 'releasing') return;
    r.done = true;
    r.shadow.release();
    this.take(r.shadow.obj.children.find((c) => c.userData.interact));
    audio.whisper(); audio.musicBox(null, 0.2);
    if (!this.S.relics.includes(n)) this.S.relics.push(n);
    this.save();
    const done = this.S.relics.length;
    this.hud.say([{ text: done >= 9 ? '九個孩子的影子，都認得自己了。可是，還有十八個名字沒有被叫到。' : `他看了看手裡的東西，輕輕地笑了。（${done}/9）`, dur: 4.5 }], true);
    this.updateInventory();
    this.refreshObjective();
  }

  // ------------------------------------------------------------------ zone dressings
  buildBumper() {
    const L = this.level, P = L.points.bumper, G = L.groups.bumper;
    // the iron shutter
    const gate = P.magnet_gate_1;
    const gk = gate && L.cols.filter((k) => k.zone === 'bumper' && Math.abs(k.d[1] - 92) < 0.6 && Math.abs(k.d[0]) < 6);
    this.gateCols = gk || [];
    this.shutter = G.getObjectByName('B_shutter');
    for (const k of this.gateCols) L.interact(k.m, { kind: 'magnet_gate', label: '' });
    // heavy iron crates in the way
    this.crates = {};
    for (let n = 1; n <= 3; n++) {
      const o = G.getObjectByName(`B_magnet_crate_${n}`);
      const p = P[`magnet_crate_${n}`];
      if (!o || !p) continue;
      const cols = L.colsNear('bumper', p.x, -p.z, 1.2, 3);
      const spec = { kind: 'magnet_crate', n, label: '' };
      L.interact(o, spec);
      cols.forEach((k) => { k.m.userData.interact = spec; });
      this.crates[n] = { o, cols, p: p.clone() };
    }
  }

  openGate(silent = false) {
    if (this.S.gate && !silent && this.gateOpen) return;
    this.gateOpen = true;
    this.S.gate = true;
    for (const k of this.gateCols) L_drop(this.level, k);
    this.physics.rebuild();
    const s = this.shutter;
    if (s) {
      if (silent) s.position.y += 5;
      else {
        const y0 = s.position.y;
        audio.rumble(s.getWorldPosition(new THREE.Vector3()), 3, 0.8);
        audio.clank(s.getWorldPosition(new THREE.Vector3()), 1);
        this.anim(2.6, (k) => { s.position.y = y0 + k * 5; });
      }
    }
    if (!silent) { this.save(); this.hud.hint('鐵捲門被磁力拉開了。', 4); }
  }

  pullCrate(n, silent = false) {
    const c = this.crates[n];
    if (!c || c.gone) return;
    c.gone = true;
    c.cols.forEach((k) => this.level.dropCol(k));
    this.physics.rebuild();
    if (silent) { c.o.visible = false; return; }
    if (!this.S.crates.includes(n)) this.S.crates.push(n);
    this.save();
    const from = c.o.position.clone();
    const p = this.player.pos;
    const to = from.clone();
    const dir = new THREE.Vector3(p.x - from.x, 0, p.z - from.z).normalize();
    to.x = p.x - dir.x * 2.4; to.z = p.z - dir.z * 2.4;
    to.y = from.y;
    // the crate is the parent group of its mesh; its local frame is the zone's (identity), so world == local
    audio.clank(from, 1);
    this.anim(0.7, (k) => { c.o.position.lerpVectors(from, to, k); c.o.position.y = from.y + Math.sin(k * Math.PI) * 0.8; });
    this.after(0.75, () => { audio.thud(to, 1); audio.clank(to, 0.8); this.player.shake(0.5); c.o.visible = false; this.take(c.o); });
  }

  buildTower() {
    const L = this.level, P = L.points.tower;
    this.anchors = [];
    for (let n = 1; n <= 4; n++) {
      const a = P[`anchor_${n}`];
      if (!a) continue;
      const m = this.hiddenBox(a.x, a.y, a.z, 1.6, 1.6, 1.6, { kind: 'anchor', n, label: '', aimPoint: a.clone() });
      this.anchors.push({ n, p: a.clone(), m });
    }
    this.rope = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1, 6).translate(0, 0.5, 0), new THREE.MeshStandardMaterial({ color: 0x1a1c18, roughness: 0.6, metalness: 0.5 }));
    this.rope.visible = false; this.rope.frustumCulled = false;
    this.scene.add(this.rope);
  }

  /** Scripted haul across the pit: physics is 2D, so the player follows an arc to the other rim. */
  grapple(anchor, handIdx) {
    if (this.hauling) return;
    const P = this.level.points.tower, p = this.player.pos;
    if (Math.hypot(anchor.p.x - p.x, anchor.p.z - p.z) > 18) { this.hud.hint('鉤環太遠了。', 3); return; }
    if (Math.abs(p.x - PIT_X) > 9) { this.hud.hint('走到深坑邊再用鉤索爪。', 3); return; }
    const west = p.x < PIT_X;
    const rim = west ? P.pit_b : P.pit_a;
    if (!rim) return;
    const from = p.clone(), to = new THREE.Vector3(rim.x, 0, anchor.p.z);
    this.hauling = { t: 0, dur: 1.7, from, to, anchor: anchor.p.clone() };
    audio.clank(anchor.p, 0.9); audio.rumble(p, 1.2, 0.35);
    this.rope.visible = true;
  }

  updateHaul(dt) {
    const h = this.hauling;
    if (!h) return;
    h.t += dt;
    const k = Math.min(1, h.t / h.dur), e = k * k * (3 - 2 * k);
    const p = this.player.pos;
    p.x = h.from.x + (h.to.x - h.from.x) * e;
    p.z = h.from.z + (h.to.z - h.from.z) * e;
    p.y = Math.sin(Math.PI * Math.min(1, k * 1.05)) * 3.2;
    const head = tmp.set(p.x, p.y + 1.5, p.z);
    const dir = tmp2.copy(h.anchor).sub(head);
    this.rope.position.copy(head); this.rope.scale.set(1, dir.length(), 1);
    this.rope.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    if (k >= 1) {
      p.y = 0;
      const r = this.physics.resolve(p.x, p.z, this.player.radius);
      p.x = r.x; p.z = r.z;
      this.hauling = null; this.rope.visible = false;
      audio.thud(p, 0.8); this.player.shake(0.4);
    }
  }

  buildMirror() {
    const L = this.level, P = L.points.mirror;
    this.secrets = {};
    for (let n = 1; n <= 3; n++) {
      const pt = P[`secret_${n}`];
      if (!pt) continue;
      const k = L.colAt('mirror', pt.x, -pt.z);
      this.secrets[n] = { pt: pt.clone(), col: k, door: L.groups.mirror.getObjectByName(`U_secret_door_${n}`), found: false };
    }
  }

  revealSecret(n, silent = false) {
    const s = this.secrets[n];
    if (!s || s.found) return;
    s.found = true;
    if (s.col) L_drop(this.level, s.col);
    this.physics.rebuild();
    if (s.door) s.door.visible = false;
    this.level.light(s.pt.x, 1.6, s.pt.z, { color: 0xffe8b0, intensity: 1.4, distance: 6, flicker: 0.03 });
    if (!silent) {
      if (!this.S.secrets.includes(n)) this.S.secrets.push(n);
      this.save();
      audio.creak(s.pt, 0.8); audio.rumble(s.pt, 1, 0.4);
      this.hud.hint('牆上出現了一道門。', 4);
    }
  }

  buildRadio() {
    const L = this.level, P = L.points.radio, G = L.groups.radio;
    this.cracks = {};
    for (let n = 1; n <= 3; n++) {
      const pt = P[`crack_${n}`];
      if (!pt) continue;
      const o = G.getObjectByName(`RAD_crack_${n}`);
      const cols = L.colsNear('radio', pt.x, -pt.z, 2.6, 5);
      const spec = { kind: 'crack', n, label: '' };
      if (o) L.interact(o, spec);
      cols.forEach((k) => { k.m.userData.interact = spec; });
      this.cracks[n] = { o, cols, pt: pt.clone(), broken: false };
    }
    if (P.tape_reveal) {
      const pt = P.tape_reveal;
      const t = L.add('cassette', pt.x, pt.z, { y: pt.y + 0.03, rot: 0.7 });
      L.interact(t, { kind: 'pickup', label: '撿起 錄音帶', item: 'tape3' });
      L.light(pt.x, pt.y + 0.6, pt.z, { color: 0xffd0a0, intensity: 1.4, distance: 3.5, flicker: 0.05 });
      this.items.tape = t;
    }
  }

  breakCrack(n, silent = false) {
    const c = this.cracks[n];
    if (!c || c.broken) return;
    c.broken = true;
    c.cols.forEach((k) => this.level.dropCol(k));
    this.physics.rebuild();
    if (c.o) { c.o.visible = false; this.take(c.o); }
    if (!silent) {
      if (!this.S.cracks.includes(n)) this.S.cracks.push(n);
      this.save();
      audio.rumble(c.pt, 2, 1); audio.boneShatter?.(c.pt); audio.clank(c.pt, 1);
      this.player.shake(0.7);
      this.hud.hint('裂開的牆被震垮了，後面還有一個房間。', 4);
    }
  }

  buildPower() {
    const L = this.level, P = L.points.power, G = L.groups.power;
    this.nodes = {};
    this.breakers = {};
    const matOff = new THREE.MeshStandardMaterial({ color: 0x401010, emissive: 0xff2010, emissiveIntensity: 0.9, roughness: 0.5 });
    const post = new THREE.MeshStandardMaterial({ color: 0x2a2e30, roughness: 0.6, metalness: 0.6 });
    for (let n = 1; n <= 6; n++) {
      const pt = P[`node_${n}`];
      if (!pt) continue;
      const g = new THREE.Group();
      g.position.set(pt.x, 0, pt.z);
      const col = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.22, 1.5, 10), post); col.position.y = 0.75; g.add(col);
      const orb = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 8), matOff.clone()); orb.position.y = 1.7; g.add(orb);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.04, 6, 16), post); ring.position.y = 1.7; ring.rotation.x = Math.PI / 2; g.add(ring);
      this.scene.add(g);
      const light = L.light(pt.x, 1.8, pt.z, { color: 0xff3020, intensity: 1.2, distance: 6, flicker: 0.05 });
      const spec = { kind: 'node', n, label: '', aimPoint: new THREE.Vector3(pt.x, 1.7, pt.z) };
      const hit = this.hiddenBox(pt.x, 1.2, pt.z, 1.2, 2.4, 1.2, spec);
      this.nodes[n] = { g, orb, light, powered: false, hit, spec };
    }
    for (let n = 1; n <= 3; n++) {
      const pt = P[`breaker_${n}`];
      if (!pt) continue;
      const g = new THREE.Group();
      g.position.set(pt.x + 2.2, 0, pt.z);
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.8, 1.4), post); box.position.y = 1.1; g.add(box);
      const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.16, 8, 6), matOff.clone()); lamp.position.set(-0.3, 1.6, 0); g.add(lamp);
      const lever = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.7, 0.14), new THREE.MeshStandardMaterial({ color: 0xb0a070, roughness: 0.5, metalness: 0.6 }));
      lever.position.set(-0.32, 1.1, 0); lever.rotation.z = 0.6; g.add(lever);
      this.scene.add(g);
      this.physics.boxAt(g.position.x, g.position.z, 0.7, 1.5, 0);
      const light = L.light(g.position.x - 1, 1.7, g.position.z, { color: 0xff3020, intensity: 1.2, distance: 6, flicker: 0.05 });
      const spec = { kind: 'breaker', n, label: '', aimPoint: new THREE.Vector3(g.position.x - 0.3, 1.3, g.position.z) };
      const hit = this.hiddenBox(g.position.x - 0.3, 1.2, g.position.z, 1.4, 2.4, 1.6, spec);
      this.breakers[n] = { g, lamp, lever, light, closed: false, hit };
    }
    this.physics.rebuild();
    this.finaleDoor = G.getObjectByName('PWR_finale_door');
    const fd = P.finale_door;
    this.finaleCols = fd ? L.cols.filter((k) => k.zone === 'power' && Math.hypot(k.d[0] - fd.x, k.d[1] + fd.z) < 4.5 && Math.max(k.d[3], k.d[4]) < 4) : [];
    this.finale = { puppet: null };
  }

  circuitOf(n) { return Math.ceil(n / 2); }

  powerNode(n, silent = false) {
    const nd = this.nodes[n];
    if (!nd || nd.powered) return;
    nd.powered = true;
    nd.orb.material.color.set(0x104020); nd.orb.material.emissive.set(0x30ff70);
    nd.light.color.set(0x40ff80);
    if (!silent) {
      audio.zap(nd.g.position); this.player.shake(0.2);
      if (!this.S.nodes.includes(n)) this.S.nodes.push(n);
      this.save();
      const c = this.circuitOf(n);
      const both = this.nodes[c * 2 - 1]?.powered && this.nodes[c * 2]?.powered;
      this.hud.hint(both ? `第 ${c} 條電路的兩個節點都通電了。去東牆的斷路器 ${c} 合閘。` : '節點通電了。', 5);
    }
  }

  closeBreaker(n, silent = false) {
    const b = this.breakers[n];
    if (!b || b.closed) return;
    if (!silent && !(this.nodes[n * 2 - 1]?.powered && this.nodes[n * 2]?.powered)) {
      audio.clank(b.g.position, 0.6);
      this.hud.hint(`斷路器 ${n} 的線路還沒接通。先用帶電爪啟動節點 ${n * 2 - 1} 和 ${n * 2}（紅色的球）。`, 5);
      return;
    }
    b.closed = true;
    b.lamp.material.color.set(0x104020); b.lamp.material.emissive.set(0x30ff70);
    b.lever.rotation.z = -0.6;
    b.light.color.set(0x40ff80);
    if (!silent) {
      audio.zap(b.g.position); audio.clank(b.g.position, 1);
      if (!this.S.breakers.includes(n)) this.S.breakers.push(n);
      this.save();
      const k = this.S.breakers.length;
      this.hud.hint(`電路 ${k}/3 接通。`, 4);
      this.refreshObjective();
      if (k >= 3) this.after(2, () => this.startFinale());
    }
  }

  // ------------------------------------------------------------------ misc pickups
  buildPickupsMisc() {
    const L = this.level, P = L.points;
    const bat = (pt, dx = 0.7, dz = 0) => {
      const b = L.add('battery', pt.x + dx, pt.z + dz, { y: 0.02 });
      L.interact(b, { kind: 'pickup', label: '撿起 電池', item: 'battery' });
    };
    bat(P.hub.relic_1, 1.2); bat(P.hub.relic_2, -1.2);
    for (const z of ['bumper', 'tower', 'mirror', 'radio', 'power']) {
      if (P[z].ticket_patrol_2) bat(P[z].ticket_patrol_2);
      if (P[z].ticket_patrol_3) bat(P[z].ticket_patrol_3, 0, 0.7);
    }
    if (P.power.claw_charge) bat(P.power.claw_charge, 1.5, 0.5);
    // the lost-and-found counter files your progress
    const sv = P.hub.save;
    if (sv) {
      this.hiddenBox(sv.x, sv.y + 0.3, sv.z, 1.2, 0.8, 0.8, { kind: 'use', label: '登記進度（存檔）', use: () => this.saveHere() });
      L.light(sv.x, sv.y + 0.9, sv.z, { color: 0xffe0b0, intensity: 1.6, distance: 5, flicker: 0.04 });
    }
  }

  saveHere() {
    this.S.zone = this.zone;
    this.checkpoint = { x: this.player.pos.x, z: this.player.pos.z, yaw: this.player.yaw };
    this.save();
    audio.pickup();
    this.hud.hint('進度已登記。', 3);
  }

  // ------------------------------------------------------------------ enemies
  buildEnemies() {
    const L = this.level, P = L.points;
    this.ticket = new TicketMan(this);
    this.flicker = new Flicker(this);
    this.flicker.hp = this.S.hp;
    this.puppet = null;
    const pts = (zone, prefix) => Object.keys(P[zone]).filter((k) => k.startsWith(prefix)).sort().map((k) => P[zone][k]);
    this.patrol = Object.fromEntries(ZONES.map((z) => [z, pts(z, 'ticket_patrol')]));
    this.gigglers = {};
    const counts = { bumper: 2, tower: 2, mirror: 2, radio: 2, power: 3 };
    for (const [z, n] of Object.entries(counts)) {
      const pa = this.patrol[z];
      if (!pa.length) { this.gigglers[z] = []; continue; }
      this.gigglers[z] = Array.from({ length: n }, (_, i) => new Giggler(this, pa[(i * 2 + 1) % pa.length], pa));
      this.gigglers[z].forEach((gg) => { gg.visible = false; L.interact(gg.obj, { kind: 'giggler', giggler: gg, label: '' }); });
    }
    this.flicker.spots = [
      ...pts('mirror', 'lamp_').map((p) => p.clone().setY(0)),
    ];
  }

  allGigglers() { return Object.values(this.gigglers).flat(); }

  /** Where Flicker may appear in each zone. */
  flickerSpots(zone) {
    const P = this.level.points[zone];
    if (zone === 'mirror') return Object.keys(P).filter((k) => k.startsWith('lamp_')).map((k) => P[k].clone().setY(0));
    if (zone === 'power') {
      const s = Object.keys(P).filter((k) => k.startsWith('node_')).map((k) => P[k].clone().setY(0));
      return s;
    }
    return [];
  }

  // ------------------------------------------------------------------ start
  start() {
    audio.init();
    this.started = true;
    this.paused = false;
    this.hud.show(true);
    const z = this.S.zone;
    const cp = this.zoneCheckpoint(z, null);
    this.checkpoint = cp;
    this.player.place(cp.x, cp.z, cp.yaw);
    this.player.surface = 'ground';
    audio.setIndoor(true);
    this.hud.fade(0, 3);
    this.zone = null;
    this.enterZone(z, this.S.zone === 'hub' ? null : 'hub', true);
    if (!this.clawInv.includes('scissors')) {
      this.hud.say(INTRO3);
      this.after(16, () => this.hud.hint('櫃檯上有一把剪刀。按 E 或用爪子把它抓過來。', 8));
    } else if (!this.S.done) {
      this.hud.say([{ text: '我回到了失物招領中心。', dur: 3 }]);
    }
    this.updateInventory();
    this.refreshObjective();
  }

  zoneCheckpoint(zone, prev) {
    let e = ENTRY[zone];
    if (zone === 'hub' && prev && HUB_DOOR[prev]) e = HUB_DOOR[prev];
    if (zone === 'tower' && prev === 'power') e = [77, 30, Math.PI];
    if (zone === 'power' && this.S.finale > 0) e = [79.65, 99.35, 0];
    return { x: e[0], z: -e[1], yaw: e[2] };
  }

  enterZone(name, prev, first = false) {
    this.prevZone = prev;
    this.zone = name;
    if (!first || name !== 'hub' || true) this.checkpoint = this.zoneCheckpoint(name, prev);
    this.S.zone = name;
    this.save();
    this.updateVisibility(true);
    audio.setIndoor(true);
    // enemies belong to the zone you are in
    this.allGigglers().forEach((g) => { g.active = false; g.visible = false; });
    (this.gigglers[name] || []).forEach((g) => { g.visible = true; g.active = true; g.reset(); });
    const T = this.ticket;
    const pts = this.patrol[name] || [];
    if (pts.length && !this.finaleRunning()) {
      const p = this.player.pos;
      T.active = true; T.visible = true;
      const sideFn = name === 'tower' ? (pp) => (pp.x < PIT_X) === (p.x < PIT_X) : null;
      T.place(pts, p, sideFn);
    } else { T.active = false; T.visible = false; }
    this.setupFlicker(name);
    if (PA3[name] && !first) { this.hud.say([{ who: '廣播', text: PA3[name], dur: 4.5 }]); audio.voice(`pa_${name}`, { kind: 'pa', rate: 0.88 }); }
    if (name !== 'hub' && pts.length && !this.S.ticketHint && !first) {
      this.S.ticketHint = true;
      this.after(6, () => { this.hud.say([{ who: '廣播', text: PA3.ticket, dur: 4.5 }]); audio.voice('pa_ticket', { kind: 'pa', rate: 0.88 }); });
    }
    this.refreshObjective();
  }

  setupFlicker(zone) {
    const f = this.flicker;
    const owns = this.clawInv.includes('flash');
    f.spots = this.flickerSpots(zone);
    const on = f.alive && owns && f.spots.length > 0 && !this.finaleRunning();
    f.active = on;
    if (!on) { f.vanish(3); f.light.intensity = 0; } else if (f.state === 'gone') f.timer = 4 + Math.random() * 3;
  }

  finaleRunning() { return this.S.finale > 0 && !this.S.done; }

  refreshObjective() {
    const S = this.S, own = (c) => this.clawInv.includes(c);
    let t;
    if (!own('scissors')) t = '拿起櫃檯上的剪刀';
    else if (this.finaleRunning()) t = '打倒園長的人偶';
    else if (S.breakers.length >= 3) t = '前往配電廠深處';
    else if (own('charge')) t = `接通配電廠的三條電路（${S.breakers.length}/3）`;
    else t = `用剪刀剪開封條，找回爪子和孩子的遺物（遺物 ${S.relics.length}/9）`;
    if (own('scissors') && !this.finaleRunning() && S.breakers.length < 3) {
      const missing = CLAWS.filter((c) => !own(c)).length;
      if (missing && !own('charge')) t += `（爪子 ${this.clawInv.length}/6）`;
    }
    this.hud.objective(t);
  }

  updateInventory() {
    const S = this.S;
    this.hud.inventory([
      S.relics ? `遺物 ${S.relics.length}/9` : '',
      this.flags.tapes ? `錄音帶 ${this.flags.tapes}` : '',
      Object.values(this.relics || {}).some((r) => r.taken && !r.done) ? '帶著孩子的遺物' : '',
    ]);
  }

  /** Hide zones that are far away: the map is 240 m wide and mostly invisible through fog anyway. */
  updateVisibility(force = false) {
    const p = this.player.pos, bx = p.x, by = -p.z;
    for (const name of ZONES) {
      const [x0, x1, y0, y1] = BOX[name];
      const dx = Math.max(x0 - bx, 0, bx - x1), dy = Math.max(y0 - by, 0, by - y1);
      const show = Math.hypot(dx, dy) < 46 || name === this.zone;
      const g = this.level.groups[name];
      if (g.visible !== show) g.visible = show;
    }
  }

  // ------------------------------------------------------------------ tapes / pickups
  collect(spec) {
    if (spec.item === 'claw') { this.take(spec.obj); this.giveClaw(spec.claw); this.afterClaw(spec.claw); return; }
    if (spec.item === 'relic') { this.take(spec.obj); this.takeRelic(spec.n); return; }
    if (spec.item === 'tape3') {
      this.take(spec.obj);
      audio.pickup();
      this.flags.tapes++;
      this.S.tape = true; this.save();
      this.playTape('reveal', TAPES3.reveal).then?.(() => {});
      this.updateInventory();
      return;
    }
    super.collect(spec);
  }

  afterClaw(id) {
    if (id === 'scissors') {
      this.hud.say(MEI_NOTE, true);
      this.after(14, () => this.hud.hint('把剪刀爪對準門口的封條，發射。', 8));
    }
    this.refreshObjective();
  }

  toggleMap() { this.hud.hint('這裡沒有地圖。', 3); }

  noiseAt(x, z, radius) { this.ticket?.hear(x, z, radius); }

  whiteout(sec) {
    this.whiteEl.style.transition = 'opacity .06s';
    this.whiteEl.style.opacity = 1;
    audio.zap(this.player.pos);
    setTimeout(() => { this.whiteEl.style.transition = `opacity ${sec}s`; this.whiteEl.style.opacity = 0; }, 350);
  }

  // ------------------------------------------------------------------ claw effects
  onClawHit(index, hit, point, hand) {
    const id = hand.claw;
    const it = hit?.interact;
    const kind = it?.kind;
    const need = (c) => { audio.clank(point, 0.6); this.hud.hint(`這個要用${CLAW_NAME[c]}。（${HINTS3.swap}）`, 4); };

    // enemies
    if (kind === 'giggler') { it.giggler.knock(); if (id === 'charge') { it.giggler.timer = 8; audio.zap(point); } return; }
    if (kind === 'enemy') return this.hitEnemy(it.enemy, id, point);
    if (kind === 'string') {
      if (id !== 'scissors') return need('scissors');
      return this.cutString(it);
    }
    if (kind === 'puppetchest') return this.hitPuppet(id, point);
    if (kind === 'shadow') { audio.clank(point, 0.3); return; }

    switch (id) {
      case 'scissors':
        if (kind === 'cut') { this.cutSeal(it.id); return; }
        break;
      case 'magnet':
        if (kind === 'magnet_gate') { this.openGate(); return; }
        if (kind === 'magnet_crate') { this.pullCrate(it.n); return; }
        break;
      case 'grapple':
        if (kind === 'anchor') { this.grapple(this.anchors.find((a) => a.n === it.n), index); return; }
        break;
      case 'flash':
        this.flashBurst(point);
        if (kind === 'pickup') break;
        return;
      case 'horn':
        this.hornBlast(point, it);
        if (kind === 'pickup') break;
        return;
      case 'charge':
        if (kind === 'node') { this.powerNode(it.n); return; }
        if (kind === 'breaker') { this.closeBreaker(it.n); return; }
        break;
    }
    // wrong claw on a special target: say which one it needs
    const wants = { cut: 'scissors', magnet_gate: 'magnet', magnet_crate: 'magnet', anchor: 'grapple', crack: 'horn', node: 'charge', breaker: 'charge' }[kind];
    if (wants) return need(wants);
    super.onClawHit(index, hit, point, hand);
  }

  hitEnemy(e, id, point) {
    if (!e.visible || !e.active) { audio.clank(point, 0.3); return; }
    if (e instanceof TicketMan) {
      if (id === 'charge') { e.stun(4, 'Stagger'); audio.zap(point); this.player.shake(0.5); this.hud.hint('剪票人被電暈了幾秒。', 3); }
      else if (id === 'magnet') { if (!e.rip(point)) { audio.clank(point, 0.8); this.hud.hint('他身上已經沒有鋼甲可以扯了。', 3); } else this.hud.hint(`鋼甲被扯掉了！剪票人變慢了（${e.maxPlates - e.plates}/${e.maxPlates}）`, 4); }
      else if (id === 'flash') this.flashBurst(point);
      else if (id === 'horn') this.hornBlast(point);
      else audio.clank(point, 0.7);
    } else if (e instanceof Flicker) {
      if (id === 'charge') e.hitCharge(point);
      else if (id === 'flash') this.flashBurst(point);
      else audio.clank(point, 0.4);
    }
  }

  hornBlast(point, it) {
    audio.horn(point, 1);
    audio.horn(this.player.pos, 0.5);
    this.player.shake(0.3);
    this.ticket.hear(point.x, point.z, 70, true);
    for (const [n, c] of Object.entries(this.cracks || {})) {
      if (c.broken) continue;
      if ((it?.kind === 'crack' && it.n == n) || (c.pt.distanceTo(point) < 4.5)) this.breakCrack(+n);
    }
  }

  flashBurst(point) {
    const fl = this.flashLight;
    fl.position.copy(point).addScaledVector(this.camera.getWorldDirection(tmp), -0.6);
    fl.intensity = 60;
    this.anim(0.5, (k) => { fl.intensity = 60 * (1 - k); });
    audio.zap(point);
    const cam = this.camera.getWorldPosition(new THREE.Vector3());
    const dir = this.camera.getWorldDirection(new THREE.Vector3());
    const seen = (p, r = 22) => {
      const to = tmp2.copy(p).sub(cam); const d = to.length();
      return d < r && to.normalize().dot(dir) > 0.45 && this.physics.lineClear(cam.x, cam.z, p.x, p.z);
    };
    // secret doors show themselves
    for (const [n, s] of Object.entries(this.secrets || {})) {
      if (!s.found && (s.pt.distanceTo(point) < 11 || (seen(tmp.set(s.pt.x, 1.4, s.pt.z), 10)))) this.revealSecret(+n);
    }
    // blind what is looking back
    const T = this.ticket;
    if (T.active && T.visible && seen(tmp.set(T.pos.x, 1.8, T.pos.z), 26)) { T.stun(3, 'Stagger'); this.hud.hint('剪票人被閃光弄瞎了幾秒。', 3); }
    if (this.flicker.active && this.flicker.visible && seen(tmp.set(this.flicker.pos.x, 1.6, this.flicker.pos.z), 28)) this.flicker.dazzle();
    for (const g of this.allGigglers()) if (g.active && g.visible && seen(tmp.set(g.pos.x, 0.5, g.pos.z), 20)) { g.state = 'stunned'; g.timer = 3.5; }
    const pu = this.puppet;
    if (pu?.visible && pu.phase >= 2 && !pu.broken && seen(tmp.set(pu.pos.x, 3.5, pu.pos.z), 30)) {
      pu.stun = 7; pu.wind = 0; pu.play('Idle', 0.2);
      this.hud.hint('人偶被閃光弄瞎了！快用帶電爪打他的胸口！', 5);
    }
    if (this.zone === 'mirror') this.showRoute();
  }

  /** The flash also lights the way: glowing dots along the correct route through the mirror maze. */
  showRoute() {
    const P = this.level.points.mirror;
    const done = this.relics[7]?.taken || this.S.relics.includes(7);
    const goal = done ? tmp.set(0, 0, 36) : P.relic_7;
    if (!goal) return;
    const p = this.player.pos;
    const path = this.physics.path(p.x, p.z, goal.x, goal.z, 90000);
    if (!path || !path.length) return;
    const pts = [];
    let cur = { x: p.x, z: p.z }, left = 26;
    for (const w of path) {
      const seg = Math.hypot(w.x - cur.x, w.z - cur.z);
      const n = Math.max(1, Math.floor(seg / 1.1));
      for (let i = 1; i <= n && left > 0; i++) { pts.push(cur.x + (w.x - cur.x) * i / n, 0.08, cur.z + (w.z - cur.z) * i / n); left -= seg / n; }
      cur = w;
      if (left <= 0) break;
    }
    this.routeDots?.parent?.remove(this.routeDots);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const mat = new THREE.PointsMaterial({ color: 0xffe9a0, size: 0.28, transparent: true, depthWrite: false, opacity: 1 });
    this.routeDots = new THREE.Points(geo, mat);
    this.routeDots.frustumCulled = false;
    this.scene.add(this.routeDots);
    this.routeT = 7;
    this.hud.hint('閃光照出了一條路。', 3);
  }

  onFlickerDead() {
    this.S.hp = 0; this.save();
    this.hud.hint('閃閃散成了一地碎光。', 5);
    this.hud.say([{ text: '碎掉的燈泡裡，有一個很小的聲音在說：「謝謝。」', dur: 4.5 }]);
  }

  // ------------------------------------------------------------------ the finale
  startFinale() {
    if (this.puppet) return;
    this.S.finale = 1; this.save();
    const L = this.level, P = L.points.power, fd = P.finale_door;
    if (!fd) { this.finish(); return; }
    this.ticket.active = false; this.ticket.visible = false;
    this.flicker.active = false; this.flicker.vanish(1);
    this.allGigglers().forEach((g) => { g.active = false; g.visible = false; });
    // the puppet stands in the last long straight stretch of the maze before the door; you start at the other end of it
    const n4 = P.node_4;
    const route = (n4 && this.physics.path(n4.x, n4.z, fd.x, fd.z + 1.3, 60000)) || [];
    let a = n4 ? n4.clone() : new THREE.Vector3(fd.x, 0, fd.z + 8), b = new THREE.Vector3(fd.x, 0, fd.z + 3.2);
    for (let i = route.length - 1; i > 0; i--) {
      if (Math.hypot(route[i].x - route[i - 1].x, route[i].z - route[i - 1].z) >= 4.5) { a = new THREE.Vector3(route[i - 1].x, 0, route[i - 1].z); b = new THREE.Vector3(route[i].x, 0, route[i].z); break; }
    }
    const dir = b.clone().sub(a).setY(0).normalize();
    a.addScaledVector(dir, 0.5);
    this.checkpoint = { x: a.x, z: a.z, yaw: Math.atan2(-dir.x, -dir.z) };
    this.finaleSpot = this.checkpoint;
    const pu = (this.puppet = new DirectorPuppet(this));
    pu.pos.set(b.x, 0, b.z);
    pu.obj.rotation.y = Math.atan2(-dir.x, -dir.z);
    this.hud.fade(1, 0.15);
    this.after(1.8, () => this.hud.fade(0, 1.5));
    this.player.place(a.x, a.z, this.checkpoint.yaw);
    pu.visible = true; pu.active = true;
    pu.restore(); pu.phase = 0;
    const p = this.player;
    this.cinematic = true; p.frozen = true; this.input.enabled = false;
    audio.stinger(1); audio.rumble(pu.pos, 4, 1);
    this.refreshObjective();
    this.hud.objective('???');
    p.look(tmp.set(pu.pos.x, 3, pu.pos.z), 1.5);
    // all the lights go out for a moment, then his come on
    const savedI = L.lights.map((l) => l.intensity);
    L.lights.forEach((l) => { l.intensity = 0; });
    this.after(2.5, () => { audio.musicBox(pu.pos.clone().setY(3), 0.5); pu.light.intensity = 10; });
    this.after(2.5, () => { L.lights.forEach((l, i) => { l.intensity = savedI[i]; }); });
    let t = 4;
    for (const line of DIRECTOR3) {
      this.after(t, () => { this.hud.say([line], true); audio.voice(line.voice, { kind: 'pa', rate: 0.82 }); });
      t += line.dur + 0.4;
    }
    this.after(t, () => {
      pu.phase = 1;
      this.cinematic = false; p.frozen = false; this.input.enabled = true; p.lookTarget = null;
      this.hud.objective('剪斷人偶的提線');
      this.hud.hint('他的手腕被線吊著。用剪刀爪剪斷提線。', 7);
    });
  }

  cutString(spec) {
    const pu = spec.puppet, s = pu.strings[spec.index];
    if (s.cut) return;
    s.cut = true; s.line.visible = false;
    this.take(s.proxy);
    audio.clank(pu.pos, 1); audio.stinger(0.5); this.player.shake(0.6);
    pu.play('Idle', 0.1);
    if (pu.strings.every((x) => x.cut)) {
      pu.phase = 2; pu.cooldown = 3;
      this.hud.hint('兩條線都斷了，他動起來了！他舉手的時候，用閃光爪照他。', 8);
      this.hud.objective('用閃光爪讓人偶失明，再用帶電爪打他的胸口');
    } else this.hud.hint('一條線斷了。', 3);
  }

  hitPuppet(id, point) {
    const pu = this.puppet;
    if (!pu || pu.broken) return;
    if (id === 'flash') { this.flashBurst(point); return; }
    if (id !== 'charge') { audio.clank(point, 0.7); return; }
    if (pu.phase < 2 || pu.stun <= 0) { audio.clank(point, 0.7); this.hud.hint('他還在動。先用閃光爪讓他失明。', 4); return; }
    audio.zap(point);
    this.breakPuppet();
  }

  breakPuppet() {
    const pu = this.puppet, p = this.player, L = this.level;
    pu.broken = true; pu.wind = 0; pu.stun = 0;
    this.cinematic = true; p.frozen = true; this.input.enabled = false; this.claw.show(false);
    this.S.finale = 2; this.save();
    audio.stinger(1); audio.scream(0.8); this.r.u.warp.value = 1.5; p.shake(1.5);
    this.after(0.5, () => { this.r.u.warp.value = 0; });
    p.look(tmp.set(pu.pos.x, 3, pu.pos.z), 2);
    pu.mixer.timeScale = 0;
    pu.light.intensity = 30;
    this.anim(2.2, (k) => { pu.obj.rotation.x = -k * 1.45; pu.obj.position.y = k * 0.2; pu.light.intensity = 30 * (1 - k) + 1; });
    this.after(1.2, () => { audio.thud(pu.pos, 1); audio.clank(pu.pos, 1); audio.rumble(pu.pos, 3, 0.8); p.shake(1); });
    this.after(2.4, () => { if (pu.head) pu.head.scale.setScalar(0.001); });
    // the door opens: behind the puppet, cables run into the dark
    const fd = L.points.power.finale_door;
    this.after(3.5, () => {
      this.finaleCols.forEach((k) => L.dropCol(k)); this.physics.rebuild();
      if (this.finaleDoor) { const y0 = this.finaleDoor.position.y; this.anim(2, (k) => { this.finaleDoor.position.y = y0 + k * 3; }); }
      audio.doorCreak(new THREE.Vector3(fd.x, 1, fd.z)); audio.rumble(new THREE.Vector3(fd.x, 1, fd.z), 3, 0.7);
      const mat = new THREE.MeshStandardMaterial({ color: 0x15171a, roughness: 0.4, metalness: 0.8, emissive: 0x300808 });
      for (let i = 0; i < 5; i++) {
        const a = new THREE.Vector3(pu.pos.x - 0.4 + i * 0.2, 0.7, pu.pos.z - 0.8);
        const b = new THREE.Vector3(fd.x - 0.4 + i * 0.2, 0.15, fd.z - 14 - i);
        const c = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 6).translate(0, 0.5, 0), mat);
        c.position.copy(a); c.scale.set(1, a.distanceTo(b), 1);
        c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
        this.scene.add(c);
      }
      L.light(fd.x, 0.8, fd.z - 5, { color: 0xff3020, intensity: 2.5, distance: 12, flicker: 0.1 });
      p.look(tmp.set(fd.x, 0.6, fd.z - 12), 1.2);
    });
    let t = 5.5;
    for (const line of DIRECTOR3_BROKEN) {
      this.after(t, () => { this.hud.say([line], true); if (line.voice) audio.voice(line.voice, { kind: 'pa', rate: 0.78 }); });
      t += line.dur + 0.5;
    }
    this.after(t + 1, () => this.hud.fade(1, 3));
    this.after(t + 4.5, () => this.finish());
  }

  finish() {
    this.S.done = true; this.save();
    $('dead').classList.add('hidden');
    this.ended = true;
    this.paused = true;
    document.exitPointerLock?.();
    this.hud.show(false);
    $('endText').textContent = ENDING3 + `\n\n（找回的遺物：${this.S.relics.length}/9）`;
    $('ending').classList.remove('hidden');
    $('ch2Btn')?.classList.add('hidden');
    $('ch3Btn')?.classList.add('hidden');
    $('againBtn').onclick = () => { try { localStorage.removeItem(SAVE_KEY); } catch { /* ignore */ } location.reload(); };
    audio.musicBox(null, 0.3);
  }

  // ------------------------------------------------------------------ save restore
  applySave() {
    const S = this.S;
    S.claws.forEach((c) => this.giveClaw(c, true));
    S.cut.forEach((id) => this.cutSeal(id, true));
    if (S.gate) this.openGate(true);
    S.crates.forEach((n) => this.pullCrate(n, true));
    S.secrets.forEach((n) => this.revealSecret(n, true));
    S.cracks.forEach((n) => this.breakCrack(n, true));
    S.nodes.forEach((n) => this.powerNode(n, true));
    S.breakers.forEach((n) => this.closeBreaker(n, true));
    S.relics.forEach((n) => {
      const r = this.relics[n];
      if (!r) return;
      r.taken = r.done = true;
      this.take(r.obj);
      r.shadow.visible = false; r.shadow.state = 'gone';
      this.take(r.shadow.obj.children.find((c) => c.userData.interact));
    });
    if (S.tape && this.items.tape) { this.take(this.items.tape); this.flags.tapes = 1; }
    S.hands.forEach((c, i) => { if (c && this.clawInv.includes(c)) this.equipClaw(i, c, true); });
    if (!S.hands.some(Boolean) && this.clawInv.length) this.equipClaw(1, this.clawInv[0], true);
    this.lastGiven = 1;
    this.updateClawBar();
  }

  // ------------------------------------------------------------------ loop hooks
  updateMonsters(dt) {
    if (this.grace > 0) return;
    this.ticket.update(dt);
    this.flicker.update(dt);
    this.puppet?.update(dt);
    const pp = this.player.pos;
    for (const g of this.allGigglers()) if (g.visible) g.update(dt);
    for (const r of Object.values(this.relics)) if (r.shadow.visible && r.shadow.distTo(pp) < 70) r.shadow.update(dt);
  }

  updateWorld(dt) {
    this.introUpdate?.(dt);
    const p = this.player, I = this.input;
    // zone tracking
    const z = zoneAt(p.pos.x, -p.pos.z);
    if (z !== this.zone && !this.hauling) this.enterZone(z, this.zone);
    this.zoneT = (this.zoneT || 0) - dt;
    if (this.zoneT <= 0) { this.zoneT = 0.5; this.updateVisibility(); }

    // keys 1-6: left claw; Shift + 1-6: right claw
    if (!this.cinematic && !this.dying) {
      CLAWS.forEach((id, i) => {
        if (I.hit(`Digit${i + 1}`)) this.equipClaw(I.down('ShiftLeft') || I.down('ShiftRight') ? 1 : 0, id);
      });
    }
    this.updateHaul(dt);
    for (const id of CLAWS) { const o = this.items[`claw_${id}`]; if (o?.parent === this.scene) { o.rotation.y += dt * 0.9; } }
    // charged claws stay charged
    this.hands.forEach((id, i) => {
      if (id !== 'charge') return;
      const h = this.claw.hands[i];
      if (h.charged < 1e8) h.charged = 1e9;
      if (!h.hum && audio.ctx) h.hum = audio.hum();
    });
    if (this.routeDots) {
      this.routeT -= dt;
      this.routeDots.material.opacity = Math.max(0, Math.min(1, this.routeT / 2));
      if (this.routeT <= 0) { this.routeDots.parent?.remove(this.routeDots); this.routeDots = null; }
    }
    if (this.S.finale === 0 && this.S.breakers.length >= 3 && this.zone === 'power' && !this.cinematic) this.startFinale();
    if (this.S.finale === 1 && !this.puppet && this.zone === 'power') this.startFinale();
  }

  danger() {
    const p = this.player.pos;
    let danger = 0;
    const T = this.ticket;
    if (T.active && (T.state === 'chase' || T.state === 'charge')) danger = 1 - T.distTo(p) / 22;
    else if (T.active && T.visible) danger = Math.max(danger, (1 - T.distTo(p) / 14) * 0.5);
    const F = this.flicker;
    if (F.active && ['flash', 'rush'].includes(F.state)) danger = Math.max(danger, 1 - F.distTo(p) / 16);
    for (const g of this.allGigglers()) if (g.active && g.state === 'chase') danger = Math.max(danger, 1 - g.distTo(p) / 14);
    if (this.puppet?.visible && !this.puppet.broken && this.puppet.phase >= 2) danger = Math.max(danger, 0.5);
    return danger;
  }

  resetZone() {
    this.ticket.reset();
    if (this.ticket.active) this.ticket.place(this.patrol[this.zone] || [], this.player.pos);
    (this.gigglers[this.zone] || []).forEach((g) => g.reset());
    this.flicker.vanish(4);
    if (this.puppet && !this.puppet.broken) {
      const pu = this.puppet, s = pu.strings;
      pu.restore();
      pu.phase = s.length ? 1 : 1;
      this.hud.objective('剪斷人偶的提線');
    }
    this.hauling = null; this.rope.visible = false;
  }

  objectiveMarks() { return []; }
}

function L_drop(level, k) { level.dropCol(k); }
