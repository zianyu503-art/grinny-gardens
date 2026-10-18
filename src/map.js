// Hand-drawn park map, used both for in-world map boards and the paper map overlay (M).
import * as THREE from 'three';

const B = { minX: -46, maxX: 46, minZ: -202, maxZ: 68 };

export const MAP_LABELS = [
  ['售票亭', -6, 51], ['正門', 0, 40], ['旋轉木馬', 0, 20], ['碰碰車', -34, 22], ['馬戲團', 34, 21],
  ['咖啡杯', -15, 7], ['鬼屋', 0, -18], ['員工通道', 0, -53], ['雲霄飛車', 0, -102], ['吊橋', 0, -138], ['摩天輪', 0, -186],
];

/**
 * orient 'v': entrance at the bottom, ferris wheel at the top (paper map)
 * orient 'h': entrance on the left, ferris wheel on the right (wide map boards)
 */
export function drawParkMap(g, W, H, { orient = 'v', here = null, player = null, yaw = 0, marks = [], scribbles = true } = {}) {
  const pad = 0.06;
  const P = (x, z) => {
    const u = (B.maxZ - z) / (B.maxZ - B.minZ);       // 0 entrance .. 1 ferris
    const v = (x - B.minX) / (B.maxX - B.minX);       // 0 west .. 1 east
    return orient === 'v'
      ? [W * (pad + v * (1 - 2 * pad)), H * (1 - pad - u * (1 - 2 * pad))]
      : [W * (pad + u * (1 - 2 * pad)), H * (pad + v * (1 - 2 * pad))];
  };
  const S = orient === 'v' ? (W * (1 - 2 * pad)) / (B.maxX - B.minX) : (H * (1 - 2 * pad)) / (B.maxX - B.minX);
  const rect = (x0, z0, x1, z1) => {
    const [ax, ay] = P(x0, z0), [bx, by] = P(x1, z1);
    return [Math.min(ax, bx), Math.min(ay, by), Math.abs(bx - ax), Math.abs(by - ay)];
  };
  // paper
  g.fillStyle = '#cdbf9c'; g.fillRect(0, 0, W, H);
  let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  for (let i = 0; i < 260; i++) {
    g.fillStyle = `rgba(${rnd() < 0.5 ? '90,70,40' : '255,250,230'},${rnd() * 0.08})`;
    g.beginPath(); g.arc(rnd() * W, rnd() * H, rnd() * W * 0.05, 0, 7); g.fill();
  }
  g.strokeStyle = 'rgba(80,60,30,.35)'; g.lineWidth = 3; g.strokeRect(6, 6, W - 12, H - 12);
  const unit = Math.min(W, H) / 512;
  // grass / zones
  const zone = (x0, z0, x1, z1, fill, dash = false) => {
    g.fillStyle = fill; g.fillRect(...rect(x0, z0, x1, z1));
    g.setLineDash(dash ? [8 * unit, 6 * unit] : []);
    g.strokeStyle = '#4a3a24'; g.lineWidth = 2 * unit; g.strokeRect(...rect(x0, z0, x1, z1));
    g.setLineDash([]);
  };
  zone(-15, 40, 15, 66, 'rgba(120,140,90,.35)');
  zone(-44, 0, 44, 40, 'rgba(120,140,90,.35)');
  zone(-16, -36, 16, 0, 'rgba(110,60,110,.35)');
  zone(-12, -70, 12, -36, 'rgba(90,90,90,.3)', true);
  zone(-4, -134, 4, -70, 'rgba(140,110,70,.35)');
  zone(-25, -200, 25, -142, 'rgba(120,140,90,.35)');
  // the pit
  g.fillStyle = '#1a1410'; g.fillRect(...rect(-12, -134, 12, -142));
  g.fillStyle = '#8a6a40'; g.fillRect(...rect(-1.5, -134, 1.5, -142));
  // path
  g.strokeStyle = '#7a1414'; g.lineWidth = 3 * unit; g.setLineDash([10 * unit, 8 * unit]);
  g.beginPath(); g.moveTo(...P(0, 63)); g.lineTo(...P(0, -186)); g.stroke(); g.setLineDash([]);
  // attractions
  const circ = (x, z, r, fill) => { const [cx, cy] = P(x, z); g.fillStyle = fill; g.beginPath(); g.arc(cx, cy, r * S, 0, 7); g.fill(); g.stroke(); };
  g.strokeStyle = '#3a2a18'; g.lineWidth = 2 * unit;
  circ(0, 20, 6.4, '#b05050'); circ(34, 21, 9, '#c06040'); circ(-15, 7, 5, '#a07090'); circ(0, -186, 8, 'rgba(160,160,170,.6)');
  g.fillStyle = '#5a6a8a'; g.fillRect(...rect(-39, 15, -29, 29)); g.strokeRect(...rect(-39, 15, -29, 29));
  g.fillStyle = '#9a5a3a'; g.fillRect(...rect(-7.2, 52, -4.8, 50)); g.strokeRect(...rect(-7.2, 52, -4.8, 50));
  g.fillStyle = '#2a1a10';
  g.font = `bold ${Math.round(17 * unit)}px "PingFang TC", "Noto Sans TC", sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
  for (const [t, x, z] of MAP_LABELS) {
    const [cx, cy] = P(x, z);
    g.fillStyle = 'rgba(205,191,156,.75)';
    const w = g.measureText(t).width + 8 * unit;
    g.fillRect(cx - w / 2, cy - 11 * unit, w, 22 * unit);
    g.fillStyle = '#2a1a10'; g.fillText(t, cx, cy);
  }
  g.font = `bold ${Math.round(24 * unit)}px "PingFang TC", sans-serif`;
  g.fillStyle = '#7a1414';
  const [tx, ty] = orient === 'v' ? [W / 2, H * 0.025 + 14 * unit] : [W * 0.2, H * 0.08];
  g.fillText('微笑樂園　導覽圖', tx, ty);
  // scribbles left by someone who was here before
  if (scribbles) {
    g.save();
    g.strokeStyle = 'rgba(150,10,10,.85)'; g.fillStyle = 'rgba(150,10,10,.9)'; g.lineWidth = 4 * unit;
    const [fx, fy] = P(0, -18);
    g.beginPath(); g.ellipse(fx, fy, 22 * S, 10 * S, 0, 0, 7); g.stroke();
    g.font = `${Math.round(18 * unit)}px "Comic Sans MS", "PingFang TC", sans-serif`;
    g.fillText('不要出聲！', fx + 30 * unit, fy + 26 * unit);
    const [wx, wy] = P(0, -186);
    g.beginPath(); g.moveTo(wx - 14 * unit, wy - 14 * unit); g.lineTo(wx + 14 * unit, wy + 14 * unit);
    g.moveTo(wx + 14 * unit, wy - 14 * unit); g.lineTo(wx - 14 * unit, wy + 14 * unit); g.stroke();
    g.fillText('他們都在這裡', wx, wy + 34 * unit);
    const [cx, cy] = P(0, 20);
    g.fillText('照著牠們', cx + 40 * unit, cy - 20 * unit);
    g.restore();
  }
  // objective marks
  const t = performance.now() / 300;
  for (const m of marks) {
    const [mx, my] = P(m.x, m.z);
    g.strokeStyle = '#c01010'; g.lineWidth = 3 * unit;
    g.beginPath(); g.arc(mx, my, (9 + Math.sin(t) * 2) * unit, 0, 7); g.stroke();
  }
  const pin = (x, z, label) => {
    const [px, py] = P(x, z);
    g.fillStyle = '#c01010'; g.beginPath(); g.arc(px, py, 8 * unit, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.beginPath(); g.arc(px, py, 3 * unit, 0, 7); g.fill();
    g.fillStyle = '#c01010'; g.font = `bold ${Math.round(16 * unit)}px "PingFang TC", sans-serif`;
    g.fillText(label, px, py - 18 * unit);
  };
  if (here) pin(here.x, here.z, '你在這裡');
  if (player) {
    const [px, py] = P(player.x, player.z);
    // arrow: forward is -Z in world; on the vertical map that is "up"
    const ang = orient === 'v' ? -yaw : -yaw - Math.PI / 2;
    g.save(); g.translate(px, py); g.rotate(ang);
    g.fillStyle = '#c01010';
    g.beginPath(); g.moveTo(0, -14 * unit); g.lineTo(9 * unit, 10 * unit); g.lineTo(0, 5 * unit); g.lineTo(-9 * unit, 10 * unit); g.fill();
    g.restore();
  }
}

export function mapTexture(opts) {
  const c = document.createElement('canvas');
  c.width = 1024; c.height = 640;
  drawParkMap(c.getContext('2d'), c.width, c.height, { orient: 'h', ...opts });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
