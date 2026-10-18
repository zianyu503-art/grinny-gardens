import * as THREE from 'three';

function canvas(w, h = w) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

let seed = 1;
function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }

function grime(g, w, h, amount = 900, dark = 0.35) {
  for (let i = 0; i < amount; i++) {
    const r = rnd() * 40 + 4;
    g.fillStyle = `rgba(${rnd() < .5 ? '20,14,10' : '60,50,40'},${rnd() * dark * 0.25})`;
    g.beginPath(); g.arc(rnd() * w, rnd() * h, r, 0, Math.PI * 2); g.fill();
  }
}

function tex(c, repeat = [1, 1], srgb = true) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat);
  t.anisotropy = 4;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function asphalt() {
  seed = 11;
  const [c, g] = canvas(512);
  g.fillStyle = '#26241f'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) {
    const v = 20 + rnd() * 40;
    g.fillStyle = `rgb(${v},${v - 2},${v - 6})`;
    g.fillRect(rnd() * 512, rnd() * 512, 2, 2);
  }
  grime(g, 512, 512, 300, 1.2);
  g.strokeStyle = 'rgba(8,6,4,.85)'; g.lineWidth = 1.5;
  for (let k = 0; k < 14; k++) {
    let x = rnd() * 512, y = rnd() * 512;
    g.beginPath(); g.moveTo(x, y);
    for (let s = 0; s < 12; s++) { x += (rnd() - .5) * 50; y += (rnd() - .5) * 50; g.lineTo(x, y); }
    g.stroke();
  }
  return tex(c, [40, 40]);
}

export function wallpaper() {
  seed = 21;
  const [c, g] = canvas(512);
  for (let x = 0; x < 512; x += 64) {
    g.fillStyle = '#3a1f3a'; g.fillRect(x, 0, 32, 512);
    g.fillStyle = '#5a3a4a'; g.fillRect(x + 32, 0, 32, 512);
  }
  // little faded clown faces in the pattern
  g.globalAlpha = .25;
  for (let y = 40; y < 512; y += 128) for (let x = 16; x < 512; x += 128) {
    g.fillStyle = '#d8c8b0'; g.beginPath(); g.arc(x + 16, y, 14, 0, 7); g.fill();
    g.fillStyle = '#7a1010'; g.beginPath(); g.arc(x + 16, y + 2, 4, 0, 7); g.fill();
    g.strokeStyle = '#100808'; g.beginPath(); g.arc(x + 16, y + 2, 9, 0.2, Math.PI - 0.2); g.stroke();
  }
  g.globalAlpha = 1;
  grime(g, 512, 512, 500, 1.5);
  // water stains running down
  for (let i = 0; i < 12; i++) {
    const x = rnd() * 512, h = 100 + rnd() * 300;
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, 'rgba(30,20,10,.5)'); gr.addColorStop(1, 'rgba(30,20,10,0)');
    g.fillStyle = gr; g.fillRect(x, 0, 6 + rnd() * 14, h);
  }
  return tex(c, [2, 1]);
}

export function checker() {
  seed = 31;
  const [c, g] = canvas(512);
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
    g.fillStyle = (x + y) % 2 ? '#1a1414' : '#a89c88';
    g.fillRect(x * 64, y * 64, 64, 64);
  }
  grime(g, 512, 512, 700, 2);
  return tex(c, [1, 1]);
}

export function concrete(tint = '#4a4844') {
  seed = 41;
  const [c, g] = canvas(512);
  g.fillStyle = tint; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 12000; i++) {
    const v = rnd() * 30 - 15;
    g.fillStyle = `rgba(${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${Math.abs(v) / 200})`;
    g.fillRect(rnd() * 512, rnd() * 512, 3, 3);
  }
  grime(g, 512, 512, 600, 1.8);
  g.fillStyle = 'rgba(0,0,0,.35)';
  for (let y = 0; y < 512; y += 128) g.fillRect(0, y, 512, 2);
  return tex(c, [1, 1]);
}

export function tiles() {
  seed = 51;
  const [c, g] = canvas(512);
  g.fillStyle = '#20201c'; g.fillRect(0, 0, 512, 512);
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
    const v = 140 + rnd() * 30;
    g.fillStyle = `rgb(${v},${v + 5},${v - 10})`;
    if (rnd() > 0.06) g.fillRect(x * 32 + 1, y * 32 + 1, 30, 30);
  }
  grime(g, 512, 512, 900, 2.5);
  return tex(c, [1, 1]);
}

