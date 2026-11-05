// Chapter 2: the toy factory under the park. Same game loop as Chapter 1 (Game), different world.
import * as THREE from 'three';
import { spawn, loadJSON, animator } from './assets.js';
import { audio } from './audio.js';
import { Game } from './game.js';
import { Level } from './level.js';
import { Monster } from './monsters.js';
import { INTRO2, PA2, TAPES2, NAME_TAG, ENDING2, THROW } from './story.js';
import { dust } from './atmosphere.js';

const ZONE_FILES = ['zone_a_entry', 'zone_b_lockers', 'zone_c_sewing', 'zone_d_packing', 'zone_e_warehouse', 'zone_f_core'];
const tmp = new THREE.Vector3();
let DATA = null;

/** Zone chunks are authored in Blender coordinates (Z up, route along +Y). */
const toWorld = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

/** Fetch the zone JSON (colliders, lights, markers) before the game is built. */
export async function loadChapter2() {
  const [manifest, ...zones] = await Promise.all([loadJSON('ch2/manifest.json'), ...ZONE_FILES.map((z) => loadJSON(`ch2/${z}.json`))]);
  DATA = { manifest, zones: Object.fromEntries(ZONE_FILES.map((z, i) => [z, zones[i]])) };
}

// ------------------------------------------------------------------------- level
class Level2 extends Level {
  build() {
    const { scene } = this;
    scene.background = new THREE.Color(0x030304);
    scene.fog = new THREE.FogExp2(0x030304, 0.06);
    scene.add(new THREE.HemisphereLight(0x3a4250, 0x0c0908, 0.3));

    // invisible stand-ins for walls so claws and the interaction ray stop at them
    const wallMat = new THREE.MeshBasicMaterial({ visible: false });
    const unitBox = new THREE.BoxGeometry(1, 1, 1);
    const addBlock = ([cx, cy, cz, sx, sy, sz, rz]) => {
      const lo = cz - sz / 2, hi = cz + sz / 2;
      if (lo > 1.9 || hi < 0.3) return; // overhead (rails, gantry) or flat floor dressing
      this.physics.boxAt(cx, -cy, sx, sy, rz);
      const m = new THREE.Mesh(unitBox, wallMat);
      m.position.copy(toWorld(cx, cy, cz));
      m.scale.set(sx, sz, sy);
      m.rotation.y = rz;
      scene.add(m);
      this.rayTargets.push(m);
    };

    for (const name of ZONE_FILES) {
      scene.add(spawn(`ch2/${name}`));
      const z = DATA.zones[name];
      z.colliders.forEach(addBlock);
      for (const li of z.lights) {
        const [x, y, h] = li.pos;
        this.light(x, h, -y, { color: li.color, intensity: li.intensity * 3.5, distance: li.range * 1.4, flicker: li.flicker ? 0.25 : 0.01 });
      }
      this.points[name.split('_')[1]] = Object.fromEntries(Object.entries(z.markers).map(([k, [x, y, h]]) => [k, toWorld(x, y, h)]));
    }
    scene.add(spawn('ch2/zone_seams'));
    DATA.manifest.seams.colliders.forEach(addBlock);
    this.physics.rebuild();
  }
}

// ------------------------------------------------------------------------- the Seamstress
/**
 * Hangs from the ceiling rail loop in the sewing hall and only moves along it. She notices a
 * flashlight beam on her or footsteps nearby, then glides along the rails toward you; get under
 * her while she's hunting and she strikes. Crouch, turn the light off and keep away from the rails.
 */
class Seamstress extends Monster {
  constructor(game, loop) {
    super(game, 'seamstress', loop[0].x, loop[0].z, 1.0);
    // hang the trolley on the rail: the model's top sits at the rail's bottom flange
    const box = new THREE.Box3().setFromObject(this.obj);
    this.hang = 5.25 - box.max.y;
    this.faceY = 3.2;
    this.buildGraph(loop);
    this.node = this.nodes.findIndex((n) => n.z === loop[0].z && n.x === loop[0].x);
    this.route = [];
    this.state = 'patrol';
    this.alert = 0;
    this.timer = 0;
    this.snipT = 2;
    this.start = this.node;
    this.place();
    this.play('Glide', 0);
  }

