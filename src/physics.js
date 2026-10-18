// 2D (XZ) collision against boxes/circles plus a navigation grid with A* for monsters.

export class Physics {
  constructor(bounds = { minX: -48, maxX: 48, minZ: -206, maxZ: 70 }, cell = 0.5) {
    this.colliders = [];
    this.bounds = bounds;
    this.cell = cell;
    this.w = Math.ceil((bounds.maxX - bounds.minX) / cell);
    this.h = Math.ceil((bounds.maxZ - bounds.minZ) / cell);
    this.grid = new Uint8Array(this.w * this.h);
    this.dirty = true;
  }

  box(minX, maxX, minZ, maxZ, tag = '') {
    const c = { type: 'box', minX, maxX, minZ, maxZ, enabled: true, tag };
    this.colliders.push(c);
    this.dirty = true;
    return c;
  }

  /** Box centred at (x, z) with full size (w, d) and rotation (radians, 0/90° steps fine). */
  boxAt(x, z, w, d, rot = 0, tag = '') {
    const sw = Math.abs(Math.cos(rot)) * w + Math.abs(Math.sin(rot)) * d;
    const sd = Math.abs(Math.sin(rot)) * w + Math.abs(Math.cos(rot)) * d;
    return this.box(x - sw / 2, x + sw / 2, z - sd / 2, z + sd / 2, tag);
  }

  circle(x, z, r, tag = '') {
    const c = { type: 'circle', x, z, r, enabled: true, tag };
    this.colliders.push(c);
    this.dirty = true;
    return c;
  }

  setEnabled(c, on) { if (c.enabled !== on) { c.enabled = on; this.dirty = true; } }

  /** Push a circle (x, z, r) out of every collider. Returns corrected {x, z}. */
  resolve(x, z, r) {
    for (let iter = 0; iter < 3; iter++) {
      for (const c of this.colliders) {
        if (!c.enabled) continue;
        if (c.type === 'box') {
          const cx = Math.max(c.minX, Math.min(x, c.maxX));
          const cz = Math.max(c.minZ, Math.min(z, c.maxZ));
          let dx = x - cx, dz = z - cz;
          const d2 = dx * dx + dz * dz;
          if (d2 < r * r) {
            if (d2 > 1e-8) {
              const d = Math.sqrt(d2);
              x = cx + (dx / d) * r; z = cz + (dz / d) * r;
            } else { // centre inside the box: push out along the shallowest axis
              const pl = x - c.minX, pr = c.maxX - x, pb = z - c.minZ, pf = c.maxZ - z;
              const m = Math.min(pl, pr, pb, pf);
              if (m === pl) x = c.minX - r; else if (m === pr) x = c.maxX + r;
              else if (m === pb) z = c.minZ - r; else z = c.maxZ + r;
            }
          }
        } else {
          const dx = x - c.x, dz = z - c.z;
          const d = Math.hypot(dx, dz), rr = r + c.r;
          if (d < rr && d > 1e-6) { x = c.x + (dx / d) * rr; z = c.z + (dz / d) * rr; }
        }
      }
    }
    return { x, z };
  }

