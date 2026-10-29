import * as THREE from 'three';
import { spawn, setEmit } from './assets.js';
import { audio } from './audio.js';
import { Renderer } from './render.js';
import { Input } from './input.js';
import { Physics } from './physics.js';
import { Level, GATES_Z } from './level.js';
import { Player } from './player.js';
import { ClawPack, findInteract } from './clawpack.js';
import { HUD } from './hud.js';
import { Horse, Hornman, Grinny, Statue } from './monsters.js';
import { INTRO, PA, TAPES, ENDING } from './story.js';
import { polaroid, kidName, PHOTO_COUNT, dust } from './atmosphere.js';
import { drawParkMap } from './map.js';

const POOL = 7;
const v3 = new THREE.Vector3();
const $ = (id) => document.getElementById(id);

export class Game {
  constructor(canvas, { touch = false } = {}) {
    this.r = new Renderer(canvas);
    this.scene = this.r.scene;
    this.camera = this.r.camera;
    this.input = new Input(canvas);
    this.input.touchMode = touch;
    this.physics = new Physics();
    this.hud = new HUD();
    this.level = new Level(this.scene, this.physics);
    this.level.build();
    this.player = new Player(this.camera, this.scene);
    this.claw = new ClawPack(this.camera, this);
    this.time = 0;
    this.started = false;
    this.paused = true;
    this.dying = false;
    this.flags = { fuses: 0, fusesIn: 0, tapes: 0, rec2: 0, photos: 0 };
    this.zone = 'entrance';
    this.checkpoint = { x: 0, z: 63, yaw: 0 };
    this.timers = [];
    this.triggers = [];
    this.lightPool = Array.from({ length: POOL }, () => {
      const l = new THREE.PointLight(0xffffff, 0, 10, 1.7);
      this.scene.add(l);
      return l;
    });
    this.poolT = 0;
    this.setupWorld();
    this.input.onLockChange = (locked) => {
      if (!this.started || this.dying || this.ended) return;
      this.paused = !locked;
      $('pause').classList.toggle('hidden', locked);
    };
    $('volume').oninput = (e) => audio.setVolume(+e.target.value);
    $('sens').oninput = (e) => { this.input.sensitivity = +e.target.value; };
    $('pause').onclick = (e) => {
      if (['SELECT', 'INPUT', 'OPTION', 'LABEL'].includes(e.target.tagName)) return;
      if (this.input.touchMode) this.resume(); else this.input.lock();
    };
    let q = this.input.touchMode ? 'low' : 'mid';
    try { q = localStorage.getItem('quality') || q; } catch { /* storage unavailable */ }
    $('quality').value = q;
    this.r.setQuality(q, this.player.flashlight);
    $('quality').onchange = (e) => {
      this.r.setQuality(e.target.value, this.player.flashlight);
      try { localStorage.setItem('quality', e.target.value); } catch { /* ignore */ }
    };
    $('retryBtn').onclick = () => this.respawn();
    $('againBtn').onclick = () => location.reload();
  }

  pause() {
    if (!this.started || this.dying || this.ended) return;
    this.paused = true;
    $('pause').classList.remove('hidden');
  }

  resume() {
    this.paused = false;
    $('pause').classList.add('hidden');
  }

  // ------------------------------------------------------------------ helpers
  after(sec, fn) { this.timers.push({ t: this.time + sec, fn }); }
  pa(key) { const t = PA[key]; this.hud.say([{ who: '廣播', text: t, dur: 4.5 }]); audio.speak(t, { pitch: 0.45, rate: 0.8 }); }

  inView(p, margin = 1) {
    v3.copy(p).project(this.camera);
    return v3.z < 1 && Math.abs(v3.x) < margin && Math.abs(v3.y) < margin;
  }

  litByFlashlight(p) {
    if (!this.player.flashOn || this.player.flashlight.intensity < 6) return false;
    const cam = this.camera.getWorldPosition(new THREE.Vector3());
    const to = p.clone().sub(cam);
    const d = to.length();
    if (d > 24) return false;
    const fwd = this.camera.getWorldDirection(new THREE.Vector3());
    return to.normalize().dot(fwd) > Math.cos(0.42);
  }

  noiseAt(x, z, radius) { this.hornman?.active && this.hornman.hear(x, z, radius); }