  /** Rail graph: the loop (with the cross rail's two ends spliced in) plus the cross rail at x = 0. */
  buildGraph(loop) {
    const nodes = loop.map((p) => ({ x: p.x, z: p.z }));
    const edges = nodes.map((_, i) => [(i + 1) % nodes.length, (i + nodes.length - 1) % nodes.length]);
    const near = (x, z) => nodes.reduce((b, n, i) => (Math.hypot(n.x - x, n.z - z) < Math.hypot(nodes[b].x - x, nodes[b].z - z) ? i : b), 0);
    const zs = loop.map((p) => p.z);
    const zA = Math.max(...zs), zB = Math.min(...zs); // near and far ends of the loop
    const ends = [near(0, zA), near(0, zB)];
    let prev = ends[0];
    for (let z = zA - 4; z > zB + 2; z -= 4) {
      const i = nodes.push({ x: 0, z }) - 1;
      edges.push([prev]); edges[prev].push(i);
      prev = i;
    }
    edges[prev].push(ends[1]); edges[ends[1]].push(prev);
    this.nodes = nodes; this.edges = edges;
  }

  nearestNode(x, z) {
    let best = 0, bd = Infinity;
    this.nodes.forEach((n, i) => { const d = Math.hypot(n.x - x, n.z - z); if (d < bd) { bd = d; best = i; } });
    return best;
  }

  /** Breadth-first route along the rails (nodes are evenly spaced, so hops are a fine cost). */
  routeTo(goal) {
    const prev = new Map([[this.node, -1]]);
    const q = [this.node];
    while (q.length) {
      const c = q.shift();
      if (c === goal) break;
      for (const n of this.edges[c]) if (!prev.has(n)) { prev.set(n, c); q.push(n); }
    }
    const out = [];
    for (let c = goal; c !== this.node && c !== undefined && c !== -1; c = prev.get(c)) out.unshift(c);
    return out;
  }

  place() { this.pos.y = this.hang; }

  reset() {
    this.node = this.start;
    const n = this.nodes[this.node];
    this.pos.set(n.x, this.hang, n.z);
    this.route = []; this.state = 'patrol'; this.alert = 0;
  }

  glide(speed, dt) {
    let step = speed * dt;
    while (step > 0 && this.route.length) {
      const n = this.nodes[this.route[0]];
      const dx = n.x - this.pos.x, dz = n.z - this.pos.z, d = Math.hypot(dx, dz);
      if (d < 0.02) { this.node = this.route.shift(); continue; }
      const s = Math.min(step, d);
      this.pos.x += (dx / d) * s; this.pos.z += (dz / d) * s;
      this.face(n.x, n.z, dt, 3);
      step -= s;
      if (s === d) this.node = this.route.shift();
    }
  }

  update(dt) {
    super.update(dt);
    if (!this.active) return;
    const g = this.game, pl = g.player, p = pl.pos;
    const d = this.distTo(p);
    // what she notices: a beam on her, or footsteps (not crouching) close by
    const lit = g.litByFlashlight(tmp.set(this.pos.x, 3.4, this.pos.z));
    const heard = pl.noise > 2 && d < pl.noise * 0.9;
    if ((lit && d < 16) || heard) {
      if (this.state !== 'hunt') { audio.stinger(0.5); this.snipT = 0; }
      this.state = 'hunt';
      this.alert = 5;
    }
    if (this.state === 'patrol') {
      this.play('Glide', 0.5, 0.8);
      if (!this.route.length) {
        const e = this.edges[this.node];
        this.route = [e[Math.floor(Math.random() * e.length)]];
        if (Math.random() < 0.15) { this.state = 'search'; this.timer = 3; }
      }
      this.glide(1.4, dt);
    } else if (this.state === 'search') {
      this.play('Search', 0.5);
      this.timer -= dt;
      if (this.timer <= 0) this.state = 'patrol';
    } else if (this.state === 'hunt') {
      this.play('Glide', 0.3, 1.6);
      this.alert -= dt;
      this.repath -= dt;
      if (this.repath <= 0) { this.route = this.routeTo(this.nearestNode(p.x, p.z)); this.repath = 0.5; }
      this.glide(3.1, dt);
      if (this.alert <= 0) { this.state = 'search'; this.timer = 3; this.route = []; }
      if (d < 2.4 && !pl.crouched) g.caught(this, '縫線娘娘看得見燈光，也聽得見腳步聲。關掉手電筒、按 C 蹲下，離她的軌道遠一點。');
      else if (d < 1.4) g.caught(this, '就算蹲著，也不要從她的正下方經過。');
    }
    this.snipT -= dt;
    if (this.snipT <= 0) { audio.clank(tmp.set(this.pos.x, 4, this.pos.z), this.state === 'hunt' ? 0.5 : 0.18); this.snipT = this.state === 'hunt' ? 0.6 : 2.5 + Math.random() * 3; }
    this.place();
  }
}