  // ---------------------------------------------------------------- nav grid
  rebuild(margin = 0.35) {
    const { w, h, cell, bounds: b } = this;
    this.grid.fill(0);
    for (const c of this.colliders) {
      if (!c.enabled) continue;
      let minX, maxX, minZ, maxZ;
      if (c.type === 'box') { minX = c.minX - margin; maxX = c.maxX + margin; minZ = c.minZ - margin; maxZ = c.maxZ + margin; }
      else { minX = c.x - c.r - margin; maxX = c.x + c.r + margin; minZ = c.z - c.r - margin; maxZ = c.z + c.r + margin; }
      const i0 = Math.max(0, Math.floor((minX - b.minX) / cell)), i1 = Math.min(w - 1, Math.floor((maxX - b.minX) / cell));
      const j0 = Math.max(0, Math.floor((minZ - b.minZ) / cell)), j1 = Math.min(h - 1, Math.floor((maxZ - b.minZ) / cell));
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
        if (c.type === 'circle') {
          const x = b.minX + (i + 0.5) * cell, z = b.minZ + (j + 0.5) * cell;
          if (Math.hypot(x - c.x, z - c.z) > c.r + margin) continue;
        }
        this.grid[j * w + i] = 1;
      }
    }
    this.dirty = false;
  }

  cellOf(x, z) {
    return [Math.floor((x - this.bounds.minX) / this.cell), Math.floor((z - this.bounds.minZ) / this.cell)];
  }

  blocked(i, j) {
    if (i < 0 || j < 0 || i >= this.w || j >= this.h) return true;
    return this.grid[j * this.w + i] === 1;
  }

  center(i, j) {
    return { x: this.bounds.minX + (i + 0.5) * this.cell, z: this.bounds.minZ + (j + 0.5) * this.cell };
  }

  /** Is the straight line between two points free of walls (grid march)? */
  lineClear(x0, z0, x1, z1) {
    if (this.dirty) this.rebuild();
    const d = Math.hypot(x1 - x0, z1 - z0);
    const steps = Math.ceil(d / (this.cell * 0.5));
    for (let s = 1; s < steps; s++) {
      const t = s / steps;
      const [i, j] = this.cellOf(x0 + (x1 - x0) * t, z0 + (z1 - z0) * t);
      if (this.blocked(i, j)) return false;
    }
    return true;
  }

  nearestFree(i, j) {
    if (!this.blocked(i, j)) return [i, j];
    for (let r = 1; r < 8; r++) for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
      if (!this.blocked(i + di, j + dj)) return [i + di, j + dj];
    }
    return [i, j];
  }

  /** A* path from a to b. Returns array of {x,z} waypoints (smoothed) or null. */
  path(ax, az, bx, bz, maxNodes = 12000) {
    if (this.dirty) this.rebuild();
    if (this.lineClear(ax, az, bx, bz)) return [{ x: bx, z: bz }];
    const { w } = this;
    let [si, sj] = this.nearestFree(...this.cellOf(ax, az));
    let [ti, tj] = this.nearestFree(...this.cellOf(bx, bz));
    const start = sj * w + si, goal = tj * w + ti;
    const g = new Map([[start, 0]]);
    const came = new Map();
    const open = new Heap();
    const hfn = (i, j) => Math.hypot(i - ti, j - tj);
    open.push(start, hfn(si, sj));
    const closed = new Set();
    let n = 0;
    const DIRS = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.414], [1, -1, 1.414], [-1, 1, 1.414], [-1, -1, 1.414]];
    while (open.size && n++ < maxNodes) {
      const cur = open.pop();
      if (cur === goal) break;
      if (closed.has(cur)) continue;
      closed.add(cur);
      const ci = cur % w, cj = (cur / w) | 0;
      for (const [di, dj, cost] of DIRS) {
        const ni = ci + di, nj = cj + dj;
        if (this.blocked(ni, nj)) continue;
        if (di && dj && (this.blocked(ci + di, cj) || this.blocked(ci, cj + dj))) continue;
        const nk = nj * w + ni;
        const ng = g.get(cur) + cost;
        if (ng < (g.get(nk) ?? Infinity)) {
          g.set(nk, ng); came.set(nk, cur);
          open.push(nk, ng + hfn(ni, nj));
        }
      }
    }
    if (!came.has(goal)) return null;
    const cells = [];
    for (let k = goal; k !== start; k = came.get(k)) cells.push(k);
    cells.reverse();
    // string-pull smoothing
    const pts = cells.map((k) => this.center(k % w, (k / w) | 0));
    const out = [];
    let from = { x: ax, z: az };
    let i = 0;
    while (i < pts.length) {
      let j = pts.length - 1;
      while (j > i && !this.lineClear(from.x, from.z, pts[j].x, pts[j].z)) j--;
      out.push(pts[j]);
      from = pts[j];
      i = j + 1;
    }
    out[out.length - 1] = { x: bx, z: bz };
    return out;
  }
}

class Heap {
  constructor() { this.k = []; this.p = []; }
  get size() { return this.k.length; }
  push(key, pri) {
    const k = this.k, p = this.p;
    k.push(key); p.push(pri);
    let i = k.length - 1;
    while (i > 0) {
      const par = (i - 1) >> 1;
      if (p[par] <= p[i]) break;
      [k[par], k[i]] = [k[i], k[par]]; [p[par], p[i]] = [p[i], p[par]];
      i = par;
    }
  }
  pop() {
    const k = this.k, p = this.p;
    const top = k[0];
    const lk = k.pop(), lp = p.pop();
    if (k.length) {
      k[0] = lk; p[0] = lp;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < k.length && p[l] < p[m]) m = l;
        if (r < k.length && p[r] < p[m]) m = r;
        if (m === i) break;
        [k[m], k[i]] = [k[i], k[m]]; [p[m], p[i]] = [p[i], p[m]];
        i = m;
      }
    }
    return top;
  }
}