  // ------------------------------------------------------------------ world wiring
  setupWorld() {
    const L = this.level, I = L.items;
    // entrance: claw pack, generator, receiver, statue
    L.interact(I.packPickup, { label: '撿起 抓抓爪', use: () => this.takePack() });
    L.interact(I.gen1, { kind: 'power', label: '發電機（用爪子抓住電球）' });
    L.interact(I.rec1, { kind: 'receiver', label: '電源接收器', powered: false, onPower: () => this.openGate() });
    this.statue = new Statue(this, L.points.statue);
    this.statue.active = true;
    // paper map on the ticket booth counter
    const paper = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.3), new THREE.MeshStandardMaterial({ color: 0xcdbf9c, roughness: 0.9 }));
    paper.rotation.set(-Math.PI / 2, 0, 0.3);
    paper.position.set(-5.4, 1.165, 52.2);
    this.scene.add(paper);
    L.interact(paper, { kind: 'pickup', label: '撿起 樂園導覽圖', item: 'map' });
    // polaroids of the missing children
    L.points.photos.forEach((pt, i) => {
      const ph = new THREE.Mesh(new THREE.PlaneGeometry(0.26, 0.31), new THREE.MeshStandardMaterial({ map: polaroid(i), roughness: 0.6 }));
      ph.rotation.set(-Math.PI / 2, 0, i * 1.3);
      ph.position.copy(pt).setY(pt.y + 0.01);
      this.scene.add(ph);
      L.interact(ph, { kind: 'pickup', label: '撿起 照片', item: 'photo', index: i });
      L.light(pt.x, pt.y + 0.5, pt.z, { color: 0xfff0d0, intensity: 0.5, distance: 2.2, flicker: 0.02 });
    });
    this.dustUpdate = dust(this.scene);

    // carousel plaza: fuses, batteries, fuse box, horses
    this.fuseObjs = L.points.fuses.map((p, i) => {
      const f = L.add('fuse', p.x, p.z, { y: p.y, rot: i });
      L.interact(f, { kind: 'pickup', label: '撿起 保險絲', item: 'fuse' });
      return f;
    });
    [...L.points.batteries2, ...L.points.batteries6].forEach((p) => this.addBattery(p));
    L.interact(I.fusebox, { label: '插入保險絲', use: () => this.insertFuses() });
    this.horses = L.points.horseHome.map(([x, z, r]) => new Horse(this, x, z, r));
    this.horses.forEach((h) => {
      h.obj.position.y = 0.4;
      L.interact(h.obj, { kind: 'horse', horse: h, label: '' });
    });

    // fun house
    const fp = L.points;
    const wps = ['a', 'b', 'c', 'd', 'e', 'f'].map((k) => fp['f' + k][0]);
    this.hornman = new Hornman(this, wps);
    this.hornman.visible = false;
    const kc = L.add('keycard', fp.fK[0].x, fp.fK[0].z, { y: 0.02 });
    L.interact(kc, { kind: 'pickup', label: '撿起 員工鑰匙卡', item: 'keycard' });
    const bt = fp.fB[0]; this.addBattery(new THREE.Vector3(bt.x, 0.02, bt.z));
    this.addTape(fp.fT[0], 'funhouse');
    const jb = (this.jackbox = L.add('jackbox', fp.fJ[0].x, fp.fJ[0].z, { collide: [0.6, 0.6], rot: 0.3 }));
    this.popper = jb.getObjectByName('Popper');
    this.lid = jb.getObjectByName('Lid');
    this.popper.position.y -= 0.7; this.popper.visible = false;
    this.trigger((p) => p.distanceTo(jb.position) < 2.4, () => this.jackScare());
    L.interact(I.fhDoor, { label: '用鑰匙卡開門', use: () => this.openFunDoor() });

    // tunnel
    this.addTape(fp.tT[0], 'tunnel1');
    this.addTape(fp.tT[1], 'tunnel2');
    L.interact(I.tunDoor, { label: '推開門', use: () => this.openTunnelDoor() });
    const wp = L.points.window;
    this.windowFace = new Grinny(this, wp.x + 2.2, wp.z);
    this.windowFace.obj.rotation.y = -Math.PI / 2;
    this.windowFace.obj.position.y = -1.15;
    this.windowFace.visible = false;
    this.trigger((p) => this.flags.tapes >= 2 && p.x > 3 && p.z < -50 && p.z > -56 && this.inView(new THREE.Vector3(wp.x, 1.7, wp.z), 0.5),
      () => this.windowScare());

    // coaster: gates, lever, chase
    I.gates.forEach((g) => L.interact(g.handle, { kind: 'handle', label: '閘門把手（用爪子拉）', gate: g,
      aimPoint: g.handle.position.clone().add(new THREE.Vector3(0, 1.35, 0.1)) }));
    L.interact(I.lever, { kind: 'lever', label: '拉下拉桿', use: () => this.pullLever() });
    this.grinny = new Grinny(this, 0, -64);
    this.grinny.visible = false;
    this.trigger((p) => p.z < -75 && !this.flags.chase, () => this.startChase(), true);

    // ferris
    L.interact(I.gen2, { kind: 'power', label: '發電機（用爪子抓住電球）' });
    I.receivers2.forEach((rc, i) => L.interact(rc, { kind: 'receiver', label: '摩天輪電源接收器', powered: false,
      onPower: () => this.powerWheel() }));
    this.director = spawn('director');
    this.director.position.set(0, -14, -177);
    this.director.scale.setScalar(2.4);
    this.directorLight = this.level.light(0, 7, -170, { color: 0xff2010, intensity: 0, distance: 26, flicker: 0.15 });
    this.director.visible = false;
    this.scene.add(this.director);

    // zone checkpoints / ambience
    const zones = [
      ['carousel', (p) => p.z < 39, { x: 0, z: 37, yaw: 0 }],
      ['funhouse', (p) => p.z < -1.5, { x: 0, z: -2.5, yaw: 0 }],
      ['tunnel', (p) => p.z < -37, { x: 0, z: -38.5, yaw: 0 }],
      ['coaster', (p) => p.z < -72, { x: 0, z: -72.5, yaw: 0 }],
      ['ferris', (p) => p.z < -145, { x: 0, z: -146, yaw: 0 }],
    ];
    zones.forEach(([name, test, cp]) => this.trigger(test, () => this.enterZone(name, cp)));
  }

  trigger(test, fn, repeatable = false) { this.triggers.push({ test, fn, repeatable, done: false }); }

  addBattery(p) {
    const b = this.level.add('battery', p.x, p.z, { y: p.y });
    this.level.interact(b, { kind: 'pickup', label: '撿起 電池', item: 'battery' });
  }

  addTape(p, id) {
    const t = this.level.add('cassette', p.x, p.z, { y: 0.02, rot: 0.7 });
    this.level.interact(t, { kind: 'pickup', label: '撿起 錄音帶', item: 'tape', tape: id });
    // a small lamp so tapes can be found in the dark
    this.level.light(p.x, 0.6, p.z, { color: 0xffd0a0, intensity: 1.2, distance: 3, flicker: 0.05 });
  }

  // ------------------------------------------------------------------ start / zones
  start() {
    audio.init();
    this.started = true;
    this.paused = false;
    this.hud.show(true);
    this.player.place(this.checkpoint.x, this.checkpoint.z, this.checkpoint.yaw);
    this.hud.fade(0, 3);
    this.hud.say(INTRO);
    this.hud.objective('進入樂園');
    this.after(22, () => this.pa('welcome'));
    this.after(24, () => this.hud.hint('售票亭附近好像有東西，櫃檯上還有一張導覽圖。按 E 互動。', 7));
    this.updateInventory();
  }

  enterZone(name, cp) {
    this.zone = name;
    this.checkpoint = cp;
    const indoor = name === 'funhouse' || name === 'tunnel';
    audio.setIndoor(indoor);
    this.player.surface = indoor ? 'wood' : 'ground';
    this.scene.fog.density = indoor ? 0.07 : 0.05;
    if (name === 'carousel') {
      this.statue.active = false; this.statue.visible = false;
      this.hud.objective('找到 3 根保險絲，替鬼屋接上電源（0/3）');
      this.hud.hint('保險絲可以用 E 撿起，太遠的可以用爪子抓回來。', 6);
    }
    if (name === 'funhouse') {
      this.horses.forEach((h) => (h.active = false));
      this.musicBox?.stop();
      this.hornman.visible = true; this.hornman.active = true;
      this.pa('funhouse');
      this.hud.objective('找到員工鑰匙卡，從後門離開鬼屋');
      this.after(5, () => this.hud.hint('有東西在聽。按 C 蹲下可以安靜移動，奔跑會被聽見。', 8));
      this.after(14, () => this.hud.hint('用爪子打牆會發出聲響，可以把他引開。', 7));
    }
    if (name === 'tunnel') {
      this.hornman.active = false; this.hornman.visible = false;
      this.hud.objective('穿過員工通道');
    }
    if (name === 'coaster') this.hud.objective('???');
    if (name === 'ferris') {
      this.hud.objective('替摩天輪接上電源（0/4）');
      this.after(2, () => this.pa('ferris'));
    }
  }

  // ------------------------------------------------------------------ zone 1
  takePack() {
    const I = this.level.items;
    this.scene.remove(I.packPickup);
    this.level.rayTargets.splice(this.level.rayTargets.indexOf(I.packPickup), 1);
    this.flags.pack = true;
    this.claw.show(true);
    audio.pickup();
    this.hud.objective('替大門接上電源');
    this.hud.hint('滑鼠左鍵 / 右鍵：發射左爪 / 右爪。', 6);
    this.after(6.5, () => this.hud.hint('用一隻爪子抓住發電機上的藍色電球，帶著電，再用同一隻爪子碰大門的接收器。', 9));
  }

  powerReceiver(spec, handIndex) {
    if (spec.powered) return;
    spec.powered = true;
    this.claw.discharge(handIndex);
    const sock = spec.obj.getObjectByName('Socket');
    sock.traverse((o) => o.isMesh && o.material.color.set(0x40ff70));
    setEmit(sock, 2.5);
    audio.zap(spec.obj.position);
    spec.onPower?.();
  }

  openGate() {
    const I = this.level.items;
    audio.rumble(I.arch.position, 2.5, 0.5);
    audio.doorCreak(I.arch.position);
    this.anim(2.5, (k) => { I.doorL.rotation.y = k * 1.45; I.doorR.rotation.y = -k * 1.45; });
    this.physics.setEnabled(I.gateCollider, false);
    this.hud.objective('進入樂園');
    this.after(1, () => this.pa('gate'));
  }

  // ------------------------------------------------------------------ zone 2
  collect(spec) {
    const o = spec.obj;
    o.parent?.remove(o);
    const i = this.level.rayTargets.indexOf(o);
    if (i >= 0) this.level.rayTargets.splice(i, 1);
    audio.pickup();
    if (spec.item === 'battery') {
      this.player.battery = Math.min(100, this.player.battery + 45);
      this.hud.hint('手電筒電量 +45%', 2);
    } else if (spec.item === 'fuse') {
      this.flags.fuses++;
      this.hud.objective(`找到 3 根保險絲，替鬼屋接上電源（${this.flags.fuses}/3）`);
      if (this.flags.fuses === 1) this.wakeHorses();
      if (this.flags.fuses === 3) this.hud.objective('把保險絲插進鬼屋門口的配電箱');
    } else if (spec.item === 'photo') {
      this.flags.photos++;
      this.hud.hint(`照片：${kidName(spec.index)}（${this.flags.photos}/${PHOTO_COUNT}）`, 4);
      audio.whisper();
    } else if (spec.item === 'map') {
      this.flags.map = true;
      this.hud.hint('拿到樂園導覽圖。按 M 打開地圖。', 6);
    } else if (spec.item === 'keycard') {
      this.flags.keycard = true;
      this.hud.objective('用鑰匙卡打開鬼屋後門');
    } else if (spec.item === 'tape') {
      this.flags.tapes++;
      const tape = TAPES[spec.tape];
      this.hud.say([{ text: `▶ ${tape.title}`, dur: 2 }, ...tape.lines], true);
      const speakAll = (k) => {
        if (k >= tape.lines.length) return;
        audio.speak(tape.lines[k].text.replace(/[（）()「」]/g, ''), { pitch: 0.5, rate: 0.85 });
      };
      this.after(2, () => speakAll(0));
      this.after(2 + tape.lines[0].text.length * 0.16, () => speakAll(1));
      this.after(2 + (tape.lines[0].text.length + tape.lines[1].text.length) * 0.16, () => speakAll(2));
    }
    this.updateInventory();
  }

  updateInventory() {
    const f = this.flags;
    this.hud.inventory([
      f.fuses && f.fusesIn < 3 ? `保險絲 ${f.fuses}/3` : '',
      f.keycard ? '員工鑰匙卡' : '',
      f.tapes ? `錄音帶 ${f.tapes}/3` : '',
      f.photos ? `照片 ${f.photos}/${PHOTO_COUNT}` : '',
      f.map ? '<span style="opacity:.6">[M] 地圖</span>' : '',
    ]);
  }

  wakeHorses() {
    const L = this.level;
    this.flags.horses = true;
    this.musicBox = audio.musicBox(L.items.carousel.position.clone().setY(3), 0.7);
    L.items.carouselLight.intensity = 7;
    audio.stinger(0.5);
    this.pa('carousel');
    this.after(3, () => {
      this.horses.forEach((h, i) => {
        const p = L.points.horseWake[i];
        h.pos.set(p.x, 0, p.z);
        h.active = true;
      });
      audio.creak(L.items.carousel.position, 0.8);
    });
    this.after(6, () => this.hud.hint('骨馬只在你沒有用手電筒照著牠們的時候移動。注意電量。', 9));
  }

  insertFuses() {
    const f = this.flags;
    if (f.fuses === 0) { this.hud.hint('配電箱少了 3 根保險絲。', 3); return; }
    f.fusesIn = f.fuses;
    audio.clank(this.level.items.fusebox.position, 0.5);
    if (f.fusesIn < 3) { this.hud.hint(`已插入 ${f.fusesIn}/3 根保險絲。`, 3); return; }
    const I = this.level.items;
    this.updateInventory();
    audio.zap(I.fusebox.position);
    audio.rumble(I.funhouse.position, 2, 0.6);
    this.anim(2, (k) => { I.jaw.position.y = -k * 3.3; });
    this.physics.setEnabled(I.jawCollider, false);
    this.hud.objective('進入鬼屋');
    this.horses.forEach((h) => (h.active = false));
    this.after(0.5, () => audio.giggle(I.funhouse.position.clone().setY(3), 0.6));
  }

  // ------------------------------------------------------------------ zone 3
  jackScare() {
    const jb = this.jackbox;
    audio.stinger(0.9);
    audio.giggle(jb.position, 0.9);
    this.popper.visible = true;
    this.anim(0.15, (k) => { this.popper.position.y = 0.3 - 0.7 + k * 0.9; this.lid.rotation.x = -k * 1.9; });
    this.player.shake(0.6);
    this.r.u.warp.value = 1;
    this.after(0.4, () => (this.r.u.warp.value = 0));
    this.noiseAt(jb.position.x, jb.position.z, 30);
  }

  openFunDoor() {
    if (!this.flags.keycard) { this.hud.hint('門鎖住了，需要員工鑰匙卡。', 3); return; }
    this.openDoor(this.level.items.fhDoor, this.level.items.fhDoorCollider);
    this.flags.funDoor = true;
  }

  openDoor(model, collider) {
    const d = model.getObjectByName('Door');
    audio.doorCreak(model.position);
    this.anim(1.2, (k) => { d.rotation.y = k * 1.5; });
    this.physics.setEnabled(collider, false);
    const i = this.level.rayTargets.indexOf(model);
    if (i >= 0) model.userData.interact = null;
  }

  // ------------------------------------------------------------------ zone 4
  windowScare() {
    const f = this.windowFace;
    f.visible = true;
    f.play('Idle', 0, 2);
    audio.stinger(1.0);
    audio.giggle(f.pos, 0.8);
    this.r.u.warp.value = 1.2;
    this.player.shake(0.4);
    this.after(0.55, () => {
      f.visible = false;
      this.r.u.warp.value = 0;
      this.blackout = 2.2;
    });
  }

  openTunnelDoor() {
    this.openDoor(this.level.items.tunDoor, this.level.items.tunDoorCollider);
    this.hud.objective('離開員工通道');
  }

  // ------------------------------------------------------------------ zone 5
  startChase() {
    this.flags.chase = true;
    this.player.adrenaline = true;
    const g = this.grinny;
    g.pos.set(0, 0, -67);
    g.obj.rotation.set(0, Math.PI, 0);
    g.visible = true;
    g.state = 'idle';
    g.maxSpeed = 5.75;
    g.speed = 2;
    this.pa('chase');
    audio.giggle(new THREE.Vector3(0, 2, -66), 1);
    this.hud.objective('快跑！');
    this.after(2.2, () => {
      audio.rumble(new THREE.Vector3(0, 1, -70), 1.2, 0.9);
      audio.stinger(1.0);
      this.player.shake(0.8);
      g.state = 'chase';
      this.hud.hint('邊跑邊用爪子拉開閘門的把手！', 5);
    });
  }

  openGate2(gate) {
    if (gate.open) return;
    gate.open = true;
    audio.clank(gate.model.position, 0.9);
    audio.rumble(gate.model.position, 1, 0.5);
    this.anim(0.9, (k) => { gate.grate.position.y = k * 3.2; });
    this.after(0.45, () => this.physics.setEnabled(gate.collider, false));
  }

  pullLever() {
    if (this.flags.bridgeDown) return;
    if (this.player.pos.z > -142.5) { this.hud.hint('先過橋。', 2); return; }
    this.flags.bridgeDown = true;
    const I = this.level.items;
    const h = I.lever.getObjectByName('Handle');
    this.anim(0.4, (k) => { h.rotation.x = -k * 1.2; });
    audio.clank(I.lever.position, 1);
    audio.rumble(I.bridge.position, 2.5, 1);
    const g = this.grinny;
    if (g.state === 'chase') {
      g.state = 'idle';
      g.pos.set(0, 0, Math.min(g.pos.z, -135.5));
      g.playOnce('Attack', 1.2);
    }
    this.after(0.5, () => {
      this.anim(1.6, (k) => { I.bridge.position.y = -k * k * 30; I.bridge.rotation.x = k * 0.6; });
      if (g.visible) { g.state = 'fall'; audio.giggle(g.pos, 1); this.after(0.6, () => audio.scream(0.5)); }
      this.physics.setEnabled(I.pitBlock, true);
    });
    this.after(3, () => {
      this.player.adrenaline = false;
      this.hud.objective('前往摩天輪');
    });
  }

  // ------------------------------------------------------------------ zone 6
  powerWheel() {
    const f = this.flags;
    f.rec2++;
    const I = this.level.items;
    this.hud.objective(`替摩天輪接上電源（${f.rec2}/4）`);
    audio.rumble(I.ferris.position.clone().setY(10), 2, 0.6);
    const startA = I.wheel.rotation.z;
    this.anim(2.5, (k) => { I.wheel.rotation.z = startA + k * (Math.PI / 4); });
    setEmit(I.ferris, f.rec2 / 4);
    I.wheelLight.intensity = 3 + f.rec2 * 3;
    if (f.rec2 === 2) this.after(2, () => audio.giggle(new THREE.Vector3(0, 10, -186), 0.7));
    if (f.rec2 === 4) this.after(2.8, () => this.finale());
  }

  finale() {
    const I = this.level.items, p = this.player;
    this.cinematic = true;
    p.frozen = true;
    this.input.enabled = false;
    this.claw.show(false);
    p.look(new THREE.Vector3(0, 9, -190), 1.5);
    this.musicBox = audio.musicBox(new THREE.Vector3(0, 10, -186), 0.9);
    this.wheelSpin = 0.6;
    this.after(3, () => this.pa('final'));
    this.after(5, () => {
      const d = this.director;
      d.visible = true;
      audio.rumble(new THREE.Vector3(0, 2, -192), 6, 1);
      audio.stinger(1);
      this.directorLight.intensity = 26;
      this.anim(6, (k) => { d.position.y = -14 + k * 14; p.shake(0.4); });
      p.look(new THREE.Vector3(0, 6, -177), 1.2);
    });
    this.after(11.5, () => {
      audio.scream(1);
      p.look(new THREE.Vector3(0, 6.5, -172), 6);
      this.r.u.red.value = 0.8;
      this.r.u.warp.value = 2;
      p.shake(1.5);
      const from = this.director.position.z, to = Math.min(p.pos.z - 4, -160);
      this.anim(0.6, (k) => { this.director.position.z = from + k * (to - from); });
    });
    this.after(12.4, () => {
      this.hud.fade(1, 0.05);
      this.r.u.red.value = 0;
      this.musicBox?.stop();
    });
    this.after(15, () => this.showEnding());
  }

  showEnding() {
    this.ended = true;
    this.paused = true;
    document.exitPointerLock?.();
    this.hud.show(false);
    $('endText').textContent = ENDING + (this.flags.photos >= PHOTO_COUNT
      ? '\n\n你帶著八張照片離開了。\n至少，還有人記得他們的名字。'
      : `\n\n（找到的照片：${this.flags.photos}/${PHOTO_COUNT}）`);
    $('ending').classList.remove('hidden');
    audio.musicBox(null, 0.35);
  }

  // ------------------------------------------------------------------ claws & interaction
  onClawHit(index, hit, point, hand) {
    const it = hit?.interact;
    if (!it) {
      if (hit) {
        audio.clank(point, 0.7);
        this.noiseAt(point.x, point.z, 15);
      }
      return;
    }
    switch (it.kind) {
      case 'power':
        this.claw.charge(index);
        audio.zap(point);
        if (!this.flags.chargeHint) { this.flags.chargeHint = true; this.hud.hint('這隻爪子帶電了！快去碰接收器。', 4); }
        break;
      case 'receiver':
        if (this.claw.hands[index].charged > 0) this.powerReceiver(it, index);
        else { audio.clank(point, 0.6); this.hud.hint('接收器沒有電。先用同一隻爪子抓住發電機的電球。', 4); }
        break;
      case 'pickup':
        hand.carry = it.obj;
        this.scene.attach(it.obj);
        break;
      case 'handle':
        this.openGate2(it.gate);
        break;
      case 'lever':
        this.pullLever();
        break;
      case 'horse':
        it.horse.shatter(point);
        if (!this.flags.shatterHint) { this.flags.shatterHint = true; this.hud.hint('骨馬碎了！牠 5 秒後就會拼回來。', 4); }
        break;
      default:
        audio.clank(point, 0.6);
        it.use?.();
    }
  }

  onClawReturn(index, obj) {
    const spec = obj.userData.interact;
    if (spec) this.collect(spec);
  }

  interact() {
    const a = this.claw.aim(this.level.rayTargets);
    const it = a?.interact;
    if (!it || a.distance > 2.8) return;
    if (it.kind === 'pickup') this.collect(it);
    else it.use?.();
  }

  // ------------------------------------------------------------------ paper map
  toggleMap() {
    if (!this.flags.map) { this.hud.hint('你還沒有地圖。售票亭的櫃檯上好像有一張。', 3); return; }
    this.mapOpen = !this.mapOpen;
    $('mapOverlay').classList.toggle('hidden', !this.mapOpen);
    if (this.mapOpen) audio.clawGrab();
  }

  drawMap() {
    const c = $('mapCanvas');
    const h = Math.min(innerHeight * 0.9, 980);
    const w = Math.round(h * 0.42);
    if (c.width !== w * 2) { c.width = w * 2; c.height = h * 2; c.style.width = w + 'px'; c.style.height = h + 'px'; }
    drawParkMap(c.getContext('2d'), c.width, c.height, {
      orient: 'v', player: this.player.pos, yaw: this.player.yaw, marks: this.objectiveMarks(),
    });
  }

  /** World positions the current objective points at (for the map). */
  objectiveMarks() {
    const f = this.flags, I = this.level.items, P = this.level.points;
    const live = (o) => o && o.parent;
    if (!f.pack) return [I.packPickup.position];
    if (!I.rec1.userData.interact.powered) return [I.gen1.position, I.rec1.position];
    if (f.fuses < 3) return this.fuseObjs.filter(live).map((o) => o.position);
    if (f.fusesIn < 3) return [I.fusebox.position];
    if (!f.keycard) return [P.fK[0]];
    if (!f.funDoor) return [I.fhDoor.position];
    if (this.level.items.tunDoorCollider.enabled) return [I.tunDoor.position];
    if (!f.bridgeDown) return [I.lever.position];
    return I.receivers2.filter((r) => !r.userData.interact.powered).map((r) => r.position).concat([I.gen2.position]);
  }

  // ------------------------------------------------------------------ death
  caught(monster, tip) {
    if (this.dying || this.cinematic || this.grace > 0) return;
    this.dying = true;
    this.killer = monster;
    if (this.mapOpen) this.toggleMap();
    const p = this.player;
    p.frozen = true;
    this.input.enabled = false;
    const f = p.forward;
    monster.pos.set(p.pos.x + f.x * 1.4, 0, p.pos.z + f.z * 1.4);
    monster.obj.rotation.set(0, Math.atan2(-f.x, -f.z), 0);
    monster.visible = true;
    monster.playOnce?.('Attack', 1.6);
    const faceY = monster instanceof Horse ? 1.9 : monster instanceof Hornman ? 2.5 : 2.9;
    p.look(new THREE.Vector3(monster.pos.x, faceY, monster.pos.z), 14);
    p.flashOn = true;
    audio.scream(1);
    this.r.u.red.value = 0.6;
    this.r.u.warp.value = 2;
    p.shake(2);
    this.deathTip = tip;
    this.after(1.3, () => {
      this.hud.fade(1, 0.1);
      this.r.u.red.value = 0; this.r.u.warp.value = 0;
    });
    this.after(1.8, () => {
      document.exitPointerLock?.();
      $('deadMsg').textContent = tip || '';
      $('dead').classList.remove('hidden');
      this.paused = true;
    });
  }

  respawn() {
    $('dead').classList.add('hidden');
    const cp = this.checkpoint;
    const p = this.player;
    p.place(cp.x, cp.z, cp.yaw);
    p.frozen = false;
    p.battery = Math.max(p.battery, 40);
    p.stamina = 100;
    this.input.enabled = true;
    this.dying = false;
    this.grace = 2.5;
    this.hud.fade(0, 1.2);
    // reset the zone's threats
    if (this.zone === 'carousel' && this.flags.horses && this.flags.fusesIn < 3) {
      this.horses.forEach((h, i) => { const s = this.level.points.horseWake[i]; h.mend(); h.pos.set(s.x, 0, s.z); h.path = null; });
    }
    if (this.zone === 'funhouse') this.hornman.reset();
    if (this.zone === 'coaster' && !this.flags.bridgeDown) {
      this.flags.chase = false;
      this.grinny.state = 'idle';
      this.grinny.visible = false;
      this.grinny.pos.set(0, 0, -64);
      this.level.items.gates.forEach((g) => {
        g.open = false; g.grate.position.y = 0; this.physics.setEnabled(g.collider, true);
      });
      this.triggers.find((t) => t.repeatable).done = false;
    }
    this.input.lock();
    this.paused = false;
  }

  // ------------------------------------------------------------------ tweening
  anim(dur, fn) {
    const start = this.time;
    const a = { start, dur, fn };
    (this.anims ||= []).push(a);
  }

  // ------------------------------------------------------------------ loop
  update(dt) {
    this.time += dt;
    const p = this.player;
    // timers and tweens
    for (const t of this.timers.filter((t) => t.t <= this.time)) { this.timers.splice(this.timers.indexOf(t), 1); t.fn(); }
    if (this.anims) for (const a of [...this.anims]) {
      const k = Math.min(1, (this.time - a.start) / a.dur);
      a.fn(k * k * (3 - 2 * k));
      if (k >= 1) this.anims.splice(this.anims.indexOf(a), 1);
    }

    p.update(dt, this.input, this.physics);
    this.claw.update(dt);

    // input actions
    if (!this.dying && !this.cinematic) {
      if (this.claw.enabled) {
        if (this.input.click(0)) this.claw.fire(0, this.level.rayTargets);
        if (this.input.click(2)) this.claw.fire(1, this.level.rayTargets);
      }
      if (this.input.hit('KeyE')) this.interact();
      if (this.input.hit('KeyM') || this.input.hit('Tab')) this.toggleMap();
      const a = this.claw.aim(this.level.rayTargets);
      const it = a?.interact;
      const near = it && a.distance < 2.8 && (it.use || it.kind === 'pickup');
      this.hud.prompt(near ? `[E] ${it.label}` : '');
      this.hud.crosshair(it && this.claw.enabled && a.distance < 20, this.claw.hands.some((h) => h.charged > 0));
      for (const t of this.triggers) {
        if (t.done) continue;
        if (t.test(p.pos)) { t.done = true; t.fn(); }
      }
    }

    // monsters (frozen during a jumpscare, except the one that caught you)
    if (this.dying) {
      this.killer?.mixer?.update(dt);
    } else {
      this.grace = (this.grace || 0) - dt;
      this.statue.update(dt);
      if (this.grace <= 0) this.horses.forEach((h) => h.update(dt));
      if (this.grace <= 0) this.hornman.update(dt);
      this.grinny.update(dt);
      this.windowFace.update(dt);
    }

    // ambient motion
    for (const u of this.level.updaters) u(dt);
    this.dustUpdate(dt, p.pos);
    if (this.mapOpen) this.drawMap();
    // carousel & wheel motion
    const I = this.level.items;
    I.teacupSpin.rotation.y += dt * 0.06;
    if (this.flags.horses && this.flags.fusesIn < 3) I.carouselSpin.rotation.y += dt * 0.25;
    if (this.wheelSpin) I.wheel.rotation.z += dt * this.wheelSpin;
    for (const c of I.cabins) c.rotation.z = -I.wheel.rotation.z;
    if (this.director.visible) this.director.scale.setScalar(2.4 * (1 + Math.sin(this.time * 2) * 0.02));

    // tunnel blackout after the window scare
    if (this.blackout > 0) {
      this.blackout -= dt;
      p.flickerOverride = this.blackout > 0.3 ? 0 : undefined;
      if (this.blackout <= 0) p.flickerOverride = undefined;
    }

    // danger -> heartbeat, vignette, drone
    let danger = 0;
    const consider = (m, range) => { if (m.active || m.state === 'chase') danger = Math.max(danger, 1 - m.distTo(p.pos) / range); };
    this.horses.forEach((h) => h.active && !h.frozen && consider(h, 14));
    if (this.hornman.active) consider(this.hornman, 12);
    if (this.grinny.state === 'chase') consider(this.grinny, 24);
    danger = Math.max(0, Math.min(1, danger));
    audio.update(dt, danger);
    audio.setDread(danger);
    this.r.u.pulse.value += ((danger > 0.3 ? Math.abs(Math.sin(this.time * 6)) * danger : 0) - this.r.u.pulse.value) * Math.min(1, dt * 8);
    this.r.u.grain.value = 0.05 + danger * 0.05;

    // HUD meters
    this.hud.battery(p.battery);
    this.hud.stamina(p.stamina);
    this.hud.claws(this.claw.state(0), this.claw.state(1));
    this.hud.update(dt);
    this.updateLights(dt);
    audio.updateListener(this.camera);
  }

  updateLights(dt) {
    const p = this.player.pos;
    this.poolT -= dt;
    if (this.poolT <= 0) {
      this.poolT = 0.4;
      const ls = this.level.lights.filter((l) => l.on && l.intensity > 0)
        .map((l) => [l, l.pos.distanceToSquared(p)]).sort((a, b) => a[1] - b[1]).slice(0, POOL);
      this.assigned = ls.map((x) => x[0]);
    }
    this.lightPool.forEach((pl, i) => {
      const l = this.assigned?.[i];
      if (!l) { pl.intensity = 0; return; }
      pl.position.copy(l.pos);
      pl.color.copy(l.color);
      pl.distance = l.distance;
      let k = 1;
      if (l.flicker && Math.random() < l.flicker * 0.25) k = Math.random() * 0.5;
      if (this.blackout > 0.3) k = 0;
      pl.intensity = l.intensity * k * 7;
    });
  }

  frame(dt) {
    if (this.started && !this.paused) this.update(Math.min(dt, 0.05));
    else if (this.dying) { // keep animating the jumpscare while the death screen fades in
      this.time += dt; this.player.update(dt, this.input, this.physics);
      for (const t of this.timers.filter((t) => t.t <= this.time)) { this.timers.splice(this.timers.indexOf(t), 1); t.fn(); }
    }
    this.onHudTick?.();
    this.input.endFrame();
    this.r.render(performance.now() / 1000);
  }
}
