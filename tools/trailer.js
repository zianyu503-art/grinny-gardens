// Scripted gameplay trailer, rendered frame by frame with the real game engine.
// Run in the dev server page:  const T = await import('/tools/trailer.js'); T.setup(); await T.renderFrames(0, 300); ...
// Frames and the soundtrack are POSTed to a local receiver (tools/receiver.py) and encoded by Blender (tools/encode_video.py).
import * as THREE from 'three';
import { Audio, audio as gameAudio } from '/src/audio.js';
import { setEmit } from '/src/assets.js';

export const FPS = 30, W = 1280, H = 720, DURATION = 62;
const RECEIVER = 'http://127.0.0.1:8766/';

let g, p, L, out, ctx, cur = null;
const S = {}; // per-shot scratch state

// ------------------------------------------------------------------ helpers
const ease = (k) => k * k * (3 - 2 * k);
const clamp01 = (k) => Math.max(0, Math.min(1, k));
const lerp = (a, b, k) => a + (b - a) * k;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

function cam(x, y, z, tx, ty, tz) {
  p.pos.set(x, 0, z);
  p.eye = y;
  const dx = tx - x, dz = tz - z;
  p.yaw = Math.atan2(-dx, -dz);
  p.pitch = Math.atan2(ty - y, Math.hypot(dx, dz));
}

function faceCamera(obj) { obj.rotation.y = Math.atan2(p.pos.x - obj.position.x, p.pos.z - obj.position.z); }

async function post(name, body) {
  const r = await fetch(RECEIVER + name, { method: 'POST', body });
  if (!r.ok) throw new Error('receiver failed ' + name);
}

// ------------------------------------------------------------------ setup
export function setup() {
  g = window.game; p = g.player; L = g.level;
  gameAudio.init(); gameAudio.setVolume(0); // game sounds stay silent; the soundtrack is rendered offline
  document.getElementById('title').classList.add('hidden');
  g.hud.show(false);
  g.started = true; g.paused = false;
  g.triggers.length = 0; g.timers.length = 0;
  g.r.setQuality('high', p.flashlight);
  const r = g.r;
  r.resize = () => {};
  r.renderer.setPixelRatio(0.75); r.renderer.setSize(W, H, false);
  r.composer.setPixelRatio(0.75); r.composer.setSize(W, H);
  g.camera.aspect = W / H; g.camera.updateProjectionMatrix();
  // cinematic camera: the trailer drives position/orientation directly
  p.update = function (dt) {
    this.flashlight.intensity = this.flashOn ? 45 * (this.flickerOverride ?? 1) : 0;
    this.syncCamera(dt);
  };
  p.flashOn = true; p.battery = 100;
  for (const m of [...g.horses, g.hornman, g.grinny, g.statue, g.windowFace]) { m.active = false; }
  g.hornman.visible = false; g.grinny.visible = false; g.statue.visible = false;
  out = document.createElement('canvas');
  out.width = W; out.height = H;
  ctx = out.getContext('2d');
  cur = null;
}