// ------------------------------------------------------------------------- Gigglers
/**
 * Small wind-up toys that wander and run at you once they see you. A flashlight beam makes them
 * stop and giggle for a moment; a claw hit knocks one over for a few seconds.
 */
class Giggler extends Monster {
  constructor(game, home, patrol) {
    super(game, 'giggler', home.x, home.z, 0.3);
    this.home = home.clone();
    this.patrol = patrol;
    this.wp = Math.floor(Math.random() * patrol.length);
    this.state = 'wander';
    this.timer = 0;
    this.giggleT = 2 + Math.random() * 4;
    this.faceY = 0.6;
    this.play('Walk', 0);
  }

  reset() {
    this.pos.copy(this.home);
    this.obj.rotation.set(0, 0, 0);
    this.state = 'wander'; this.path = null; this.timer = 0;
  }

  knock() {
    this.state = 'down'; this.timer = 4;
    this.obj.rotation.z = Math.PI / 2;
    audio.giggle(this.pos, 0.5);
  }

  update(dt) {
    super.update(dt);
    if (!this.active) return;
    const g = this.game, pl = g.player, p = pl.pos;
    const d = this.distTo(p);
    const sees = d < (pl.crouched ? 4 : 9) && g.physics.lineClear(this.pos.x, this.pos.z, p.x, p.z);
    if (this.state === 'down') {
      this.timer -= dt;
      if (this.timer <= 0) { this.obj.rotation.z = 0; this.state = 'chase'; }
      return;
    }
    if (this.state !== 'chase' && this.state !== 'stunned' && sees) {
      this.state = 'chase'; this.lost = 0;
      audio.giggle(this.pos, 0.8);
    }
    if (this.state === 'wander') {
      this.play('Walk', 0.4);
      const w = this.patrol[this.wp];
      if (this.goTo(w.x, w.z, 1.1, dt, 1)) this.wp = Math.floor(Math.random() * this.patrol.length);
    } else if (this.state === 'chase') {
      if (g.litByFlashlight(tmp.set(this.pos.x, 0.5, this.pos.z)) && d < 12) {
        this.state = 'stunned'; this.timer = 1.6;
        audio.giggle(this.pos, 0.9);
        return;
      }
      this.play('Run', 0.2, 1.2);
      this.goTo(p.x, p.z, 3.5, dt, 0.3);
      this.lost = sees ? 0 : this.lost + dt;
      if (this.lost > 4 || d > 20) this.state = 'wander';
      if (d < 0.95) g.caught(this, '笑笑兵被手電筒照到會停下來咯咯笑；用爪子可以把它們打倒幾秒。');
    } else if (this.state === 'stunned') {
      this.play('Idle', 0.2);
      this.face(p.x, p.z, dt);
      this.timer -= dt;
      if (this.timer <= 0) this.state = 'chase';
    }
    this.giggleT -= dt;
    if (this.giggleT <= 0) { audio.giggle(this.pos, this.state === 'chase' ? 0.6 : 0.2); this.giggleT = 3 + Math.random() * 5; }
  }
}

// ------------------------------------------------------------------------- chapter flow
export class Chapter2 extends Game {
  buildLevel() {
    const level = new Level2(this.scene, this.physics);
    level.build();
    return level;
  }

