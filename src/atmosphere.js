// Environmental dressing: ground fog, dust, graffiti, stains, puddles, litter, polaroids.
import * as THREE from 'three';

let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;

function canvas(w, h = w) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

function tex(c, srgb = true) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function fogTexture() {
  const [c, g] = canvas(128);
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return tex(c, false);
}

/** Low drifting fog banks. Returns an update(dt) function. */
export function groundFog(scene, areas) {
  const mat = new THREE.SpriteMaterial({ map: fogTexture(), color: 0x8a8c96, transparent: true, opacity: 0.09, depthWrite: false });
  const sprites = [];
  for (const [x0, z0, x1, z1, n] of areas) {
    for (let i = 0; i < n; i++) {
      const s = new THREE.Sprite(mat);
      const size = 5 + rnd() * 6;
      s.scale.set(size, size * 0.45, 1);
      s.position.set(x0 + rnd() * (x1 - x0), 0.4 + rnd() * 0.7, z0 + rnd() * (z1 - z0));
      s.userData.v = (rnd() - 0.5) * 0.4;
      s.userData.range = [x0, x1];
      scene.add(s);
      sprites.push(s);
    }
  }
  return (dt) => {
    for (const s of sprites) {
      s.position.x += s.userData.v * dt;
      const [a, b] = s.userData.range;
      if (s.position.x < a) s.position.x = b; else if (s.position.x > b) s.position.x = a;
    }
  };
}

/** Dust motes that follow the player. */
export function dust(scene) {
  const N = 400, R = 9;
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { pos[i * 3] = (rnd() - 0.5) * 2 * R; pos[i * 3 + 1] = rnd() * 3.5; pos[i * 3 + 2] = (rnd() - 0.5) * 2 * R; }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xd8d0c0, size: 0.025, transparent: true, opacity: 0.55, depthWrite: false }));
  pts.frustumCulled = false;
  scene.add(pts);
  return (dt, center) => {
    const a = geo.attributes.position.array;
    for (let i = 0; i < N; i++) {
      a[i * 3] += Math.sin(i + performance.now() / 3000) * dt * 0.05;
      a[i * 3 + 1] -= dt * 0.03;
      if (a[i * 3 + 1] < 0) a[i * 3 + 1] = 3.5;
    }
    geo.attributes.position.needsUpdate = true;
    pts.position.set(Math.round(center.x / 2) * 2, 0, Math.round(center.z / 2) * 2);
  };
}

// ------------------------------------------------------------------ decals
export function graffiti(text, color = '#7a0a0a', w = 512, h = 256) {
  const [c, g] = canvas(w, h);
  g.font = `bold ${Math.round(h * 0.42)}px "Comic Sans MS", "PingFang TC", sans-serif`;
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.save(); g.translate(w / 2, h / 2); g.rotate((rnd() - 0.5) * 0.15);
  // spray: draw many jittered copies
  g.globalAlpha = 0.12;
  g.fillStyle = color;
  for (let i = 0; i < 18; i++) g.fillText(text, (rnd() - 0.5) * 6, (rnd() - 0.5) * 6);
  g.globalAlpha = 0.9;
  g.fillText(text, 0, 0);
  g.restore();
  // drips
  g.fillStyle = color;
  for (let i = 0; i < 14; i++) {
    const x = w * 0.1 + rnd() * w * 0.8, y = h * 0.55 + rnd() * h * 0.1;
    g.fillRect(x, y, 2 + rnd() * 3, rnd() * h * 0.4);
  }
  return tex(c);
}

export function handprints() {
  const [c, g] = canvas(256);
  g.fillStyle = 'rgba(70,6,6,.85)';
  for (let k = 0; k < 4; k++) {
    const x = 40 + rnd() * 170, y = 40 + rnd() * 170, s = 0.6 + rnd() * 0.3, r = (rnd() - 0.5);
    g.save(); g.translate(x, y); g.rotate(r); g.scale(s, s);
    g.beginPath(); g.ellipse(0, 0, 22, 26, 0, 0, 7); g.fill();
    for (let f = 0; f < 4; f++) { g.beginPath(); g.ellipse(-18 + f * 12, -38, 5, 14, 0, 0, 7); g.fill(); }
    g.beginPath(); g.ellipse(26, -4, 6, 13, 0.8, 0, 7); g.fill();
    g.restore();
  }
  return tex(c);
}

