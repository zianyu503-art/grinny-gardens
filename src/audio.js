// Procedural Web Audio: every sound in the game is synthesised here.
import * as THREE from 'three';

export class Audio {
  constructor() {
    this.ctx = null;
    this.volume = 0.8;
  }

  init() {
    if (this.ctx) return;
    const ctx = (this.ctx = new (window.AudioContext || window.webkitAudioContext)());
    this.master = ctx.createGain();
    this.master.gain.value = this.volume;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14; comp.ratio.value = 4;
    this.master.connect(comp).connect(ctx.destination);
    this.sfx = ctx.createGain(); this.sfx.connect(this.master);
    this.amb = ctx.createGain(); this.amb.gain.value = 0.9; this.amb.connect(this.master);

    // white noise buffer shared by everything
    const len = ctx.sampleRate * 2;
    this.noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    // distortion curve
    this.curve = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) { const x = i / 512 - 1; this.curve[i] = Math.tanh(x * 6); }
    this.startAmbience();
    this.heart = { next: 0, rate: 0, level: 0 };
  }

  setVolume(v) { this.volume = v; if (this.master) this.master.gain.value = v; }
  get t() { return this.ctx.currentTime; }

  noise(dur) {
    const s = this.ctx.createBufferSource();
    s.buffer = this.noiseBuf; s.loop = true;
    s.start(this.t, Math.random() * 1.5, dur + 0.1);
    return s;
  }

  env(node, attack, peak, decay, start = this.t) {
    peak = Math.max(peak, 0.0002);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, start);
    g.gain.exponentialRampToValueAtTime(peak, start + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, start + attack + decay);
    node.connect(g);
    return g;
  }

  /** 3D panner at a world position (returns node to connect sources into). */
  panner(pos, ref = 3, rolloff = 1.2) {
    const p = this.ctx.createPanner();
    p.panningModel = 'HRTF';
    p.distanceModel = 'inverse';
    p.refDistance = ref; p.rolloffFactor = rolloff; p.maxDistance = 80;
    p.positionX.value = pos.x; p.positionY.value = pos.y; p.positionZ.value = pos.z;
    p.connect(this.sfx);
    return p;
  }

  out(pos) { return pos ? this.panner(pos) : this.sfx; }

  updateListener(camera) {
    if (!this.ctx) return;
    const l = this.ctx.listener;
    const p = camera.getWorldPosition(new THREE.Vector3());
    const f = camera.getWorldDirection(new THREE.Vector3());
    const t = this.t;
    if (l.positionX) {
      l.positionX.setTargetAtTime(p.x, t, 0.02); l.positionY.setTargetAtTime(p.y, t, 0.02); l.positionZ.setTargetAtTime(p.z, t, 0.02);
      l.forwardX.setTargetAtTime(f.x, t, 0.02); l.forwardY.setTargetAtTime(f.y, t, 0.02); l.forwardZ.setTargetAtTime(f.z, t, 0.02);
      l.upX.value = 0; l.upY.value = 1; l.upZ.value = 0;
    } else {
      l.setPosition(p.x, p.y, p.z); l.setOrientation(f.x, f.y, f.z, 0, 1, 0);
    }
  }

  // ---------------------------------------------------------------- ambience
  startAmbience() {
    const ctx = this.ctx;
    // wind
    const wind = this.ctx.createBufferSource(); wind.buffer = this.noiseBuf; wind.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 380; lp.Q.value = 0.7;
    const wg = ctx.createGain(); wg.gain.value = 0.12;
    const lfo = ctx.createOscillator(); lfo.frequency.value = 0.07;
    const lfoG = ctx.createGain(); lfoG.gain.value = 0.07; lfo.connect(lfoG).connect(wg.gain);
    const lfo2 = ctx.createOscillator(); lfo2.frequency.value = 0.13;
    const lfo2G = ctx.createGain(); lfo2G.gain.value = 200; lfo2.connect(lfo2G).connect(lp.frequency);
    wind.connect(lp).connect(wg).connect(this.amb);
    wind.start(); lfo.start(); lfo2.start();
    // dread drone
    this.drone = ctx.createGain(); this.drone.gain.value = 0.05;
    const dlp = ctx.createBiquadFilter(); dlp.type = 'lowpass'; dlp.frequency.value = 160;
    for (const f of [41.2, 43.6, 61.7]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f;
      o.connect(dlp); o.start();
    }
    dlp.connect(this.drone).connect(this.amb);
    this.windGain = wg;
    this._nextWhisper = this.t + 20;
  }

  setDread(level) {
    if (!this.ctx) return;
    this.drone.gain.setTargetAtTime(0.04 + level * 0.12, this.t, 0.8);
  }

  setIndoor(indoor) {
    if (!this.ctx) return;
    this.windGain.gain.setTargetAtTime(indoor ? 0.02 : 0.12, this.t, 1.0);
  }

  update(dt, danger) {
    if (!this.ctx) return;
    // heartbeat speeds up with danger (0..1)
    const h = this.heart;
    h.level += (danger - h.level) * Math.min(1, dt * 2);
    if (h.level > 0.08 && this.t > h.next) {
      const bpm = 60 + h.level * 110;
      this.heartbeat(0.25 + h.level * 0.75);
      h.next = this.t + 60 / bpm;
    }
    if (this.t > this._nextWhisper) {
      this.whisper();
      this._nextWhisper = this.t + 25 + Math.random() * 40;
    }
  }

  // ---------------------------------------------------------------- one-shots
  heartbeat(vol) {
    const ctx = this.ctx;
    for (const [dt, v] of [[0, 1], [0.16, 0.7]]) {
      const o = ctx.createOscillator(); o.frequency.setValueAtTime(58, this.t + dt);
      o.frequency.exponentialRampToValueAtTime(32, this.t + dt + 0.15);
      this.env(o, 0.01, 0.9 * vol * v, 0.18, this.t + dt).connect(this.sfx);
      o.start(this.t + dt); o.stop(this.t + dt + 0.3);
    }
  }

  footstep(vol = 0.3, surface = 'ground') {
    const ctx = this.ctx;
    const n = this.noise(0.15);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass';
    bp.frequency.value = surface === 'wood' ? 380 : surface === 'metal' ? 1400 : 700 + Math.random() * 300;
    bp.Q.value = surface === 'metal' ? 6 : 1.2;
    n.connect(bp);
    this.env(bp, 0.005, vol, 0.11).connect(this.sfx);
  }

  clank(pos, vol = 0.8) {
    const ctx = this.ctx; const out = this.out(pos);
    for (const f of [523, 1187, 1873, 2711]) {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f * (0.97 + Math.random() * 0.06);
      this.env(o, 0.002, vol / 4, 0.5 + Math.random() * 0.4).connect(out);
      o.start(); o.stop(this.t + 1.2);
    }
    const n = this.noise(0.05); const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 2000;
    n.connect(hp); this.env(hp, 0.001, vol * 0.6, 0.05).connect(out);
  }

  clawFire() {
    const ctx = this.ctx;
    const n = this.noise(0.3);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 3;
    bp.frequency.setValueAtTime(400, this.t); bp.frequency.exponentialRampToValueAtTime(3000, this.t + 0.25);
    n.connect(bp); this.env(bp, 0.01, 0.35, 0.25).connect(this.sfx);
    const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = 90;
    this.env(o, 0.001, 0.15, 0.05).connect(this.sfx); o.start(); o.stop(this.t + 0.1);
  }

  clawGrab() {
    const o = this.ctx.createOscillator(); o.type = 'triangle';
    o.frequency.setValueAtTime(900, this.t); o.frequency.exponentialRampToValueAtTime(200, this.t + 0.08);
    this.env(o, 0.001, 0.4, 0.1).connect(this.sfx); o.start(); o.stop(this.t + 0.2);
  }

  zap(pos) {
    const ctx = this.ctx; const out = this.out(pos);
    const o = ctx.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(120, this.t); o.frequency.exponentialRampToValueAtTime(1800, this.t + 0.4);
    const ws = ctx.createWaveShaper(); ws.curve = this.curve;
    o.connect(ws); this.env(ws, 0.01, 0.25, 0.5).connect(out); o.start(); o.stop(this.t + 0.6);
    const n = this.noise(0.4); const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 3000;
    n.connect(hp); this.env(hp, 0.005, 0.25, 0.35).connect(out);
  }

  hum() { // charged hand buzz; returns stop()
    const ctx = this.ctx;
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 60;
    const o2 = ctx.createOscillator(); o2.type = 'square'; o2.frequency.value = 120.5;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 600;
    const g = ctx.createGain(); g.gain.value = 0.05;
    o.connect(lp); o2.connect(lp); lp.connect(g).connect(this.sfx); o.start(); o2.start();
    return () => { g.gain.setTargetAtTime(0, this.t, 0.05); o.stop(this.t + 0.3); o2.stop(this.t + 0.3); };
  }

  pickup() {
    const ctx = this.ctx;
    [660, 990].forEach((f, i) => {
      const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f;
      this.env(o, 0.005, 0.18, 0.25, this.t + i * 0.07).connect(this.sfx); o.start(this.t + i * 0.07); o.stop(this.t + 0.5);
    });
  }

  rumble(pos, dur = 1.5, vol = 0.6) {
    const ctx = this.ctx; const out = this.out(pos);
    const n = this.noise(dur); const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 140;
    n.connect(lp);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, this.t);
    g.gain.exponentialRampToValueAtTime(vol, this.t + 0.2); g.gain.setValueAtTime(vol, this.t + dur - 0.3);
    g.gain.exponentialRampToValueAtTime(0.0001, this.t + dur);
    lp.connect(g).connect(out);
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 38;
    const og = this.env(o, 0.1, vol * 0.3, dur); og.connect(out); o.start(); o.stop(this.t + dur + 0.2);
  }

  creak(pos, vol = 0.5) {
    const ctx = this.ctx; const out = this.out(pos);
    const o = ctx.createOscillator(); o.type = 'sawtooth';
    const base = 90 + Math.random() * 60;
    o.frequency.setValueAtTime(base, this.t);
    o.frequency.linearRampToValueAtTime(base * 1.6, this.t + 0.6);
    const fm = ctx.createOscillator(); fm.frequency.value = 23; const fmG = ctx.createGain(); fmG.gain.value = 40;
    fm.connect(fmG).connect(o.frequency);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 900; bp.Q.value = 4;
    o.connect(bp); this.env(bp, 0.08, vol, 0.7).connect(out);
    o.start(); fm.start(); o.stop(this.t + 1); fm.stop(this.t + 1);
  }

  horseStep(pos) { // hollow wooden clop
    const ctx = this.ctx; const out = this.out(pos);
    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(320, this.t); o.frequency.exponentialRampToValueAtTime(140, this.t + 0.06);
    this.env(o, 0.001, 0.5, 0.09).connect(out); o.start(); o.stop(this.t + 0.2);
  }

  horn(pos, vol = 0.6) { // Hornman's breathing honk
    const ctx = this.ctx; const out = this.out(pos);
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 72 + Math.random() * 10;
    const vib = ctx.createOscillator(); vib.frequency.value = 5.5; const vg = ctx.createGain(); vg.gain.value = 4;
    vib.connect(vg).connect(o.frequency);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 420; bp.Q.value = 2.5;
    const ws = ctx.createWaveShaper(); ws.curve = this.curve;
    o.connect(ws).connect(bp);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, this.t);
    g.gain.exponentialRampToValueAtTime(vol, this.t + 0.4); g.gain.exponentialRampToValueAtTime(0.0001, this.t + 1.8);
    bp.connect(g).connect(out); o.start(); vib.start(); o.stop(this.t + 2); vib.stop(this.t + 2);
  }

  thud(pos, vol = 0.8) { // Grinny's heavy footfall
    const ctx = this.ctx; const out = this.out(pos);
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(70, this.t); o.frequency.exponentialRampToValueAtTime(30, this.t + 0.2);
    this.env(o, 0.005, vol, 0.25).connect(out); o.start(); o.stop(this.t + 0.4);
    const n = this.noise(0.1); const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 300;
    n.connect(lp); this.env(lp, 0.002, vol * 0.5, 0.1).connect(out);
  }

  giggle(pos, vol = 0.5) {
    const ctx = this.ctx; const out = this.out(pos);
    const n = 4 + Math.floor(Math.random() * 3);
    const base = 260 + Math.random() * 80;
    for (let i = 0; i < n; i++) {
      const st = this.t + i * 0.13;
      const o = ctx.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(base * (1.15 - i * 0.04), st);
      o.frequency.exponentialRampToValueAtTime(base * 0.8, st + 0.1);
      const f1 = ctx.createBiquadFilter(); f1.type = 'bandpass'; f1.frequency.value = 800; f1.Q.value = 5;
      const f2 = ctx.createBiquadFilter(); f2.type = 'bandpass'; f2.frequency.value = 1300; f2.Q.value = 6;
      o.connect(f1); o.connect(f2);
      const g = this.env(f1, 0.01, vol, 0.09, st); f2.connect(g); g.connect(out);
      o.start(st); o.stop(st + 0.15);
    }
  }

  scream(vol = 1.0) { // jumpscare
    const ctx = this.ctx;
    const ws = ctx.createWaveShaper(); ws.curve = this.curve;
    const g = ctx.createGain(); g.gain.setValueAtTime(vol, this.t); g.gain.exponentialRampToValueAtTime(0.0001, this.t + 1.6);
    ws.connect(g).connect(this.sfx);
    for (const f of [311, 330, 467, 622, 740]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(f * 0.6, this.t); o.frequency.exponentialRampToValueAtTime(f * 1.4, this.t + 0.3);
      o.frequency.exponentialRampToValueAtTime(f * 0.5, this.t + 1.5);
      const og = ctx.createGain(); og.gain.value = 0.12; o.connect(og).connect(ws); o.start(); o.stop(this.t + 1.6);
    }
    const n = this.noise(1.5); const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 900;
    n.connect(hp); const ng = ctx.createGain(); ng.gain.value = 0.5; hp.connect(ng).connect(ws);
  }

  stinger(vol = 0.6) { // sudden dissonant orchestral hit
    const ctx = this.ctx;
    for (const f of [55, 58.3, 82.4, 116.5, 233, 246.9]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.setValueAtTime(4000, this.t);
      lp.frequency.exponentialRampToValueAtTime(200, this.t + 2.5);
      o.connect(lp); this.env(lp, 0.01, vol / 5, 2.5).connect(this.sfx); o.start(); o.stop(this.t + 2.8);
    }
  }

  whisper() {
    const ctx = this.ctx;
    const pan = ctx.createStereoPanner(); pan.pan.value = Math.random() * 2 - 1; pan.connect(this.sfx);
    for (let i = 0; i < 5; i++) {
      const st = this.t + i * (0.12 + Math.random() * 0.15);
      const n = this.noise(0.3);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2500 + Math.random() * 2500; bp.Q.value = 4;
      n.connect(bp); this.env(bp, 0.04, 0.06, 0.15, st).connect(pan);
    }
  }

  doorCreak(pos) { this.creak(pos, 0.6); setTimeout(() => this.ctx && this.creak(pos, 0.4), 350); }

  // ---------------------------------------------------------------- music box
  /** Broken lullaby at a position; returns {stop, setVolume}. */
  musicBox(pos, vol = 0.5) {
    const ctx = this.ctx;
    const out = pos ? this.panner(pos, 4, 1) : this.sfx;
    const g = ctx.createGain(); g.gain.value = vol; g.connect(out);
    // twisted lullaby in a minor key (semitones from A4)
    const melody = [7, 5, 3, 5, 7, 7, 7, null, 5, 5, 5, null, 7, 10, 10, null, 7, 5, 3, 5, 7, 7, 7, 7, 5, 5, 7, 5, 3, null, null, null];
    let i = 0; let alive = true; let detune = 0;
    const tick = () => {
      if (!alive) return;
      const n = melody[i % melody.length]; i++;
      detune += (Math.random() - 0.5) * 6;
      detune = Math.max(-60, Math.min(60, detune));
      if (n !== null && Math.random() > 0.06) {
        const f = 440 * Math.pow(2, n / 12) * 2;
        for (const [mult, amp] of [[1, 0.5], [2.01, 0.15], [4.2, 0.06]]) {
          const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f * mult; o.detune.value = detune;
          this.env(o, 0.003, amp, 1.4).connect(g); o.start(); o.stop(this.t + 1.5);
        }
      }
      setTimeout(tick, 330 + Math.random() * 60 + (i % 32 === 0 ? 800 : 0));
    };
    tick();
    return { stop: () => { alive = false; g.gain.setTargetAtTime(0, this.t, 0.3); }, gain: g };
  }

  // ---------------------------------------------------------------- voice
  speak(text, { pitch = 0.6, rate = 0.85, volume = 1 } = {}) {
    if (!('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    const v = voices.find((x) => /zh[-_]TW/i.test(x.lang)) || voices.find((x) => /zh/i.test(x.lang));
    if (v) u.voice = v;
    u.lang = v ? v.lang : 'zh-TW';
    u.pitch = pitch; u.rate = rate; u.volume = volume * this.volume;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }
}

export const audio = new Audio();
