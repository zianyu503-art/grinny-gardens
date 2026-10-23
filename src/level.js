import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { spawn, setEmit } from './assets.js';
import * as T from './textures.js';
import * as A from './atmosphere.js';
import { mapTexture } from './map.js';
import { buildPark, placeInteriorPoints } from './park.js';

// Layout (metres). The player walks from +Z toward -Z through six zones.
export const ZONES = {
  entrance: { z0: 66, z1: 40 },
  carousel: { z0: 40, z1: 0 },
  funhouse: { z0: 0, z1: -36 },
  tunnel: { z0: -36, z1: -70 },
  coaster: { z0: -70, z1: -144 },
  ferris: { z0: -144, z1: -200 },
};

export const FUN_MAP = [
  '#######..#######',
  '#a.............#',
  '#.####.##.####.#',
  '#.#B.#.#..#..#.#',
  '#.#..#.#.J#..#b#',
  '#.##.#.##.##.#.#',
  '#......#.......#',
  '####.#####.#####',
  '#c...#...#...d.#',
  '#.##.#.#.#.###.#',
  '#.#....#...#...#',
  '#.#.####.#.#.#.#',
  '#...#T...#...#.#',
  '###.#.#####.##.#',
  '#e..#.#K..#....#',
  '#.###.#.###.##f#',
  '#.....#........#',
  '#######XX#######',
];
export const TUN_MAP = [
  '#####..#####',
  '#####..#####',
  '##......####',
  '##.T....####',
  '##..##..####',
  '#####..#####',
  '#####..#####',
  '#####......#',
  '#####....T.W',
  '#####..D...#',
  '#####..#####',
  '#####..#####',
  '##.....#####',
  '##.D...#####',
  '#####..#####',
  '#####..#####',
  '#####..#####',
];
export const GATES_Z = [-88, -106, -124];

export class Level {
  constructor(scene, physics) {
    this.scene = scene;
    this.physics = physics;
    this.rayTargets = [];   // everything the claws / interaction ray can hit
    this.lights = [];       // light sources, served by a small pool of real lights
    this.items = {};        // named objects
    this.points = {};       // named positions (map letters, spawn spots)
    this.instQueue = {};    // model name -> [Matrix4] for instanced static props
    this.updaters = [];     // per-frame ambient animation callbacks
    this.mats = {
      wallpaper: new THREE.MeshStandardMaterial({ map: T.wallpaper(), roughness: 0.9 }),
      checker: new THREE.MeshStandardMaterial({ map: T.checker(), roughness: 0.6 }),
      concrete: new THREE.MeshStandardMaterial({ map: T.concrete(), roughness: 0.95 }),
      ceiling: new THREE.MeshStandardMaterial({ map: T.concrete('#2a2624'), roughness: 1 }),
      tiles: new THREE.MeshStandardMaterial({ map: T.tiles(), roughness: 0.5 }),
      black: new THREE.MeshBasicMaterial({ color: 0x000000 }),
    };
  }