  setupWorld() {
    const L = this.level, P = L.points;
    this.flags = { tapes: 0, nameTag: false };
    this.zone = 'a';
    const e = P.a.entry;
    this.checkpoint = { x: e.x, z: e.z, yaw: -Math.PI / 2 };
    this.dustUpdate = dust(this.scene);
    this.flags.pack = true;
    this.claw.show(true);

    // pickups
    const tape = (pt, id) => {
      const t = L.add('cassette', pt.x, pt.z, { y: pt.y + 0.02, rot: 0.7 });
      L.interact(t, { kind: 'pickup', label: '撿起 錄音帶', item: 'tape2', tape: id });
      L.light(pt.x, pt.y + 0.6, pt.z, { color: 0xffd0a0, intensity: 1.2, distance: 3, flicker: 0.05 });
    };
    tape(P.a.clipboard, 'guard');
    tape(new THREE.Vector3(P.e.hide_cabin_c.x + 1.6, 0, P.e.hide_cabin_c.z), 'warehouse');
    const nt = P.b.pickup_name_tag;
    const tag = L.add('name_tag', nt.x, nt.z, { y: nt.y, scale: 2, rot: 0.4 });
    L.interact(tag, { kind: 'pickup', label: '撿起 名牌', item: 'nametag' });
    L.light(nt.x, nt.y + 0.6, nt.z, { color: 0xffe0b0, intensity: 1, distance: 2.5, flicker: 0.05 });
    [P.a.hide_pallets, P.c.hide_04, P.d.hide_2, P.e.hide_west_aisle].forEach((pt) => {
      const b = L.add('battery', pt.x + 0.6, pt.z, { y: 0.02 });
      L.interact(b, { kind: 'pickup', label: '撿起 電池', item: 'battery' });
    });

    // the Seamstress on the sewing-hall rails
    const rail = Object.keys(P.c).filter((k) => k.startsWith('rail_')).sort().map((k) => P.c[k]);
    this.seamstress = new Seamstress(this, rail);
    this.seamstress.visible = false;

    // Gigglers: packing hall and warehouse; two more wait in the machine chamber
    const pts = (zone, prefix) => Object.keys(P[zone]).filter((k) => k.startsWith(prefix)).map((k) => P[zone][k]);
    const make = (homes, patrol) => homes.map((h) => new Giggler(this, h, patrol));
    this.gigglers = {
      d: make(pts('d', 'giggler_spawn'), pts('d', 'patrol')),
      e: make(pts('e', 'spawn').slice(0, 2), pts('e', 'patrol')),
      f: make(pts('f', 'spawn'), pts('f', 'patrol')),
    };
    this.allGigglers().forEach((gg) => { gg.visible = false; this.level.interact(gg.obj, { kind: 'giggler', giggler: gg, label: '' }); });

    // the off switch, in front of the Eternal Joy machine
    const m = P.f.machine;
    const lever = (this.lever = L.add('lever', m.x + 1.6, m.z + 2.0, { rot: Math.PI, collide: [0.5, 0.5] }));
    L.interact(lever, { kind: 'lever', label: '拉下拉桿：關掉永恆歡樂機', use: () => this.pullLever() });
    this.machineLight = L.light(m.x, 4, m.z, { color: 0xffb040, intensity: 2, distance: 16, flicker: 0.1 });

    // zones: checkpoints, enemies and announcements as you go deeper (route runs toward -Z)
    const zones = [['b', -16], ['c', -34], ['d', -74], ['e', -114], ['f', -144]];
    zones.forEach(([name, z]) => this.trigger((p) => p.z < z - 0.8, () => this.enterZone(name)));
  }

  allGigglers() { return Object.values(this.gigglers).flat(); }

  start() {
    audio.init();
    this.started = true;
    this.paused = false;
    this.hud.show(true);
    this.throwIntro(() => this.beginChapter());
  }

