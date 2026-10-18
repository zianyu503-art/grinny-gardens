import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { spawn, setEmit } from './assets.js';
import * as T from './textures.js';
import * as A from './atmosphere.js';
import { mapTexture } from './map.js';

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
    const { scene } = this;
    scene.background = new THREE.Color(0x040406);
    scene.fog = new THREE.FogExp2(0x040406, 0.05);
    scene.add(new THREE.HemisphereLight(0x3a4058, 0x100808, 0.35));
    const moon = new THREE.DirectionalLight(0x8090c0, 0.35);
    moon.position.set(-30, 60, 20);
    scene.add(moon);

    // ground, with a gap for the pit under the bridge
    const asphalt = new THREE.MeshStandardMaterial({ map: T.asphalt(), roughness: 0.95 });
    const g1 = new THREE.Mesh(new THREE.PlaneGeometry(90, 210), asphalt);
    g1.rotation.x = -Math.PI / 2; g1.position.set(0, 0, -29); g1.receiveShadow = true; scene.add(g1);
    const g2 = new THREE.Mesh(new THREE.PlaneGeometry(90, 70), asphalt);
    g2.rotation.x = -Math.PI / 2; g2.position.set(0, 0, -177); g2.receiveShadow = true; scene.add(g2);
    for (const s of [-1, 1]) {
      const g3 = new THREE.Mesh(new THREE.PlaneGeometry(33, 8), asphalt);
      g3.rotation.x = -Math.PI / 2; g3.position.set(s * 28.5, 0, -138); scene.add(g3);
    }
    const pit = new THREE.Mesh(new THREE.BoxGeometry(24, 30, 8), new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide }));
    pit.position.set(0, -15, -138); scene.add(pit);

    this.buildEntrance();
    this.buildCarousel();
    this.buildFunhouse();
    this.buildTunnel();
    this.buildCoaster();
    this.buildFerris();
    this.scatterTrees();
    this.dressing();
    this.flushInstances();
    this.physics.rebuild();
  }

  buildEntrance() {
    const P = this.physics;
    this.fenceLine(-15, 66, 15, 66);
    this.fenceLine(-15, 40, -15, 66);
    this.fenceLine(15, 40, 15, 66);
    this.fenceLine(-15, 40, -4.6, 40);
    this.fenceLine(4.6, 40, 15, 40);
    const arch = (this.items.arch = this.add('arch', 0, 40));
    P.circle(-4, 40, 0.55); P.circle(4, 40, 0.55);
    this.items.gateCollider = P.box(-3.6, 3.6, 39.8, 40.2, 'gate');
    this.items.doorL = arch.getObjectByName('DoorL');
    this.items.doorR = arch.getObjectByName('DoorR');
    this.rayTargets.push(arch);
    this.light(0, 6.2, 40.6, { color: 0xffb070, intensity: 5, distance: 14, flicker: 0.3 });

    this.add('booth', -6, 51, { collide: [2.6, 2.4] });
    this.light(-6, 2.6, 49.5, { color: 0xff9050, intensity: 3, distance: 6, flicker: 0.6 });
    const crate = this.add('crate', -3.4, 49.6, { collide: [1, 1] });
    const pack = (this.items.packPickup = this.add('clawpack', -3.4, 49.6, { y: 1.05, rot: 0.6 }));
    this.items.posterBooth = this.decal(T.poster('微笑樂園', '每個孩子\n都會笑著回家'), -6, 1.8, 52.25, 1.0, 1.5, 0);

    const gen = (this.items.gen1 = this.add('generator', 8, 47, { collide: [1.5, 1.1], rot: -0.4 }));
    const rec = (this.items.rec1 = this.add('receiver', 5.2, 42.2, { collide: [0.5, 0.4], unique: true }));
    setEmit(rec.getObjectByName('Socket'), 0.6);

    this.add('lamp', -5, 58, { collide: 'circle', inst: true });
    this.light(-5, 3.7, 57.6, { intensity: 6, distance: 12, flicker: 0.08 });
    this.add('lamp', 5, 58, { rot: Math.PI, collide: 'circle', inst: true });
    this.add('lamp', 4.5, 44, { rot: Math.PI, collide: 'circle', inst: true });
    this.light(4.5, 3.7, 44.4, { intensity: 4, distance: 10, flicker: 0.5 });
    this.add('bench', 10, 58, { rot: -Math.PI / 2, collide: [1.8, 0.6] });
    this.add('bench', -10, 46, { rot: Math.PI / 2, collide: [1.8, 0.6] });
    this.add('trash', -9, 59, { collide: 'circle', scale: 0.8 });
    this.add('plush_pile', 11, 62, { collide: [1.6, 1.6] });
    this.add('balloon_cart', 10.5, 51.5, { rot: -0.6, collide: [1.4, 1] });
    this.points.spawn = new THREE.Vector3(0, 0, 63);
    this.points.statue = [new THREE.Vector3(2, 0, 31), new THREE.Vector3(-6, 0, 27), new THREE.Vector3(7, 0, 33),
      new THREE.Vector3(-2, 0, 35), new THREE.Vector3(0, 0, 29)];
  }

  buildCarousel() {
    // the plaza now spans x -44..44 with side attractions west (bumper cars) and east (big top)
    this.fenceLine(-44, 0, -44, 40);
    this.fenceLine(44, 0, 44, 40);
    this.fenceLine(-44, 40, -15, 40);
    this.fenceLine(15, 40, 44, 40);
    this.fenceLine(-44, 0, -12.2, 0, false);
    this.fenceLine(12.2, 0, 44, 0, false);
    for (let x = -42.5; x <= -13; x += 3) this.add('fence', x, 0.2, { inst: true });
    for (let x = 13.5; x <= 43; x += 3) this.add('fence', x, 0.2, { inst: true });
    const car = (this.items.carousel = this.add('carousel', 0, 20));
    this.physics.circle(0, 20, 6.4);
    this.items.carouselSpin = car.getObjectByName('Spin');
    this.items.carouselLight = this.light(0, 4.0, 20, { color: 0xffa060, intensity: 0, distance: 16, flicker: 0.4 });

    // ---- west: bumper car pavilion (entrance faces the plaza, +X)
    const ar = (this.items.arena = this.add('bumper_arena', -34, 22, { rot: Math.PI / 2 }));
    for (const [lx, lz, w, d] of [[0, -4.85, 14, 0.3], [6.85, 0, 0.3, 10], [-6.85, 0, 0.3, 10], [-4.5, 4.85, 5, 0.3], [4.5, 4.85, 5, 0.3]]) {
      this.localBox(ar, lx, lz, w, d);
    }
    for (const lx of [-7, 0, 7]) for (const lz of [-5, 5]) this.localCircle(ar, lx, lz, 0.2);
    const carCols = [0xa02020, 0x2050a0, 0xa08020, 0x208050, 0x8030a0, 0xd0d0c0];
    [[-36.5, 18, 0.4], [-31.5, 20, 2.2], [-35, 26.5, -1.1], [-31, 25.5, 3.0], [-37.5, 22.5, 1.6], [-33, 16.5, -0.3]].forEach(([x, z, r], i) => {
      const c = this.add('bumper_car', x, z, { rot: r, unique: true, collide: [1.4, 2.0] });
      c.traverse((o) => o.isMesh && o.material.color.set(carCols[i]));
    });
    this.light(-34, 3.9, 22, { color: 0xff5050, intensity: 3, distance: 10, flicker: 0.6 });
    this.light(-30, 3.9, 18, { color: 0x50a0ff, intensity: 2, distance: 8, flicker: 0.8 });

    // ---- east: the big top (entrance faces the plaza, -X)
    const tent = (this.items.tent = this.add('circus_tent', 34, 21, { rot: -Math.PI / 2 }));
    for (let k = 0; k < 40; k++) {
      const a = (2 * Math.PI * k) / 40;
      if (Math.abs(Math.atan2(Math.sin(a - Math.PI), Math.cos(a - Math.PI))) < 0.2) continue; // doorway
      this.physics.circle(34 + 9 * Math.cos(a), 21 + 9 * Math.sin(a), 0.75);
    }
    this.physics.circle(34, 21, 0.4);
    this.physics.box(34 + 4.8, 34 + 7.8, 21 - 4.5, 21 + 4.5, 'bleachers');
    this.light(34, 6, 21, { color: 0xff3020, intensity: 2.5, distance: 12, flicker: 0.3 });
    this.add('circus_wagon', 27, 34.5, { rot: Math.PI + 0.3, collide: [3.8, 2.2] });
    this.add('stall_tent', 22, 3.5, { rot: -0.2, collide: [3, 2.4] });

    // ---- plaza clutter and side rides
    const tc = (this.items.teacups = this.add('teacups', -15, 7));
    this.physics.circle(-15, 7, 5.2);
    this.items.teacupSpin = tc.getObjectByName('Spin');
    this.add('cotton_candy', 10, 31, { rot: 0.3, collide: [1.6, 0.9] });
    this.add('striker', 17, 4, { rot: -0.4, collide: [0.9, 0.9] });
    this.add('stall_tent', -26, 36, { rot: 0.2, collide: [3, 2.4] });
    this.add('popcorn', -18, 34.5, { collide: [2.1, 1.3] });
    this.add('balloon_cart', 17, 33, { rot: 0.4, collide: [1.4, 1] });
    this.add('bench', -20, 22, { rot: Math.PI / 2, collide: [1.8, 0.6] });
    this.add('bench', 19, 18, { rot: -Math.PI / 2, collide: [1.8, 0.6] });
    this.add('trash', 19.5, 9, { collide: 'circle', scale: 0.8 });
    this.add('trash', -12, 30, { collide: 'circle', scale: 0.8 });
    this.add('trashbags', 13, 1.5, { collide: [2.2, 1.4] });
    this.add('trashbags', -40, 38, { rot: 1, collide: [2.2, 1.4] });
    this.add('crate', -23, 4, { collide: [1, 1] });
    this.add('crate', -22, 5.2, { collide: [1, 1], rot: 0.4 });
    this.add('crate', 21, 28, { collide: [1, 1], rot: 0.2 });
    this.add('plush_pile', 6, 4, { collide: [1.6, 1.6] });
    this.add('coaster_car', -30, 4, { rot: 2.2, collide: [1.6, 2.2] });
    this.add('signpost', 3, 36.5, { rot: 0.2, collide: 'circle', scale: 1 });
    this.mapBoard(-7, 36.5, 0.15);
    for (const [x, z, r] of [[-11, 36, 0], [11, 36, Math.PI], [-12, 14, 0], [12, 10, Math.PI], [-24, 20, 0], [24, 8, Math.PI]]) {
      this.add('lamp', x, z, { rot: r, collide: 'circle', inst: true });
    }
    this.light(-11, 3.7, 35.6, { intensity: 5, distance: 11, flicker: 0.15 });
    this.light(12, 3.7, 10.4, { intensity: 4, distance: 10, flicker: 0.7 });
    this.light(-24, 3.7, 20.4, { intensity: 4, distance: 10, flicker: 0.3 });
    this.stringLights([[-11, 3.9, 36], [-24, 3.9, 20], [-12, 3.9, 14]], 0.35);
    this.stringLights([[11, 3.9, 36], [24, 3.9, 8], [12, 3.9, 10]], 0.15);
    this.decal(T.poster('旋轉木馬', '永遠轉下去\n永遠不停'), -17.96, 1.6, 35.17, 0.8, 1.2, 0);

    // fun-house facade with jaw door and the fuse box
    const fh = (this.items.funhouse = this.add('funhouse', 0, 0));
    this.physics.box(-12, -1.5, -0.3, 0.3, 'facade');
    this.physics.box(1.5, 12, -0.3, 0.3, 'facade');
    this.items.jawCollider = this.physics.box(-1.5, 1.5, -0.3, 0.3, 'jaw');
    this.items.jaw = fh.getObjectByName('Jaw');
    this.rayTargets.push(fh);
    const fb = (this.items.fusebox = this.add('fusebox', 3.8, 0.75, { collide: [0.9, 0.4], unique: true }));
    this.light(0, 7.5, 1.5, { color: 0xff3040, intensity: 4, distance: 9, flicker: 0.25 });

    this.points.fuses = [new THREE.Vector3(-38, 0.08, 25.5), new THREE.Vector3(34, 0.06, 21), new THREE.Vector3(0, 0.45, 14.4)];
    this.points.batteries2 = [new THREE.Vector3(12, 0.02, 36), new THREE.Vector3(-21.5, 0.02, 14), new THREE.Vector3(20, 0.02, 24),
      new THREE.Vector3(-8, 0.02, 3), new THREE.Vector3(-30.5, 0.08, 27), new THREE.Vector3(30, 0.02, 14.5)];
    this.points.horseHome = [[-4.6, 20, 1.6], [3.2, 23.4, -2.4], [2.6, 15.8, 0.5], [-1.5, 24.3, 3.0]];
    this.points.horseWake = [new THREE.Vector3(-22, 0, 27), new THREE.Vector3(24, 0, 2.5), new THREE.Vector3(28, 0, 38),
      new THREE.Vector3(36.5, 0, 14.2)];
  }

  /** Collider box given in a model's local XZ frame (rotation in 90° steps). */
  localBox(obj, lx, lz, w, d) {
    const c = Math.cos(obj.rotation.y), s = Math.sin(obj.rotation.y);
    const x = obj.position.x + lx * c + lz * s, z = obj.position.z - lx * s + lz * c;
    return this.physics.boxAt(x, z, w, d, obj.rotation.y);
  }

  localCircle(obj, lx, lz, r) {
    const c = Math.cos(obj.rotation.y), s = Math.sin(obj.rotation.y);
    return this.physics.circle(obj.position.x + lx * c + lz * s, obj.position.z - lx * s + lz * c, r);
  }

  buildFunhouse() {
    const cell = 2, x0 = -16, z0 = 0;
    this.maze(FUN_MAP, x0, z0, cell, 3.6, this.mats.wallpaper, this.mats.checker, this.mats.ceiling, 'f');
    // keycard door at the back
    const door = (this.items.fhDoor = this.add('staff_door', 0, -36));
    this.items.fhDoorCollider = this.physics.box(-0.7, 0.7, -36.15, -35.85, 'door');
    this.wall(-2, -35.9, -0.7, -36.1, 3.6, this.mats.wallpaper);
    this.wall(0.7, -35.9, 2, -36.1, 3.6, this.mats.wallpaper);
    this.rayTargets.push(door);
    // red emergency lights
    for (const k of ['a', 'd', 'e', 'b']) {
      const p = this.points['f' + k][0];
      this.light(p.x, 3.3, p.z, { color: 0xff2a20, intensity: 3.5, distance: 7, flicker: 0.35 });
    }
    const words = ['他聽得到你', '不要跑', '笑一個', '他在笑', '安靜', '救救我們'];
    this.wallFaces(FUN_MAP, x0, z0, cell, 7).forEach((p, i) => {
      if (i < words.length) this.decal(T.drawing(3, words[i]), p.x, 1.7, p.z, 1.4, 1.05, 0);
    });
  }

  buildTunnel() {
    const cell = 2, x0 = -12, z0 = -36;
    this.maze(TUN_MAP, x0, z0, cell, 3.0, this.mats.concrete, this.mats.tiles, this.mats.ceiling, 't');
    // window in the east room
    const wp = this.points.tW[0];
    this.physics.box(wp.x - 1, wp.x + 1, wp.z - 1, wp.z + 1, 'window');
    this.wall(wp.x - 1, wp.z + 1, wp.x + 1, wp.z + 0.9, 3.0);
    this.wall(wp.x - 1, wp.z - 0.9, wp.x + 1, wp.z - 1, 3.0);
    this.wall(wp.x - 0.1, wp.z - 1, wp.x + 0.1, wp.z + 1, 0.9);
    const top = this.wall(wp.x - 0.1, wp.z - 1, wp.x + 0.1, wp.z + 1, 0.8);
    top.position.y = 2.6;
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(2, 1.7),
      new THREE.MeshStandardMaterial({ color: 0x0a1014, roughness: 0.05, metalness: 0.4, transparent: true, opacity: 0.45 }));
    glass.position.set(wp.x - 0.05, 1.75, wp.z); glass.rotation.y = -Math.PI / 2;
    this.scene.add(glass);
    this.points.window = wp.clone();
    // exit door
    const door = (this.items.tunDoor = this.add('staff_door', 0, -70));
    this.items.tunDoorCollider = this.physics.box(-0.7, 0.7, -70.15, -69.85, 'door');
    this.wall(-2, -69.9, -0.7, -70.1, 3.0);
    this.wall(0.7, -69.9, 2, -70.1, 3.0);
    this.rayTargets.push(door);
    // flickering fluorescent tubes
    for (const z of [-40, -50, -60, -66]) this.light(0, 2.9, z, { color: 0xc8f0e0, intensity: 3.5, distance: 9, flicker: 0.25 });
    this.items.windowLight = this.light(8, 2.9, -53, { color: 0xc8f0e0, intensity: 3, distance: 8, flicker: 0.1 });
    // children's drawings
    let k = 0;
    const texts = [null, '我們的新朋友', '他說永遠不會長大', null];
    for (const p of this.points.tD || []) {
      for (let n = 0; n < 3; n++) {
        this.decal(T.drawing(k % 3, texts[k % 4]), p.x - 0.6 + n * 0.6, 1.3 + (n % 2) * 0.5, p.z - 0.98, 0.55, 0.42, 0);
        k++;
      }
    }
    this.decal(T.poster('員工守則', '1. 永遠保持微笑\n2. 不要直視熊的眼睛'), -2.98, 1.6, -45, 0.9, 1.35, Math.PI / 2);
    this.decal(T.poster('永恆歡樂計畫', '機密　1996', '#1a1a3a'), 1.98, 1.6, -62, 0.9, 1.35, -Math.PI / 2);
  }

  buildCoaster() {
    const z0 = -70, z1 = -134;
    // corridor walls (fence look) and track overhead
    this.fenceLine(-4, z0, -4, z1);
    this.fenceLine(4, z0, 4, z1);
    for (let z = z0 - 4; z > z1; z -= 4) {
      for (const s of [-1, 1]) {
        this.add('coaster_support', 7 * s, z, { inst: true });
        this.add('coaster_track', 7 * s, z, { y: 5.2, inst: true });
      }
    }
    this.add('coaster_car', 7, -97, { y: 5.25 });
    this.items.gates = GATES_Z.map((gz, i) => {
      const g = this.add('coaster_gate', 0, gz);
      const grate = g.getObjectByName('Grate');
      const collider = this.physics.box(-2.3, 2.3, gz - 0.15, gz + 0.15, 'grate');
      this.physics.box(-4, -2.4, gz - 0.2, gz + 0.2, 'gatepost');
      this.physics.box(2.4, 4, gz - 0.2, gz + 0.2, 'gatepost');
      const h = this.add('gate_handle', 3.2, gz + 2.6, { collide: 'circle', scale: 1 });
      this.light(-3.5, 3.4, gz + 0.5, { color: 0xff3020, intensity: 3, distance: 8, flicker: 0.5 });
      return { model: g, grate, collider, handle: h, open: false, z: gz };
    });
    // pit and bridge
    this.physics.box(-12, -1.6, -142, -134, 'pit');
    this.physics.box(1.6, 12, -142, -134, 'pit');
    this.items.pitBlock = this.physics.box(-1.6, 1.6, -141.5, -140.5, 'pitblock');
    this.physics.setEnabled(this.items.pitBlock, false);
    const br = (this.items.bridge = this.add('bridge', 0, -138));
    this.items.lever = this.add('lever', 2.6, -144.2, { collide: [0.4, 0.3], ray: true });
    this.light(2.6, 2.5, -143.5, { color: 0xffa040, intensity: 3, distance: 6, flicker: 0.2 });
    this.light(0, 3.0, -136, { color: 0x6080ff, intensity: 2, distance: 9, flicker: 0.1 });
  }

  buildFerris() {
    this.fenceLine(-25, -144, -25, -200);
    this.fenceLine(25, -144, 25, -200);
    this.fenceLine(-25, -200, 25, -200);
    this.fenceLine(-25, -142, -12, -142);
    this.fenceLine(12, -142, 25, -142);
    this.fenceLine(-12, -142, -12, -134, false);
    this.fenceLine(12, -142, 12, -134, false);
    const f = (this.items.ferris = this.add('ferris', 0, -186, { unique: true }));
    this.physics.box(-5, 5, -188, -184, 'ferris');
    const wheel = f.getObjectByName('Wheel');
    // cabins follow the wheel but stay upright
    const pivot = new THREE.Object3D();
    pivot.position.copy(wheel.position);
    f.add(pivot);
    f.remove(wheel);
    wheel.position.set(0, 0, 0);
    pivot.add(wheel);
    this.items.cabins = [];
    for (let i = 0; i < 8; i++) {
      const c = f.getObjectByName('Cabin' + i);
      if (!c) continue;
      f.remove(c);
      c.position.sub(pivot.position);
      pivot.add(c);
      this.items.cabins.push(c);
    }
    this.items.wheel = pivot;
    setEmit(f, 0.0);
    this.items.gen2 = this.add('generator', 0, -160, { collide: [1.5, 1.1] });
    this.items.receivers2 = [[-10, -168, 0.5], [10, -168, -0.5], [-16, -179, 0.8], [16, -179, -0.8]].map(([x, z, r]) => {
      const rc = this.add('receiver', x, z, { rot: r, collide: [0.6, 0.6], unique: true });
      setEmit(rc.getObjectByName('Socket'), 0.6);
      return rc;
    });
    this.items.wheelLight = this.light(0, 10, -184, { color: 0xffb070, intensity: 0, distance: 30, flicker: 0.1 });
    this.light(0, 3, -158, { color: 0x5ab8ff, intensity: 3, distance: 8, flicker: 0.2 });
    for (const [x, z] of [[-18, -150], [18, -152], [-20, -190], [20, -192]]) {
      this.add('lamp', x, z, { collide: 'circle', rot: x > 0 ? Math.PI : 0, inst: true });
    }
    this.light(-18, 3.7, -150.4, { intensity: 4, distance: 10, flicker: 0.5 });
    this.add('plush_pile', -6, -194, { collide: [1.6, 1.6] });
    this.add('plush_pile', 7, -195, { collide: [1.6, 1.6] });
    this.add('popcorn', 19, -170, { rot: -Math.PI / 2, collide: [1.3, 2.1] });
    this.add('trash', -21, -165, { collide: 'circle', scale: 0.8 });
    this.points.batteries6 = [new THREE.Vector3(-21, 0.02, -160), new THREE.Vector3(19, 0.02, -184)];
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

  /** Graffiti, stains, puddles, litter, skyline silhouettes, photos and fog. */
  dressing() {
    const D = (t, x, y, z, w, h, r) => this.decal(t, x, y, z, w, h, r);
    // graffiti on outdoor walls and attractions
    D(A.graffiti('他在看著你'), -7.27, 1.5, 51, 1.8, 0.9, -Math.PI / 2);
    D(A.graffiti('SMILE', '#1a1a1a'), 6, 2.2, 0.32, 3.2, 1.6, 0);
    D(A.graffiti('別讓燈熄掉', '#7a5a0a'), -9, 2.0, 0.32, 3.2, 1.6, 0);
    D(A.handprints(), 1.98, 1.4, -58, 1.2, 1.2, -Math.PI / 2);
    D(A.handprints(), -1.98, 1.2, -48, 1.2, 1.2, Math.PI / 2);
    this.groundDecal(A.graffiti('跑', '#6a0606', 256, 256), 0, -95, 2.6, 2.6, 0, 0.9);
    this.groundDecal(A.graffiti('不要回頭'), 0, -115, 4, 2, 0, 0.9);
    // drag marks leading into the fun house and toward the ferris wheel
    this.groundDecal(A.dragMarks(), 0.5, 6, 1.2, 9, 0.05);
    this.groundDecal(A.dragMarks(), -1, -170, 1.2, 12, -0.1);
    this.groundDecal(A.dragMarks(), 30, 21, 1.0, 8, Math.PI / 2 - 0.2, 0.8);
    // puddles reflecting the lamps
    const pm = A.puddleMap();
    const pmat = new THREE.MeshStandardMaterial({ color: 0x1c1e22, roughness: 0.08, metalness: 0.25, alphaMap: pm, transparent: true, opacity: 0.7, depthWrite: false });
    for (const [x, z, w] of [[3, 56, 5], [-8, 44, 4], [6, 28, 6], [-10, 16, 5], [20, 12, 4], [-30, 8, 5], [0, -80, 3],
      [1, -112, 3], [-8, -162, 6], [9, -176, 5], [-5, 60, 3]]) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w), pmat);
      m.rotation.set(-Math.PI / 2, 0, x);
      m.position.set(x, 0.012, z);
      this.scene.add(m);
    }
    // litter: tickets, popcorn boxes, leaves (one instanced mesh, per-instance colour)
    const litter = new THREE.InstancedMesh(new THREE.BoxGeometry(0.16, 0.012, 0.1),
      new THREE.MeshStandardMaterial({ roughness: 0.9 }), 900);
    const cols = [0x6a5a3a, 0x3a2a1a, 0x8a1a1a, 0xb0a890, 0x2a3a1a, 0x4a3a2a];
    const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler();
    const areas = [[-14, 41, 14, 65, 140], [-43, 1, 43, 39, 420], [-3.5, -133, 3.5, -71, 120], [-24, -199, 24, -143, 220]];
    let n = 0;
    for (const [x0, z0, x1, z1, k] of areas) {
      for (let i = 0; i < k; i++, n++) {
        const x = x0 + Math.random() * (x1 - x0), z = z0 + Math.random() * (z1 - z0);
        Q.setFromEuler(E.set(0, Math.random() * 6.3, (Math.random() - 0.5) * 0.3));
        const sc = 0.6 + Math.random() * 1.4;
        M4.compose(new THREE.Vector3(x, 0.01, z), Q, new THREE.Vector3(sc, 1, sc));
        litter.setMatrixAt(n, M4);
        litter.setColorAt(n, new THREE.Color(cols[n % cols.length]));
      }
    }
    litter.count = n;
    litter.receiveShadow = true;
    this.scene.add(litter);
    // skyline: giant silhouettes beyond the fences
    this.add('coaster_hill', -62, -40, { rot: 0.3, scale: 1.3, inst: true });
    this.add('coaster_hill', 60, 12, { rot: -0.5, scale: 1.4, inst: true });
    this.add('coaster_hill', 50, -110, { rot: 0.1, scale: 1.2, inst: true });
    this.add('billboard', 24, 52, { rot: -Math.PI / 2 - 0.3, collide: [1, 1] });
    this.add('billboard', -34, -160, { rot: Math.PI / 2 + 0.2, scale: 1.2 });
    // entrance extras
    this.add('turnstile', -11.5, 47, { rot: Math.PI / 2, collide: [1.2, 1] });
    this.add('turnstile', -13.5, 47, { rot: Math.PI / 2, collide: [1.2, 1] });
    this.add('stall_tent', 10, 44.5, { rot: Math.PI, collide: [3, 2.4] });
    this.add('trashbags', -12, 55, { collide: [2.2, 1.4] });
    this.mapBoard(-8.5, 60, 0.4);
    // ferris plaza extras (cover from sight lines)
    this.add('stall_tent', -13, -152, { rot: 0.4, collide: [3, 2.4] });
    this.add('cotton_candy', 12, -154, { rot: -0.3, collide: [1.6, 0.9] });
    this.add('striker', -21, -186, { rot: 0.9, collide: [0.9, 0.9] });
    this.add('circus_wagon', 17, -191, { rot: -0.4, collide: [3.8, 2.2] });
    this.add('trashbags', 21, -147, { collide: [2.2, 1.4] });
    this.add('signpost', 3, -146.5, { rot: Math.PI - 0.3, collide: 'circle' });
    this.mapBoard(-6, -147, 0);
    this.stringLights([[-18, 3.9, -150], [0, 6, -160], [18, 3.9, -152]], 0.25);
    // collectible photos of the missing children
    this.points.photos = [[12.4, 63.6], [-31, 17.2], [39.8, 25.5], [-12.4, 7.2, 0.52], [9, -7], [-7, -41], [-3.3, -80], [-4.5, -193]]
      .map(([x, z, y = 0.02]) => new THREE.Vector3(x, y, z));
    // ground fog banks
    this.updaters.push(A.groundFog(this.scene, [[-14, 41, 14, 65, 14], [-43, 1, 43, 39, 40], [-4, -133, 4, -72, 14], [-24, -199, 24, -143, 26],
      [-12, -142, 12, -134, 8]]));
  }

  scatterTrees() {
    const spots = [[-12, 63], [13, 45], [-22, 30], [-23, 12], [-41, 4], [-41, 33], [41, 3], [-28, 50], [28, 58], [-36, 46], [38, 48],
      [-9, -80], [10, -100], [-10, -120], [11, -76], [-22, -150], [23, -196], [-30, -170], [30, -160], [-14, -198]];
    spots.forEach(([x, z], i) => this.add('deadtree', x, z, { rot: i * 1.7, scale: 0.9 + (i % 3) * 0.2, collide: 'circle', inst: true }));
  }
}