/** Child's crayon drawing. kind: 0 bear, 1 family, 2 carousel, 3 text */
export function drawing(kind, words) {
  seed = 61 + kind * 7;
  const [c, g] = canvas(256, 192);
  g.fillStyle = '#e8e0cc'; g.fillRect(0, 0, 256, 192);
  grime(g, 256, 192, 40, 1);
  g.lineCap = 'round'; g.lineJoin = 'round';
  const crayon = (col, w = 4) => { g.strokeStyle = col; g.lineWidth = w; };
  const wob = (x, y) => [x + (rnd() - .5) * 3, y + (rnd() - .5) * 3];
  const scribble = (pts) => { g.beginPath(); g.moveTo(...wob(...pts[0])); for (const p of pts.slice(1)) g.lineTo(...wob(...p)); g.stroke(); };
  if (kind === 0 || kind === 1) {
    // a huge pink bear with a giant smile
    crayon('#c04a6a', 5);
    g.beginPath(); g.arc(150, 70, 40, 0, 7); g.stroke();
    g.beginPath(); g.arc(118, 36, 13, 0, 7); g.stroke();
    g.beginPath(); g.arc(182, 36, 13, 0, 7); g.stroke();
    scribble([[125, 105], [115, 180]]); scribble([[175, 105], [185, 180]]);
    scribble([[120, 120], [80, 150]]); scribble([[180, 120], [230, 110]]);
    crayon('#101010', 6);
    g.beginPath(); g.arc(135, 62, 4, 0, 7); g.stroke();
    g.beginPath(); g.arc(165, 62, 4, 0, 7); g.stroke();
    crayon('#a00000', 4);
    g.beginPath(); g.arc(150, 76, 26, 0.15, Math.PI - 0.15); g.stroke();
    for (let i = 0; i < 9; i++) scribble([[128 + i * 5.5, 92], [128 + i * 5.5, 100]]);
    // small stick children
    const n = kind === 1 ? 4 : 2;
    for (let i = 0; i < n; i++) {
      const x = 20 + i * 24, col = ['#3060c0', '#30a050', '#d0a020', '#a040a0'][i];
      crayon(col, 3);
      g.beginPath(); g.arc(x, 120, 8, 0, 7); g.stroke();
      scribble([[x, 128], [x, 158]]); scribble([[x, 158], [x - 7, 176]]); scribble([[x, 158], [x + 7, 176]]);
      scribble([[x - 10, 140], [x + 10, 140]]);
      if (kind === 1 && i === n - 1) { crayon('#101010', 5); scribble([[x - 9, 112], [x + 9, 130]]); scribble([[x + 9, 112], [x - 9, 130]]); }
    }
  } else if (kind === 2) {
    crayon('#c03030', 4);
    scribble([[40, 60], [128, 20], [216, 60], [40, 60]]);
    scribble([[50, 60], [50, 150]]); scribble([[206, 60], [206, 150]]); scribble([[40, 150], [216, 150]]);
    for (let i = 0; i < 4; i++) {
      crayon('#e8e0cc', 1);
      const x = 70 + i * 38;
      crayon('#606060', 3); scribble([[x, 60], [x, 150]]);
      crayon('#f0f0f0', 6); scribble([[x - 12, 110], [x + 12, 110], [x + 16, 98]]);
      crayon('#c00000', 3); g.beginPath(); g.arc(x + 14, 98, 2, 0, 7); g.stroke();
    }
  }
  if (words) {
    g.fillStyle = kind === 3 ? '#a00000' : '#202060';
    g.font = `${kind === 3 ? 30 : 20}px "Comic Sans MS", "PingFang TC", sans-serif`;
    g.textAlign = 'center';
    g.save(); g.translate(128, kind === 3 ? 100 : 180); g.rotate(-0.05);
    g.fillText(words, 0, 0); g.restore();
  }
  return tex(c, [1, 1]);
}

export function poster(title, sub, color = '#7a1414') {
  seed = 71 + title.length;
  const [c, g] = canvas(256, 384);
  g.fillStyle = color; g.fillRect(0, 0, 256, 384);
  g.fillStyle = '#d8c8a0'; g.fillRect(12, 12, 232, 360);
  g.fillStyle = color; g.fillRect(20, 20, 216, 344);
  g.fillStyle = '#e8d8b0'; g.textAlign = 'center';
  g.font = 'bold 34px "PingFang TC", sans-serif'; g.fillText(title, 128, 80);
  g.font = '18px "PingFang TC", sans-serif';
  sub.split('\n').forEach((l, i) => g.fillText(l, 128, 300 + i * 26));
  // grinning bear face
  g.fillStyle = '#c08088'; g.beginPath(); g.arc(128, 180, 62, 0, 7); g.fill();
  g.beginPath(); g.arc(80, 128, 22, 0, 7); g.fill(); g.beginPath(); g.arc(176, 128, 22, 0, 7); g.fill();
  g.fillStyle = '#111'; g.beginPath(); g.arc(106, 166, 9, 0, 7); g.fill(); g.beginPath(); g.arc(150, 166, 9, 0, 7); g.fill();
  g.strokeStyle = '#111'; g.lineWidth = 5; g.beginPath(); g.arc(128, 188, 34, 0.25, Math.PI - 0.25); g.stroke();
  grime(g, 256, 384, 120, 2.5);
  // torn corner
  g.fillStyle = '#000'; g.beginPath(); g.moveTo(256, 300); g.lineTo(256, 384); g.lineTo(170, 384); g.fill();
  return tex(c, [1, 1]);
}

export function sky() {
  seed = 81;
  const [c, g] = canvas(1024, 512);
  const gr = g.createLinearGradient(0, 0, 0, 512);
  gr.addColorStop(0, '#020205'); gr.addColorStop(0.55, '#0a0a14'); gr.addColorStop(1, '#16121a');
  g.fillStyle = gr; g.fillRect(0, 0, 1024, 512);
  for (let i = 0; i < 700; i++) {
    g.fillStyle = `rgba(220,220,240,${rnd() * 0.7})`;
    g.fillRect(rnd() * 1024, rnd() * 300, 1, 1);
  }
  g.fillStyle = 'rgba(40,36,44,.6)';
  for (let i = 0; i < 30; i++) { g.beginPath(); g.ellipse(rnd() * 1024, 160 + rnd() * 160, 80 + rnd() * 120, 14 + rnd() * 20, 0, 0, 7); g.fill(); }
  const t = tex(c, [1, 1]);
  t.mapping = THREE.EquirectangularReflectionMapping;
  return t;
}

export function noiseTexture() {
  seed = 91;
  const [c, g] = canvas(128);
  const d = g.createImageData(128, 128);
  for (let i = 0; i < d.data.length; i += 4) { const v = rnd() * 255; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  g.putImageData(d, 0, 0);
  return tex(c, [1, 1], false);
}