export function dragMarks() {
  const [c, g] = canvas(128, 512);
  for (let k = 0; k < 3; k++) {
    const x = 30 + k * 30 + rnd() * 10;
    const gr = g.createLinearGradient(0, 0, 0, 512);
    gr.addColorStop(0, 'rgba(50,6,4,.0)'); gr.addColorStop(0.2, 'rgba(50,6,4,.75)'); gr.addColorStop(1, 'rgba(50,6,4,.1)');
    g.strokeStyle = gr; g.lineWidth = 6 + rnd() * 6; g.lineCap = 'round';
    g.beginPath(); g.moveTo(x, 0);
    for (let y = 0; y < 512; y += 32) g.lineTo(x + (rnd() - 0.5) * 10, y);
    g.stroke();
  }
  return tex(c);
}

export function puddleMap() {
  const [c, g] = canvas(256);
  g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256);
  g.fillStyle = '#fff';
  for (let i = 0; i < 9; i++) { g.beginPath(); g.ellipse(128 + (rnd() - 0.5) * 120, 128 + (rnd() - 0.5) * 120, 30 + rnd() * 50, 20 + rnd() * 40, rnd() * 3, 0, 7); g.fill(); }
  return tex(c, false);
}

const KIDS = ['小雨', '阿哲', '美美', '小凱', '婷婷', '阿翔', '小安', '佳佳'];
export const PHOTO_COUNT = KIDS.length;

/** A faded polaroid of one of the missing children (with something behind them). */
export function polaroid(i) {
  seed = 100 + i * 13;
  const [c, g] = canvas(256, 310);
  g.fillStyle = '#e4ddcc'; g.fillRect(0, 0, 256, 310);
  const gr = g.createLinearGradient(0, 16, 0, 240);
  gr.addColorStop(0, '#3a3020'); gr.addColorStop(1, '#14100c');
  g.fillStyle = gr; g.fillRect(16, 16, 224, 224);
  // something huge and pink behind the child, cut off by the frame
  g.fillStyle = 'rgba(150,80,95,.75)';
  g.beginPath(); g.arc(70 + rnd() * 110, 50, 70, 0, 7); g.fill();
  g.fillStyle = '#100808'; g.beginPath(); g.arc(110, 40, 6, 0, 7); g.fill();
  g.strokeStyle = '#100808'; g.lineWidth = 4; g.beginPath(); g.arc(130, 62, 30, 0.2, Math.PI - 0.2); g.stroke();
  // child silhouette, smiling, waving
  g.fillStyle = 'rgba(220,200,170,.85)';
  const x = 90 + rnd() * 70;
  g.beginPath(); g.arc(x, 140, 22, 0, 7); g.fill();
  g.fillRect(x - 20, 162, 40, 70);
  g.fillRect(x + 18, 160, 30, 10);
  g.fillStyle = '#201410'; g.beginPath(); g.arc(x, 146, 9, 0.1, Math.PI - 0.1); g.fill();
  // grain and fading
  for (let k = 0; k < 2500; k++) { g.fillStyle = `rgba(255,240,220,${rnd() * 0.08})`; g.fillRect(16 + rnd() * 224, 16 + rnd() * 224, 2, 2); }
  g.fillStyle = 'rgba(255,220,180,.12)'; g.fillRect(16, 16, 224, 224);
  g.fillStyle = '#2a2018'; g.font = '26px "Comic Sans MS", "PingFang TC", sans-serif'; g.textAlign = 'center';
  g.fillText(`${KIDS[i]}  1996.8.31`, 128, 280);
  return tex(c);
}

export function kidName(i) { return KIDS[i]; }