// ------------------------------------------------------------------ shots
const SHOTS = [
  { t0: 0, t1: 5, card: 'title' },
  {
    t0: 5, t1: 11, enter() {
      g.claw.show(false);
      g.statue.visible = true; g.statue.pos.set(1.5, 0, 31);
      g.statue.play('Idle', 0, 0.1);
    },
    update(t) {
      const k = ease(t / 6);
      cam(0, 1.62, lerp(66, 53, k), 0, 3.0, 40);
      p.speed = 2.6; p.bob += (1 / FPS) * 8;
      faceCamera(g.statue.obj);
      if (t > 4.4) g.statue.visible = false; // gone when you look again
    },
  },
  {
    t0: 11, t1: 17, enter() { g.claw.show(true); L.items.packPickup.visible = false; p.speed = 0; S.fired = 0; },
    update(t) {
      const orb = V(8, 2.05, 47), sock = V(5.2, 1.25, 42.4), arch = V(0, 2.6, 38);
      let look = orb;
      if (t > 2) look = orb.clone().lerp(sock, ease(clamp01((t - 2) / 0.8)));
      if (t > 4) look = sock.clone().lerp(arch, ease(clamp01((t - 4) / 1.6)));
      cam(5.6, 1.62, 49.8, look.x, look.y, look.z);
      if (t > 0.5 && S.fired === 0) { S.fired = 1; g.claw.fire(0, L.rayTargets); }
      if (t > 3.2 && S.fired === 1) { S.fired = 2; g.claw.fire(0, L.rayTargets); }
    },
  },
  {
    t0: 17, t1: 25, enter() {
      g.flags.horses = true;
      L.items.carouselLight.intensity = 7;
      S.h = g.horses[0];
      S.h.pos.set(-1.5, 0, 28.6); S.h.obj.position.y = 0;
    },
    update(t) {
      const carousel = V(0, 2.4, 20), head = V(S.h.pos.x, 1.6, S.h.pos.z);
      let look = carousel.clone().add(V(-1 + t * 0.4, 0, 0));
      if (t > 2.5) look = look.lerp(head, ease(clamp01((t - 2.5) / 0.7)));
      cam(-6.5, 1.62, 34, look.x, look.y, look.z);
      faceCamera(S.h.obj);
      if (t > 4.3 && t < 4.9) p.flickerOverride = 0;
      if (t >= 4.9 && !S.moved) {
        S.moved = true; p.flickerOverride = undefined;
        S.h.pos.set(-5.3, 0, 32.3); p.shake(0.7);
      }
      if (S.moved) {
        cam(-6.5, 1.62, 34, S.h.pos.x, 1.85, S.h.pos.z);
        faceCamera(S.h.obj);
      }
    },
  },
  {
    t0: 25, t1: 31, enter() {
      g.scene.fog.density = 0.07;
      const h = g.hornman;
      h.visible = true; h.pos.set(-5, 0, -3); h.obj.rotation.y = Math.PI / 2;
      h.play('Walk', 0, 0.8);
    },
    update(t) {
      const h = g.hornman;
      if (t < 5.2) h.pos.x = -5 + 0.95 * t; else h.play('Listen', 0.5, 1);
      cam(11, 1.0, -3, h.pos.x, 1.9, -3);
    },
  },
  {
    t0: 31, t1: 36, enter() { g.hornman.visible = false; g.windowFace.visible = false; },
    update(t) {
      const w = L.points.window;
      cam(7.6, 1.62, -53, w.x, 1.7, w.z);
      if (t > 2.6 && !S.face) {
        S.face = true; g.windowFace.visible = true; g.windowFace.play('Idle', 0, 2);
        g.r.u.warp.value = 1.2; p.shake(0.4);
      }
      if (t > 3.2 && S.face && !S.dark) { S.dark = true; g.windowFace.visible = false; g.r.u.warp.value = 0; g.blackout = 2.2; }
    },
  },
  {
    t0: 36, t1: 46, enter() {
      g.scene.fog.density = 0.05;
      g.blackout = 0; p.flickerOverride = undefined;
      L.items.gates.slice(0, 2).forEach((gt) => { gt.open = true; gt.grate.position.y = 3.2; g.physics.setEnabled(gt.collider, false); });
      const gr = g.grinny;
      gr.visible = true; gr.state = 'idle'; gr.obj.rotation.set(0, Math.PI, 0);
      gr.play('Run', 0, 1.3);
      S.fire = false;
    },
    update(t) {
      const z = -74 - 5.6 * t;
      p.speed = 5.6; p.bob += (1 / FPS) * 13;
      let yaw = 0, pitch = -0.04;
      if (t > 3 && t < 5.4) yaw = Math.PI * ease(clamp01((t - 3) / 0.4)) * (1 - ease(clamp01((t - 5) / 0.4)));
      const handle = V(3.2, 1.35, -121.4);
      p.pos.set(0, 0, z); p.eye = 1.62;
      if (t > 5.4 && t < 6.2) {
        const dx = handle.x, dz = handle.z - z;
        const k = ease(clamp01((t - 5.4) / 0.3)) * (1 - ease(clamp01((t - 5.95) / 0.25)));
        yaw = Math.atan2(-dx, -dz) * k;
        pitch = lerp(-0.04, Math.atan2(handle.y - 1.62, Math.hypot(dx, dz)), k);
        if (t > 5.6 && !S.fire) { S.fire = true; p.yaw = yaw; p.pitch = pitch; g.claw.fire(1, L.rayTargets); }
      }
      p.yaw = yaw; p.pitch = pitch;
      const gr = g.grinny;
      gr.pos.set(Math.sin(t * 2.1) * 0.4, 0, z + lerp(7.5, 5, t / 10));
      if (Math.floor(t / 0.36) !== S.step) { S.step = Math.floor(t / 0.36); p.shake(0.25); }
    },
  },
  {
    t0: 46, t1: 54, enter() {
      g.grinny.visible = false;
      setEmit(L.items.ferris, 1); L.items.wheelLight.intensity = 15; g.wheelSpin = 0.25;
      const d = g.director; d.visible = true; d.position.set(0, -14, -177);
      g.scene.fog.density = 0.028;
    },
    update(t) {
      const d = g.director;
      let look = V(0, 9, -186);
      if (t > 2) {
        g.directorLight.intensity = 26;
        d.position.y = -14 + 14 * ease(clamp01((t - 2) / 4.6));
        look = look.lerp(V(0, 6, -177), ease(clamp01((t - 2) / 2)));
        p.shake(0.35);
      }
      if (t > 6.5) {
        const k = ease(clamp01((t - 6.5) / 0.6));
        d.position.z = lerp(-177, -167, k);
        g.r.u.red.value = 0.8 * k; g.r.u.warp.value = 2 * k; p.shake(1.5);
        look = V(0, 6.5, d.position.z);
      }
      cam(4, 1.62, -163, look.x, look.y, look.z);
    },
  },
  {
    t0: 54, t1: 56, enter() {
      g.director.visible = false; g.directorLight.intensity = 0; g.wheelSpin = 0;
      g.r.u.red.value = 0; g.r.u.warp.value = 0; g.claw.show(false); g.scene.fog.density = 0.05;
      const gr = g.grinny; gr.visible = true; gr.state = 'idle';
      gr.pos.set(0, 0, -101.3); gr.obj.rotation.set(0, 0, 0);
      gr.playOnce('Attack', 1.6);
    },
    update(t) {
      cam(0, 1.62, -100, 0, 2.9, -101.3);
      if (t > 0.25 && t < 1.1) { g.r.u.red.value = 0.6; g.r.u.warp.value = 2; p.shake(2); }
      else { g.r.u.red.value = 0; g.r.u.warp.value = 0; }
    },
  },
  { t0: 56, t1: 62, card: 'end' },
];