  // ---------------------------------------------------------------- helpers
  add(name, x, z, { rot = 0, y = 0, scale = 1, collide = null, unique = false, ray = false, inst = false } = {}) {
    if (inst) {
      // static repeated prop: queued and drawn later as one InstancedMesh per sub-mesh
      const m = new THREE.Matrix4().compose(new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rot), new THREE.Vector3(scale, scale, scale));
      (this.instQueue[name] ||= []).push(m);
      if (collide === 'circle') this.physics.circle(x, z, 0.5 * scale);
      else if (Array.isArray(collide)) this.physics.boxAt(x, z, collide[0] * scale, collide[1] * scale, rot);
      return null;
    }
    const o = spawn(name, { uniqueMaterials: unique });
    o.position.set(x, y, z);
    o.rotation.y = rot;
    o.scale.setScalar(scale);
    this.scene.add(o);
    if (collide === 'circle') this.physics.circle(x, z, 0.5 * scale);
    else if (Array.isArray(collide)) this.physics.boxAt(x, z, collide[0] * scale, collide[1] * scale, rot);
    if (ray) this.rayTargets.push(o);
    return o;
  }

  light(x, y, z, { color = 0xffc080, intensity = 6, distance = 12, flicker = 0, on = true } = {}) {
    const l = { pos: new THREE.Vector3(x, y, z), color: new THREE.Color(color), intensity, distance, flicker, on };
    this.lights.push(l);
    return l;
  }

  fenceLine(x0, z0, x1, z1, visual = true) {
    const len = Math.hypot(x1 - x0, z1 - z0);
    const rot = Math.atan2(-(z1 - z0), x1 - x0);
    const n = Math.max(1, Math.round(len / 3));
    if (visual) for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      this.add('fence', x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, { rot, scale: len / n / 3, inst: true });
    }
    const pad = 0.2;
    this.physics.box(Math.min(x0, x1) - pad, Math.max(x0, x1) + pad, Math.min(z0, z1) - pad, Math.max(z0, z1) + pad, 'fence');
  }

  wall(x0, z0, x1, z1, h = 3.6, mat = this.mats.concrete) {
    const w = Math.max(0.2, Math.abs(x1 - x0)), d = Math.max(0.2, Math.abs(z1 - z0));
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.position.set((x0 + x1) / 2, h / 2, (z0 + z1) / 2);
    m.receiveShadow = m.castShadow = true;
    this.scene.add(m);
    this.rayTargets.push(m);
    this.physics.box(Math.min(x0, x1), Math.max(x0, x1), Math.min(z0, z1), Math.max(z0, z1), 'wall');
    return m;
  }

  plane(x, y, z, w, d, mat, repeat = [1, 1], rotX = -Math.PI / 2) {
    const mm = mat.clone();
    if (mm.map) { mm.map = mm.map.clone(); mm.map.repeat.set(...repeat); mm.map.needsUpdate = true; }
    const p = new THREE.Mesh(new THREE.PlaneGeometry(w, d), mm);
    p.rotation.x = rotX;
    p.position.set(x, y, z);
    p.receiveShadow = true;
    this.scene.add(p);
    return p;
  }

  decal(tex, x, y, z, w, h, rotY) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9, transparent: true, polygonOffset: true, polygonOffsetFactor: -2 }));
    m.position.set(x, y, z);
    m.rotation.y = rotY;
    this.scene.add(m);
    return m;
  }

  interact(obj, spec) {
    obj.userData.interact = spec;
    spec.obj = obj;
    if (!this.rayTargets.includes(obj)) this.rayTargets.push(obj);
    return spec;
  }

  /** Floor cells whose south (-Z) neighbour is a wall: good spots for wall decals. */
  wallFaces(map, x0, z0, cell, every = 5) {
    const out = [];
    let n = 0;
    for (let i = 0; i < map.length - 1; i++) for (let j = 0; j < map[0].length; j++) {
      if (map[i][j] === '#' || map[i + 1][j] !== '#') continue;
      if (n++ % every) continue;
      out.push(new THREE.Vector3(x0 + j * cell + cell / 2, 0, z0 - i * cell - cell + 0.02));
    }
    return out;
  }

  /** Build an ASCII maze: '#' wall cells merged into one mesh, letters become named points. */
  maze(map, x0, z0, cell, height, wallMat, floorMat, ceilMat, prefix) {
    const geos = [];
    const rows = map.length, cols = map[0].length;
    for (let i = 0; i < rows; i++) for (let j = 0; j < cols; j++) {
      const ch = map[i][j];
      const cx = x0 + j * cell + cell / 2, cz = z0 - i * cell - cell / 2;
      if (ch === '#') {
        const g = new THREE.BoxGeometry(cell, height, cell);
        g.translate(cx, height / 2, cz);
        geos.push(g);
        this.physics.box(cx - cell / 2, cx + cell / 2, cz - cell / 2, cz + cell / 2, 'maze');
      } else if (ch !== '.') {
        this.points[prefix + ch] = this.points[prefix + ch] || [];
        this.points[prefix + ch].push(new THREE.Vector3(cx, 0, cz));
      }
    }
    const mesh = new THREE.Mesh(mergeGeometries(geos), wallMat);
    mesh.castShadow = mesh.receiveShadow = true;
    this.scene.add(mesh);
    this.rayTargets.push(mesh);
    const w = cols * cell, d = rows * cell;
    this.plane(x0 + w / 2, 0.01, z0 - d / 2, w, d, floorMat, [cols / 2, rows / 2]);
    const c = this.plane(x0 + w / 2, height, z0 - d / 2, w, d, ceilMat, [cols / 2, rows / 2], Math.PI / 2);
    return mesh;
  }

  // ---------------------------------------------------------------- build
  build() {
    buildPark(this);
    this.flushInstances();
    this.physics.rebuild();
    placeInteriorPoints(this);
  }

  flushInstances() {
    for (const [name, mats] of Object.entries(this.instQueue)) {
      const src = spawn(name);
      src.updateMatrixWorld(true);
      src.traverse((m) => {
        if (!m.isMesh) return;
        const im = new THREE.InstancedMesh(m.geometry, m.material, mats.length);
        mats.forEach((M, i) => im.setMatrixAt(i, M.clone().multiply(m.matrixWorld)));
        im.castShadow = !['fence', 'coaster_hill', 'coaster_track'].includes(name);
        im.receiveShadow = true;
        im.computeBoundingSphere();
        this.scene.add(im);
      });
    }
    this.instQueue = {};
  }

  /** Park map board with a live-drawn map and a "you are here" pin. */
  mapBoard(x, z, rot = 0) {
    const b = this.add('mapboard', x, z, { rot, collide: [2.9, 0.4] });
    const scr = b.getObjectByName('Screen');
    if (scr) scr.visible = false;
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 1.6),
      new THREE.MeshStandardMaterial({ map: mapTexture({ here: { x, z } }), color: 0x77706a, roughness: 0.95 }));
    plane.position.set(0, 1.68, 0.045);
    b.add(plane);
    this.light(x + Math.sin(rot) * 1.2, 2.9, z + Math.cos(rot) * 1.2, { color: 0xffd8a0, intensity: 1.6, distance: 4, flicker: 0.1 });
    return b;
  }

  /** Sagging strings of carnival bulbs between posts; a few still glow. */
  stringLights(posts, litRatio = 0.3) {
    const on = new THREE.MeshBasicMaterial({ color: 0xffc070 });
    const off = new THREE.MeshStandardMaterial({ color: 0x2a2620, roughness: 0.3 });
    const geo = new THREE.SphereGeometry(0.055, 6, 4);
    const lit = [], dead = [];
    const wire = [];
    for (let i = 0; i < posts.length - 1; i++) {
      const a = new THREE.Vector3(...posts[i]), b = new THREE.Vector3(...posts[i + 1]);
      const n = Math.round(a.distanceTo(b) / 0.8);
      for (let k = 0; k <= n; k++) {
        const t = k / n;
        const p = a.clone().lerp(b, t);
        p.y -= Math.sin(Math.PI * t) * 1.1;
        wire.push(p);
        if (k % 2 === 0) (Math.random() < litRatio ? lit : dead).push(p);
      }
      const mid = a.clone().lerp(b, 0.5); mid.y -= 1.1;
      if (litRatio > 0.2) this.light(mid.x, mid.y, mid.z, { color: 0xffb060, intensity: 1.5, distance: 7, flicker: 0.2 });
    }
    this.scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(wire), new THREE.LineBasicMaterial({ color: 0x111111 })));
    for (const [list, mat] of [[lit, on], [dead, off]]) {
      if (!list.length) continue;
      const im = new THREE.InstancedMesh(geo, mat, list.length);
      list.forEach((p, i) => im.setMatrixAt(i, new THREE.Matrix4().makeTranslation(p.x, p.y, p.z)));
      this.scene.add(im);
    }
  }

  groundDecal(texture, x, z, w, d, rot = 0, opacity = 1) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({
      map: texture, transparent: true, opacity, roughness: 0.6, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 }));
    m.rotation.set(-Math.PI / 2, 0, rot);
    m.position.set(x, 0.015, z);
    m.receiveShadow = true;
    this.scene.add(m);
    return m;
  }

}