  /**
   * Opening: in a black void behind the elevator shaft the director holds you up to his mask,
   * talks, winds up and throws you down. You fall on your back watching him shrink above you,
   * hit the bottom, and wake in the freight elevator.
   */
  throwIntro(done) {
    const p = this.player, Z = 24; // empty space behind zone A's start wall
    const d = spawn('director');
    d.position.set(0, 0, Z - 1.2);
    this.scene.add(d);
    const anim = animator(d);
    anim.play('Idle', { fade: 0 });
    this.introUpdate = (dt) => anim.mixer.update(dt);
    const face = new THREE.Vector3(0, 4.3, Z - 0.95);
    const red = this.level.light(0.6, 5.8, Z + 0.8, { color: 0xff3a20, intensity: 3, distance: 9, flicker: 0.12 });
    const cold = this.level.light(-1.5, 3, Z + 1.5, { color: 0x9ab0ff, intensity: 1.2, distance: 6, flicker: 0.02 });
    this.cinematic = true;
    p.frozen = true;
    this.input.enabled = false;
    this.claw.show(false);
    p.place(0, Z + 0.15, 0);
    p.pos.y = face.y - 1.6; // held up in his hand, level with the mask
    p.look(face, 30);
    this.hud.fade(0, 1.6);
    audio.musicBox(new THREE.Vector3(0, 4, Z), 0.35);
    let t = 1.6;
    for (const line of THROW) {
      this.after(t, () => { this.hud.say([line], true); audio.voice(line.voice, { kind: 'pa', rate: 0.82 }); });
      t += line.dur + 0.3;
    }
    this.after(t, () => { anim.play('Throw', { once: true, fade: 0.1 }); audio.giggle(face, 0.8); p.shake(0.4); });
    this.after(t + 0.9, () => {
      audio.stinger(1);
      p.shake(1.2);
      const y0 = p.pos.y;
      this.anim(2.4, (k) => {
        p.pos.y = y0 - k * k * 45;
        p.pos.z = Z + 0.15 + k * 1.5;
        p.look(face, 6 + k * 20); // tumble back, staring up at him as he shrinks away
      });
    });
    this.after(t + 3.3, () => {
      this.hud.fade(1, 0.05);
      audio.thud(p.pos, 1);
      audio.clank(null, 0.9);
      p.shake(2);
    });
    this.after(t + 4.6, () => {
      this.scene.remove(d);
      this.introUpdate = null;
      red.intensity = 0; cold.intensity = 0;
      p.frozen = false;
      this.input.enabled = true;
      this.claw.show(true);
      this.cinematic = false;
      done();
    });
  }

  beginChapter() {
    this.player.place(this.checkpoint.x, this.checkpoint.z, this.checkpoint.yaw);
    this.player.surface = 'ground';
    audio.setIndoor(true);
    this.scene.fog.density = 0.06;
    this.hud.fade(0, 3);
    this.hud.say(INTRO2);
    this.hud.objective('離開貨梯，往工廠深處走');
    this.after(18, () => this.pa2('arrive'));
    this.after(21, () => this.hud.hint('警衛亭的櫃檯上好像有一捲錄音帶。按 E 互動。', 7));
    this.updateInventory();
  }

  pa2(key) { const t = PA2[key]; this.hud.say([{ who: '廣播', text: t, dur: 4.5 }]); audio.voice(`pa_${key}`, { kind: 'pa', rate: 0.88 }); }

  enterZone(name) {
    this.zone = name;
    const e = this.level.points[name].entry;
    this.checkpoint = { x: e.x, z: e.z, yaw: 0 };
    if (name === 'b') this.hud.objective('穿過員工置物間');
    if (name === 'c') {
      this.seamstress.visible = true; this.seamstress.active = true;
      this.pa2('sewing');
      this.hud.objective('穿過縫製大廳，不要被縫線娘娘發現');
      this.after(4, () => this.hud.hint('她吊在天花板的軌道上。手電筒照到她、或是走路太大聲，她就會滑過來。按 F 關燈、按 C 蹲下。', 9));
    }
    if (name === 'd') {
      this.seamstress.active = false; this.seamstress.visible = false;
      this.gigglers.d.forEach((g) => { g.visible = true; g.active = true; });
      this.pa2('packing');
      this.hud.objective('穿過包裝大廳');
      this.after(4, () => this.hud.hint('笑笑兵被手電筒照到會停下來；用爪子可以把它們打倒。', 7));
    }
    if (name === 'e') {
      this.gigglers.d.forEach((g) => { g.active = false; g.visible = false; });
      this.gigglers.e.forEach((g) => { g.visible = true; g.active = true; });
      this.pa2('warehouse');
      this.hud.objective('找到倉庫的出口');
    }
    if (name === 'f') {
      this.gigglers.e.forEach((g) => { g.active = false; g.visible = false; });
      this.pa2('core');
      this.hud.objective('關掉永恆歡樂機');
      this.after(3, () => {
        this.gigglers.f.forEach((g) => { g.visible = true; g.active = true; g.state = 'chase'; });
        audio.stinger(0.8);
        audio.giggle(this.level.points.f.machine, 1);
      });
    }
  }