// black overlay (0..1) over time
function fadeAt(t) {
  if (t < 5) return 0;
  if (t < 5.8) return 1 - (t - 5) / 0.8;
  if (t >= 53.4 && t < 54.25) return 1;
  if (t >= 54 && t < 54.25) return 1;
  if (t >= 55.1 && t < 56) return 1;
  return 0;
}

const SUBS = [
  [5.4, 8.2, '1996 年 8 月 31 日，微笑樂園在一夜之間關閉。'],
  [8.3, 10.9, '那天晚上，二十七個孩子沒有回家。'],
  [17.4, 20.2, '廣播：旋轉木馬即將啟動……請小朋友坐好，不要下來。'],
  [20.6, 24.6, '牠們只在你看不見的時候移動。'],
  [25.4, 30.6, '廣播：噓……鬼屋裡，要保持安靜喔。'],
  [36.3, 39.2, '廣播：要不要……玩捉迷藏？'],
  [47, 50.2, '廣播：你終於來了。'],
];

// ------------------------------------------------------------------ 2D overlays
function glitchText(text, x, y, size, alpha = 1, weight = 'bold') {
  ctx.font = `${weight} ${size}px "PingFang TC", "Heiti TC", sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.globalAlpha = alpha * 0.8;
  ctx.fillStyle = '#b01010'; ctx.fillText(text, x + 3, y);
  ctx.fillStyle = '#1050b0'; ctx.fillText(text, x - 3, y);
  ctx.globalAlpha = alpha;
  ctx.fillStyle = '#e4d8bc'; ctx.fillText(text, x, y);
  ctx.globalAlpha = 1;
}

function noise(amount) {
  for (let i = 0; i < amount; i++) {
    ctx.fillStyle = `rgba(255,255,255,${Math.random() * 0.06})`;
    ctx.fillRect(Math.random() * W, Math.random() * H, 2 + Math.random() * 60, 1);
  }
}

function drawCard(kind, t) {
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  noise(220);
  if (kind === 'title') {
    ctx.font = '22px "Courier New", monospace'; ctx.textAlign = 'left'; ctx.fillStyle = '#d8d8d8';
    ctx.fillText('PLAY ▶   AUG. 31 1996   23:58', 40, 48);
    const a = clamp01((t - 0.8) / 1.2), b = clamp01((t - 2.2) / 1.0), out = 1 - clamp01((t - 4.3) / 0.7);
    const jitter = Math.random() < 0.08 ? (Math.random() - 0.5) * 14 : 0;
    glitchText('微笑樂園', W / 2 + jitter, H / 2 - 30, 120, a * out);
    glitchText('最後一場表演', W / 2, H / 2 + 70, 38, b * out, 'normal');
  } else {
    const a = clamp01(t / 1.2), b = clamp01((t - 1.8) / 1), c = clamp01((t - 2.8) / 1), out = 1 - clamp01((t - 5.3) / 0.7);
    glitchText('微笑樂園：最後一場表演', W / 2, H / 2 - 60, 72, a * out);
    glitchText('免費線上遊玩　·　電腦／手機', W / 2, H / 2 + 30, 30, b * out, 'normal');
    ctx.globalAlpha = c * out;
    ctx.font = '26px "Courier New", monospace'; ctx.fillStyle = '#c8c0a8'; ctx.textAlign = 'center';
    ctx.fillText('zianyu503-art.github.io/grinny-gardens', W / 2, H / 2 + 90);
    ctx.globalAlpha = 1;
  }
}

function drawOverlay(t, isCard) {
  const f = fadeAt(t);
  if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, W, H); }
  if (f < 1 && !isCard) {
    // VHS on-screen display
    ctx.font = '20px "Courier New", monospace'; ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(230,230,230,.85)';
    const s = Math.floor(t) % 60;
    ctx.fillText(`PLAY ▶   AUG. 31 1996   23:59:${String(s).padStart(2, '0')}`, 36, 44);
  }
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  if (sub && f < 0.5) {
    const [a, b, text] = sub;
    const alpha = Math.min(clamp01((t - a) / 0.25), clamp01((b - t) / 0.25));
    const [who, line] = text.includes('：') ? text.split('：') : [null, text];
    ctx.font = '30px "PingFang TC", "Heiti TC", sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.globalAlpha = alpha;
    ctx.shadowColor = '#000'; ctx.shadowBlur = 8;
    const full = who ? `${who}：${line}` : line;
    ctx.fillStyle = '#efe6d0'; ctx.fillText(full, W / 2, H - 80);
    if (who) {
      const wFull = ctx.measureText(full).width, wWho = ctx.measureText(who + '：').width;
      ctx.textAlign = 'left'; ctx.fillStyle = '#d8a050'; ctx.fillText(who + '：', W / 2 - wFull / 2, H - 80);
    }
    ctx.shadowBlur = 0; ctx.globalAlpha = 1;
  }
}

// ------------------------------------------------------------------ frame loop
export async function renderFrames(f0, f1) {
  f1 = Math.min(f1, DURATION * FPS);
  for (let f = f0; f < f1; f++) {
    const t = f / FPS;
    const shot = SHOTS.find((s) => t >= s.t0 && t < s.t1);
    if (shot !== cur) {
      cur = shot;
      for (const k of Object.keys(S)) delete S[k];
      shot.enter?.();
      if (!shot.card) g.r.u.warp.value = Math.max(g.r.u.warp.value, 1.4); // tape glitch on every cut
    }
    if (shot.card) {
      drawCard(shot.card, t - shot.t0);
    } else {
      shot.update(t - shot.t0, t);
      g.frame(1 / FPS);
      if (g.r.u.warp.value > 0 && !S.keepWarp) g.r.u.warp.value = Math.max(0, g.r.u.warp.value - 0.5);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(g.r.renderer.domElement, 0, 0, W, H);
    }
    drawOverlay(t, !!shot.card);
    await post(`f${String(f).padStart(5, '0')}.jpg`, out.toDataURL('image/jpeg', 0.9));
  }
  return f1;
}

// ------------------------------------------------------------------ soundtrack (offline)
export async function renderAudio() {
  const SR = 48000;
  const off = new OfflineAudioContext(2, SR * DURATION, SR);
  const a = new Audio();
  a.init(off);
  a.setVolume(0.9);
  const at = (t, fn) => { a.at = t; fn(); a.at = undefined; };
  const every = (t0, t1, step, fn) => { for (let t = t0; t < t1; t += step) at(t, () => fn(t)); };

  // title
  at(0.3, () => a.setDread(0.2));
  at(0.6, () => a.rumble(null, 3, 0.35));
  at(1.0, () => a.stinger(0.35));
  // entrance
  a.musicBoxAt(5, 6, 0.18, 2);
  every(5.3, 10.9, 0.55, () => a.footstep(0.25));
  at(9.4, () => a.giggle(null, 0.3));
  // claws
  at(11.5, () => a.clawFire()); at(11.9, () => a.clawGrab()); at(11.95, () => a.zap(null));
  let stopHum; at(12.0, () => { stopHum = a.hum(); }); at(14.5, () => stopHum());
  at(14.2, () => a.clawFire()); at(14.55, () => a.clawGrab()); at(14.6, () => a.zap(null));
  at(14.8, () => a.rumble(null, 2.5, 0.5)); at(14.9, () => a.creak(null, 0.6)); at(15.3, () => a.creak(null, 0.4));
  // carousel
  a.musicBoxAt(17, 8, 0.55, 3);
  at(17.2, () => a.setDread(0.4));
  at(19.6, () => a.creak(null, 0.5));
  every(20, 25, 0.62, (t) => a.heartbeat(0.3 + (t - 20) * 0.08));
  at(21.3, () => a.clawGrab());
  for (const t of [21.55, 21.68, 21.8]) at(t, () => a.horseStep(null));
  at(21.9, () => { a.clawGrab(); a.stinger(1.0); });
  // fun house
  at(25.2, () => a.setDread(0.5));
  at(26.3, () => a.horn(null, 0.6)); at(29.6, () => a.horn(null, 0.75));
  every(25.4, 30.2, 0.7, () => a.horseStep(null));
  at(27.6, () => a.whisper());
  every(25.5, 31, 0.9, () => a.heartbeat(0.35));
  // tunnel window
  every(31, 33.5, 0.8, () => a.heartbeat(0.4));
  at(33.6, () => { a.stinger(1.0); a.giggle(null, 0.8); });
  at(34.2, () => a.clawGrab());
  // chase
  at(36, () => a.setDread(1));
  at(36.3, () => a.giggle(null, 0.8));
  every(36, 46, 0.36, () => a.thud(null, 0.75));
  every(36.1, 46, 0.32, () => a.footstep(0.45));
  every(36, 46, 0.42, () => a.heartbeat(0.8));
  at(39.1, () => a.stinger(0.8)); at(39.4, () => a.giggle(null, 1));
  at(41.6, () => a.clawFire()); at(42.0, () => { a.clank(null, 0.9); a.rumble(null, 1.2, 0.5); });
  at(43.5, () => a.giggle(null, 0.9));
  // ferris finale
  at(46, () => a.setDread(0.6));
  a.musicBoxAt(46, 7.4, 0.7, 5);
  at(48, () => { a.rumble(null, 5.5, 1); a.stinger(1); });
  every(48, 53, 0.5, () => a.heartbeat(0.7));
  at(52.5, () => a.scream(1));
  // jumpscare
  at(54.25, () => a.scream(1));
  // end card
  at(56, () => a.setDread(0.2));
  a.musicBoxAt(56.3, 5.5, 0.3, 7);
  at(58.8, () => a.stinger(0.4));

  const buf = await off.startRendering();
  await post('audio.wav', 'data:audio/wav;base64,' + toBase64(encodeWav(buf)));
  return buf.duration;
}

function encodeWav(buf) {
  const n = buf.length, ch = buf.numberOfChannels, sr = buf.sampleRate;
  const data = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const str = (o, s) => { for (let i = 0; i < s.length; i++) data.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); data.setUint32(4, 36 + n * ch * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
  data.setUint32(16, 16, true); data.setUint16(20, 1, true); data.setUint16(22, ch, true);
  data.setUint32(24, sr, true); data.setUint32(28, sr * ch * 2, true); data.setUint16(32, ch * 2, true);
  data.setUint16(34, 16, true); str(36, 'data'); data.setUint32(40, n * ch * 2, true);
  const chans = [...Array(ch)].map((_, i) => buf.getChannelData(i));
  let o = 44;
  for (let i = 0; i < n; i++) for (let c = 0; c < ch; c++) {
    const v = Math.max(-1, Math.min(1, chans[c][i]));
    data.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true); o += 2;
  }
  return new Uint8Array(data.buffer);
}

function toBase64(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