  // ------------------------------------------------------------------ items
  collect(spec) {
    if (spec.item === 'tape2') {
      const o = spec.obj;
      o.parent?.remove(o);
      this.level.rayTargets.splice(this.level.rayTargets.indexOf(o), 1);
      audio.pickup();
      this.flags.tapes++;
      this.playTape(spec.tape, TAPES2[spec.tape]);
      this.updateInventory();
      return;
    }
    if (spec.item === 'nametag') {
      const o = spec.obj;
      o.parent?.remove(o);
      this.level.rayTargets.splice(this.level.rayTargets.indexOf(o), 1);
      audio.pickup();
      audio.whisper();
      this.flags.nameTag = true;
      this.hud.say(NAME_TAG, true);
      this.updateInventory();
      return;
    }
    super.collect(spec);
  }

  updateInventory() {
    const f = this.flags;
    this.hud.inventory([f.tapes ? `錄音帶 ${f.tapes}/2` : '', f.nameTag ? '阿梅的名牌' : '']);
  }

  toggleMap() { this.hud.hint('這裡沒有地圖。只能一直往裡面走。', 3); }

  onClawHit(index, hit, point, hand) {
    if (hit?.interact?.kind === 'giggler') { hit.interact.giggler.knock(); return; }
    super.onClawHit(index, hit, point, hand);
  }

  // ------------------------------------------------------------------ finale
  pullLever() {
    if (this.flags.leverDown) return;
    this.flags.leverDown = true;
    const h = this.lever.getObjectByName('Handle');
    if (h) this.anim(0.4, (k) => { h.rotation.x = -k * 1.2; });
    audio.clank(this.lever.position, 1);
    this.allGigglers().forEach((g) => { g.active = false; g.play('Idle', 0.3); });
    const p = this.player, m = this.level.points.f.machine;
    this.cinematic = true;
    p.frozen = true;
    this.input.enabled = false;
    this.claw.show(false);
    p.look(new THREE.Vector3(m.x, 3, m.z), 1.5);
    audio.rumble(m, 4, 1);
    this.anim(3, (k) => { this.machineLight.intensity = 2 + k * 10; p.shake(0.3); });
    this.after(3, () => { audio.stinger(1); this.r.u.warp.value = 1.5; });
    this.after(3.6, () => { this.r.u.warp.value = 0; this.musicBox = audio.musicBox(new THREE.Vector3(m.x, 3, m.z), 0.8); });
    this.after(6, () => this.hud.fade(1, 3));
    this.after(9.5, () => this.showEnding());
  }

  showEnding() {
    this.ended = true;
    this.paused = true;
    document.exitPointerLock?.();
    this.hud.show(false);
    document.getElementById('endText').textContent = ENDING2 + (this.flags.tapes >= 2 ? '' : `\n\n（找到的錄音帶：${this.flags.tapes}/2）`);
    document.getElementById('ending').classList.remove('hidden');
    document.getElementById('ch2Btn')?.classList.add('hidden');
    this.musicBox?.stop();
    audio.musicBox(null, 0.35);
  }

  objectiveMarks() { return []; }

  // ------------------------------------------------------------------ loop hooks
  updateMonsters(dt) {
    if (this.grace > 0) return;
    this.seamstress.update(dt);
    this.allGigglers().forEach((g) => g.update(dt));
  }

  updateWorld(dt) {
    this.introUpdate?.(dt);
    if (this.flags.leverDown) return;
    this.machineLight.intensity = 2 + Math.sin(this.time * 3) * 0.6;
  }

  danger() {
    const p = this.player.pos;
    let danger = 0;
    if (this.seamstress.active && this.seamstress.state === 'hunt') danger = 1 - this.seamstress.distTo(p) / 18;
    for (const g of this.allGigglers()) if (g.active && g.state === 'chase') danger = Math.max(danger, 1 - g.distTo(p) / 14);
    return danger;
  }

  resetZone() {
    if (this.zone === 'c') this.seamstress.reset();
    (this.gigglers[this.zone] || []).forEach((g) => { g.reset(); if (this.zone === 'f') g.state = 'chase'; });
  }
}
