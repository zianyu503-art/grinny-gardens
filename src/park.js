// Builds the playable level from the hand-made park scene (public/models/park.glb + public/park.json,
// produced by blender/export_park.py). Fills level.items / level.points with everything game.js uses.
import * as THREE from 'three';
import { spawn, setEmit, getPark } from './assets.js';
import * as T from './textures.js';
import * as A from './atmosphere.js';
import { setMapLayout } from './map.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function buildPark(L) {
  const { scene, physics: P } = L;
  const { gltf, data } = getPark();
  const pt = (k) => data.points[k];
  const C = (k) => { const p = pt(k).c; return V(p[0], p[1], p[2]); };
  const hw = data.halfWidth;
  const Z = data.zones;
  const zEnd = Z.ferris.zBack - 3;
  const zStart = Z.gate.zFront + 10;

  scene.background = new THREE.Color(0x05060a);
  scene.fog = new THREE.FogExp2(0x05060a, 0.036);
  scene.add(new THREE.HemisphereLight(0x46507a, 0x120a10, 0.8));
  const moon = new THREE.DirectionalLight(0x7f96d0, 0.5);
  moon.position.set(-30, 60, 20);
  scene.add(moon);

  // ---------------------------------------------------------------- ground with a hole for the abyss
  const pitMin = pt('pitLip').min, pitMax = pt('pitLip').max;
  const pit = { x0: Math.min(pitMin[0], pitMax[0]), x1: Math.max(pitMin[0], pitMax[0]),
    z0: Math.min(pitMin[2], pitMax[2]), z1: Math.max(pitMin[2], pitMax[2]) };
  const asphalt = new THREE.MeshStandardMaterial({ map: T.asphalt(), roughness: 0.92, color: 0x9aa0a8 });
  const ground = (x0, x1, z0, z1) => {
    if (x1 - x0 < 0.01 || z1 - z0 < 0.01) return;
    const g = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0), asphalt.clone());
    g.material.map = asphalt.map.clone(); g.material.map.repeat.set((x1 - x0) / 4, (z1 - z0) / 4); g.material.map.needsUpdate = true;
    g.rotation.x = -Math.PI / 2; g.position.set((x0 + x1) / 2, -0.01, (z0 + z1) / 2); g.receiveShadow = true;
    scene.add(g);
  };
  const W = 70;
  ground(-W, W, pit.z1, zStart + 30);
  ground(-W, W, zEnd - 40, pit.z0);
  ground(-W, pit.x0, pit.z0, pit.z1);
  ground(pit.x1, W, pit.z0, pit.z1);

  // ---------------------------------------------------------------- the park scene
  const park = gltf.scene.clone(true);
  park.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  scene.add(park);
  const node = (n) => park.getObjectByName(n);
  park.traverse((o) => { if (o.isMesh && /^Static_/.test(o.name)) L.rayTargets.push(o); });

  // colliders (moving parts keep handles so they can be switched off)
  const tagged = {};
  for (const [x0, x1, z0, z1, tag] of data.colliders) {
    const c = P.box(x0, x1, z0, z1, tag || 'park');
    if (tag) (tagged[tag] ||= []).push(c);
  }
  // light sources from the scene
  for (const l of data.lights) {
    const col = new THREE.Color(...l.color);
    const src = L.light(l.pos[0], l.pos[1], l.pos[2], {
      color: col, intensity: Math.max(1.6, l.energy / 15), distance: 7 + Math.sqrt(l.energy) * 1.1,
      flicker: /emergency|fluorescent|Dying/i.test(l.name) ? 0.35 : 0.08 });
    src.name = l.name;
  }
  const lightNamed = (re) => L.lights.find((l) => re.test(l.name || ''));

  // ---------------------------------------------------------------- perimeter and route barriers
  const fence = (x0, z0, x1, z1) => L.fenceLine(x0, z0, x1, z1);
  fence(-hw, zStart, hw, zStart);
  fence(-hw, zStart, -hw, zEnd);
  fence(hw, zStart, hw, zEnd);
  fence(-hw, zEnd, hw, zEnd);
  const fh = pt('funhouseFloor');
  const fhX = Math.abs(fh.min[0]), fhFront = Math.max(fh.min[2], fh.max[2]), fhBack = Math.min(fh.min[2], fh.max[2]);
  for (const s of [-1, 1]) {
    fence(s * fhX, fhFront - 0.2, s * hw, fhFront - 0.2);   // can't walk around the fun house
    fence(s * fhX, fhBack + 0.2, s * hw, fhBack + 0.2);
  }
  const sp = pt('staffPassage');
  const spX = Math.abs(sp.min[0]) + 0.4, spBack = Math.min(sp.min[2], sp.max[2]);
  const cpth = pt('coasterPath');
  const cpX = Math.abs(cpth.min[0]) + 0.3, cpFront = Math.max(cpth.min[2], cpth.max[2]);
  for (const s of [-1, 1]) {
    fence(s * spX, spBack, s * hw, spBack);               // staff corridor is the only way through
    fence(s * cpX, cpFront + 0.2, s * hw, cpFront + 0.2); // coaster path entrance
    L.wall(s * (spX - 0.2), spBack + 0.2, s * spX, spBack - 0.2, 3.4); // close the corridor end beside the door
  }
  // the abyss: blocked except for the bridge
  const bx = 2.2;
  P.box(-W, -bx, pit.z0, pit.z1, 'pit'); P.box(bx, W, pit.z0, pit.z1, 'pit');
  const pitBlock = P.box(-bx, bx, pit.z0 + 3, pit.z1 - 3, 'pitblock');
  P.setEnabled(pitBlock, false);
  const abyss = new THREE.Mesh(new THREE.BoxGeometry(pit.x1 - pit.x0, 30, pit.z1 - pit.z0),
    new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide }));
  abyss.position.set(0, -15.05, (pit.z0 + pit.z1) / 2);
  scene.add(abyss);

  // ---------------------------------------------------------------- entrance
  const I = L.items;
  const gPiv = data.pivots;
  I.doorL = node('GateL'); I.doorR = node('GateR');
  I.arch = new THREE.Object3D(); I.arch.position.set(0, 0, gPiv.GateL[2]); scene.add(I.arch);
  I.gateCollider = P.box(gPiv.GateL[0], gPiv.GateR[0], gPiv.GateL[2] - 0.5, gPiv.GateL[2] + 0.5, 'gate');
  for (const c of [...(tagged.GateL || []), ...(tagged.GateR || [])]) P.setEnabled(c, false);
  const booth = C('booth');
  L.add('crate', booth.x + 1.2, booth.z + 4.2, { collide: [1, 1] });
  I.packPickup = L.add('clawpack_full', booth.x + 1.2, booth.z + 4.25, { y: 0.95, rot: 0.25, scale: 0.19 });
  I.paperSpot = V(booth.x + 0.6, 1.0, booth.z + 3.75);
  I.gen1 = node('Orb');
  const gate = C('gatePier');
  I.rec1 = L.add('receiver', gPiv.GateR[0] + 2.2, gate.z + 2.2, { collide: [0.6, 0.5], unique: true });
  setEmit(I.rec1.getObjectByName('Socket'), 0.6);
  L.points.spawn = V(0, 0, zStart - 3);
  L.points.statue = [V(2, 0, gate.z - 12), V(-6, 0, gate.z - 16), V(7, 0, gate.z - 10), V(-2, 0, gate.z - 18)];

  // ---------------------------------------------------------------- midway
  const car = C('carouselDeck');
  I.carousel = new THREE.Object3D(); I.carousel.position.copy(car); scene.add(I.carousel);
  I.carouselSpin = node('CarouselTop');
  for (const c of tagged.CarouselTop || []) P.setEnabled(c, false);
  P.circle(car.x, car.z, 5.6);
  I.carouselLight = lightNamed(/Carousel warm/) || L.light(car.x, 4, car.z, { color: 0xffa060 });
  I.carouselLight.intensity = 0;
  I.teacupSpin = new THREE.Object3D();
  const bump = C('bumperSlab'), tent = C('tentWall'), placard = C('tentPlacard');
  L.points.fuses = [V(bump.x, 0.5, bump.z), V(tent.x, 0.35, tent.z), V(car.x, 0.75, car.z + 5.3)];
  L.points.fuseReach = ['walk', 'walk', 'claw'];
  L.points.tentDoor = placard;
  const mz = Z.midway;
  L.points.batteries2 = [V(-hw + 4, 0.02, mz.zFront - 4), V(hw - 4, 0.02, mz.zBack + 4), V(-6, 0.02, mz.zBack + 3)];
  L.points.horseHome = [[car.x - 7.5, car.z, 1.6], [car.x + 7.5, car.z + 1, -1.6], [car.x, car.z - 7.8, 3.1], [car.x - 3, car.z + 7.5, 0]];
  L.points.horseWake = [V(-hw + 3, 0, mz.zFront - 6), V(hw - 3, 0, mz.zFront - 5), V(-hw + 3, 0, mz.zBack + 3), V(tent.x, 0, tent.z - 2)];
  L.points.midwayCheckpoint = V(0, 0, mz.zFront + 6);

  // ---------------------------------------------------------------- fun house
  const mask = C('clownMask');
  const mouthW = 3.3;
  const jaw = new THREE.Mesh(new THREE.BoxGeometry(mouthW * 2, 6.6, 0.3),
    new THREE.MeshStandardMaterial({ color: 0x3a0606, roughness: 0.8 }));
  jaw.position.set(0, 3.3, 0);
  const jawGroup = new THREE.Group();
  jawGroup.position.set(mask.x, 0, mask.z - 0.25);
  jawGroup.add(jaw);
  scene.add(jawGroup);
  I.jaw = jawGroup;
  I.jawDrop = 6.9;
  I.jawCollider = P.box(mask.x - mouthW, mask.x + mouthW, mask.z - 0.6, mask.z + 0.2, 'jaw');
  I.funhouse = jaw;
  L.rayTargets.push(jaw);
  I.fusebox = L.add('fusebox', mask.x + 4.6, mask.z + 1.6, { collide: [0.9, 0.4], unique: true });
  // keycard door at the rear exit
  const rear = C('rearLintel');
  I.fhDoor = makeDoor(L, rear.x, rear.z, 6.0, 5.4, 0x3a4440, 'STAFF ONLY');
  I.fhDoorCollider = P.box(rear.x - 3, rear.x + 3, rear.z - 0.35, rear.z + 0.35, 'door');

  // ---------------------------------------------------------------- staff corridor
  const spFront = Math.max(sp.min[2], sp.max[2]);
  I.tunDoor = makeDoor(L, 0, spBack + 0.05, 2.6, 3.0, 0x2e3436, 'EXIT');
  L.wall(-spX + 0.2, spBack + 0.25, -1.35, spBack - 0.15, 3.4);
  L.wall(1.35, spBack + 0.25, spX - 0.2, spBack - 0.15, 3.4);
  I.tunDoorCollider = P.box(-1.35, 1.35, spBack - 0.2, spBack + 0.25, 'door');
  const east = C('staffEastWall');
  L.points.window = V(east.x, 0, (spFront + spBack) / 2);
  L.points.windowRect = { x0: 0, x1: east.x, z0: spBack, z1: spFront };
  L.points.windowFaceOffset = 2.6;
  for (const l of L.lights) if (/fluorescent/i.test(l.name || '')) l.flicker = 0.3;

  // ---------------------------------------------------------------- coaster run
  const handleX = cpX - 1.1;
  I.gates = [1, 2, 3].map((n) => {
    const g = node('Gate' + n);
    const gz = gPiv['Gate' + n][2];
    const h = L.add('gate_handle', handleX, gz + 2.4, { collide: 'circle', scale: 1.2 });
    return { model: g, grate: g, lift: 5.8, colliders: tagged['Gate' + n] || [], handle: h, open: false, z: gz,
      collider: P.box(-cpX, cpX, gz - 0.25, gz + 0.25, 'grate') };
  });
  for (const g of I.gates) for (const c of g.colliders) P.setEnabled(c, false); // one solid box per gate instead
  I.bridge = node('Bridge');
  I.pitBlock = pitBlock;
  I.lever = L.add('lever', 3.2, pit.z0 - 2.5, { collide: [0.4, 0.3], ray: true });
  L.light(3.2, 2.5, pit.z0 - 2, { color: 0xffa040, intensity: 3, distance: 6, flicker: 0.2 });

  // ---------------------------------------------------------------- ferris plaza
  const hub = C('ferrisAxle'), plat = C('ferrisPlatform');
  I.ferris = new THREE.Object3D(); I.ferris.position.set(hub.x, 0, hub.z); scene.add(I.ferris);
  I.wheel = new THREE.Object3D(); I.cabins = [];
  I.wheelLight = lightNamed(/Ferris golden hub/) || L.light(hub.x, hub.y, hub.z, { color: 0xffb070 });
  I.wheelLight.intensity = 0;
  const fz = Z.ferris;
  I.gen2 = L.add('generator', -10, fz.zFront - 3, { collide: [1.5, 1.1], rot: 0.4 });
  I.receivers2 = [[-12, fz.zFront - 9], [12, fz.zFront - 9], [-17, hub.z - 2], [17, hub.z - 2]].map(([x, z], i) => {
    const rc = L.add('receiver', x, z, { rot: x < 0 ? 0.5 : -0.5, collide: [0.6, 0.6], unique: true });
    setEmit(rc.getObjectByName('Socket'), 0.6);
    return rc;
  });
  L.points.batteries6 = [V(-hw + 4, 0.02, fz.zFront - 6), V(hw - 4, 0.02, hub.z + 2)];
  L.points.hub = hub;
  L.points.directorStart = V(hub.x, -14, hub.z + 7);

  // ---------------------------------------------------------------- route / checkpoints for game.js
  const coasterStart = cpFront;
  L.points.route = {
    carousel: { z: Z.gate.zBack - 2, cp: { x: 0, z: Z.gate.zBack - 4, yaw: 0 } },
    funhouse: { z: fhFront - 1, cp: { x: 0, z: fhFront - 2.5, yaw: 0 } },
    tunnel: { z: spFront - 0.5, cp: { x: 0, z: spFront - 2, yaw: 0 } },
    coaster: { z: spBack - 1, cp: { x: 0, z: spBack - 2.5, yaw: 0 } },
    ferris: { z: pit.z0 - 1, cp: { x: 0, z: pit.z0 - 2.5, yaw: 0 } },
    chaseTrigger: spBack - 5,
    grinnySpawn: V(0, 0, spBack + 2.5),
    tunnelDoor: V(0, 1, spBack),
    leverSideZ: pit.z0 - 0.5,
    bridgeStandZ: (pit.z0 + pit.z1) / 2 + 2,
    finalSoundPos: V(hub.x, 10, hub.z),
  };

  // ---------------------------------------------------------------- decor around the new layout
  L.add('billboard', hw + 8, Z.midway.zFront - 6, { rot: -Math.PI / 2 - 0.3 });
  L.add('coaster_hill', -hw - 30, Z.funhouse.zFront, { rot: 0.3, scale: 1.3, inst: true });
  L.add('coaster_hill', hw + 30, Z.gate.zBack - 10, { rot: -0.5, scale: 1.4, inst: true });
  L.add('coaster_hill', hw + 26, Z.coaster.zFront, { rot: 0.1, scale: 1.2, inst: true });
  [[-hw - 6, zStart - 6], [hw + 6, Z.midway.zFront - 20], [-hw - 8, Z.staff.zFront], [hw + 7, Z.coaster.zBack],
    [-hw - 5, Z.ferris.zFront - 6], [hw + 5, zEnd + 4]].forEach(([x, z], i) =>
    L.add('deadtree', x, z, { rot: i * 1.7, scale: 1.1 + (i % 3) * 0.2, inst: true }));
  // gap areas between zones: trash, plush piles, puddles, fog, litter
  const gaps = [[Z.gate.zBack, Z.midway.zFront], [Z.midway.zBack, Z.funhouse.zFront], [Z.funhouse.zBack, Z.staff.zFront],
    [Z.staff.zBack, Z.coaster.zFront], [Z.coaster.zBack, Z.ferris.zFront]];
  gaps.forEach(([a, b], i) => {
    const zc = (a + b) / 2;
    if (i % 2 === 0) L.add('plush_pile', -hw + 5, zc, { collide: [1.6, 1.6] });
    L.add('trashbags', hw - 5, zc + 1, { rot: i, collide: [2.2, 1.4] });
  });
  L.updaters.push(A.groundFog(scene, [[-hw, Z.gate.zBack, hw, zStart, 10], [-hw, Z.midway.zBack, hw, Z.midway.zFront, 26],
    [-hw, Z.funhouse.zBack, hw, Z.funhouse.zFront, 8], [-6, Z.coaster.zBack, 6, Z.staff.zBack, 10],
    [-hw, zEnd, hw, Z.ferris.zFront, 18]]));
  litter(scene, hw, zStart, zEnd);

  // ---------------------------------------------------------------- map
  setMapLayout({
    minX: -hw - 4, maxX: hw + 4, minZ: zEnd - 3, maxZ: zStart + 3,
    zones: [
      { x0: -hw, x1: hw, z0: Z.gate.zBack, z1: zStart, fill: 'rgba(120,140,90,.35)' },
      { x0: -hw, x1: hw, z0: Z.midway.zBack, z1: Z.midway.zFront, fill: 'rgba(120,140,90,.35)' },
      { x0: -fhX, x1: fhX, z0: fhBack, z1: fhFront, fill: 'rgba(110,60,110,.4)' },
      { x0: -spX, x1: spX, z0: spBack, z1: spFront, fill: 'rgba(90,90,90,.35)', dash: true },
      { x0: -cpX, x1: cpX, z0: Z.coaster.zBack, z1: coasterStart, fill: 'rgba(140,110,70,.35)' },
      { x0: -hw, x1: hw, z0: zEnd, z1: Z.ferris.zFront, fill: 'rgba(120,140,90,.35)' },
    ],
    pit, bridgeHalf: bx,
    path: [[0, zStart - 2], [0, hub.z]],
    circles: [[car.x, car.z, 6, '#b05050'], [tent.x, tent.z, 7, '#c06040'], [C('teacups').x, C('teacups').z, 4, '#a07090'],
      [hub.x, hub.z, 7, 'rgba(160,160,170,.6)']],
    rects: [[bump.x - 7, bump.x + 7, bump.z - 7, bump.z + 7, '#5a6a8a'], [booth.x - 2, booth.x + 2, booth.z - 2, booth.z + 2, '#9a5a3a']],
    labels: [['售票亭', booth.x, booth.z + 3], ['正門', 0, gate.z + 2], ['旋轉木馬', car.x, car.z], ['碰碰車', bump.x, bump.z],
      ['馬戲團', tent.x, tent.z], ['咖啡杯', C('teacups').x, C('teacups').z], ['鬼屋', 0, (fhFront + fhBack) / 2],
      ['員工通道', 0, (spFront + spBack) / 2], ['雲霄飛車', 0, (coasterStart + pit.z1) / 2], ['吊橋', 0, (pit.z0 + pit.z1) / 2],
      ['摩天輪', hub.x, hub.z]],
    scribbles: { funhouse: [0, (fhFront + fhBack) / 2], ferris: [hub.x, hub.z], carousel: [car.x, car.z] },
  });
  L.mapBoard(gPiv.GateL[0] - 4, zStart - 4, 0.3);
  L.mapBoard(-8, Z.midway.zFront - 2, 0);
  L.mapBoard(-8, Z.ferris.zFront - 2, 0);
}

/**
 * Positions that depend on the collision grid (run after physics.rebuild()):
 * fun-house patrol points and pickups, staff-corridor tapes, the eight photos.
 */
export function placeInteriorPoints(L) {
  const P = L.physics, { data } = getPark();
  const pt = (k) => data.points[k];
  const rect = (k, inset = 0.6) => {
    const a = pt(k).min, b = pt(k).max;
    return { x0: Math.min(a[0], b[0]) + inset, x1: Math.max(a[0], b[0]) - inset, z0: Math.min(a[2], b[2]) + inset, z1: Math.max(a[2], b[2]) - inset };
  };
  const fh = rect('funhouseFloor');
  const mouth = V(0, 0, fh.z1 - 1.5);
  const spots = spreadSpots(P, fh, 11, mouth);
  // farthest spot from the entrance holds the keycard; the rest become patrol points and pickups
  L.points.fK = [spots[0]];
  ['a', 'b', 'c', 'd', 'e', 'f'].forEach((k, i) => { L.points['f' + k] = [spots[i + 1]]; });
  L.points.fB = [spots[7]]; L.points.fT = [spots[8]]; L.points.fJ = [spots[9]];
  const fhPhoto = spots[10] || spots[3];
  const st = rect('staffPassage', 1.0);
  const ss = spreadSpots(P, st, 3, V(0, 0, st.z1 - 1));
  L.points.tT = [ss[0], ss[1]];
  const car = pt('carouselDeck').c, bump = pt('bumperSlab').c, tent = pt('tentWall').c, cup = pt('teacups').c;
  const booth = pt('booth').c, cp = rect('coasterPath', 0.4), hub = pt('ferrisAxle').c;
  const near = (x, z) => { const c = freeSpot(P, x, z); return V(c.x, 0.02, c.z); };
  L.points.photos = [
    near(booth[0] - 2, booth[2] + 5), near(bump[0] - 3, bump[2] + 3), near(tent[0] + 2, tent[2] - 2),
    V(cup[0], 0.55, cup[2]), V(fhPhoto.x, 0.02, fhPhoto.z), V(ss[2].x, 0.02, ss[2].z),
    near(-cp.x1 + 0.6, (cp.z0 + cp.z1) / 2), near(hub[0] - 9, hub[2] + 4),
  ];
  for (const f of L.points.fuses) {
    const c = freeSpot(P, f.x, f.z);
    if (L.points.fuseReach[L.points.fuses.indexOf(f)] === 'walk') { f.x = c.x; f.z = c.z; }
  }
}

/** Free nav-grid spot nearest to (x, z). */
export function freeSpot(P, x, z) {
  if (P.dirty) P.rebuild();
  const [i, j] = P.nearestFree(...P.cellOf(x, z));
  return P.center(i, j);
}

/** Cells reachable on foot from a point (4-connected flood fill over the nav grid). */
export function reachable(P, x, z) {
  if (P.dirty) P.rebuild();
  const seen = new Uint8Array(P.w * P.h);
  const [si, sj] = P.nearestFree(...P.cellOf(x, z));
  const q = [sj * P.w + si];
  seen[q[0]] = 1;
  while (q.length) {
    const k = q.pop(), i = k % P.w, j = (k / P.w) | 0;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const a = i + di, b = j + dj;
      if (a < 0 || b < 0 || a >= P.w || b >= P.h) continue;
      const kk = b * P.w + a;
      if (!seen[kk] && !P.grid[kk]) { seen[kk] = 1; q.push(kk); }
    }
  }
  return seen;
}

/** Spread-out free spots inside a rectangle that can be walked to from `from` (farthest-point sampling). */
export function spreadSpots(P, rect, n, from) {
  if (P.dirty) P.rebuild();
  const seen = reachable(P, from.x, from.z);
  const cands = [];
  for (let x = rect.x0 + 1; x < rect.x1 - 1; x += 1) for (let z = rect.z0 + 1; z < rect.z1 - 1; z += 1) {
    const [i, j] = P.cellOf(x, z);
    if (!seen[j * P.w + i]) continue;
    let ok = true;
    for (let di = -1; di <= 1 && ok; di++) for (let dj = -1; dj <= 1; dj++) if (P.blocked(i + di, j + dj)) { ok = false; break; }
    if (ok) cands.push(V(x, 0, z));
  }
  const out = [];
  let ref = [from];
  for (let k = 0; k < n && cands.length; k++) {
    let best = null, bd = -1;
    for (const c of cands) {
      const d = Math.min(...ref.map((r) => Math.hypot(r.x - c.x, r.z - c.z)));
      if (d > bd) { bd = d; best = c; }
    }
    out.push(best); ref.push(best);
  }
  return out;
}

function makeDoor(L, x, z, w, h, color, label) {
  const g = new THREE.Group();
  g.position.set(x - w / 2, 0, z);
  const d = new THREE.Group();
  d.name = 'Door';
  const slab = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.18), new THREE.MeshStandardMaterial({ color, roughness: 0.7, metalness: 0.4 }));
  slab.position.set(w / 2, h / 2, 0);
  slab.castShadow = slab.receiveShadow = true;
  d.add(slab);
  if (label) {
    const c = document.createElement('canvas'); c.width = 256; c.height = 64;
    const g2 = c.getContext('2d');
    g2.fillStyle = '#7a1010'; g2.fillRect(0, 0, 256, 64);
    g2.fillStyle = '#e8e0cc'; g2.font = 'bold 34px sans-serif'; g2.textAlign = 'center'; g2.fillText(label, 128, 44);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.3), new THREE.MeshStandardMaterial({ map: t }));
    sign.position.set(w / 2, Math.min(h - 0.4, 1.9), 0.1);
    d.add(sign);
  }
  g.add(d);
  L.scene.add(g);
  L.rayTargets.push(g);
  return g;
}

function litter(scene, hw, z0, z1) {
  const n = 900;
  const m = new THREE.InstancedMesh(new THREE.BoxGeometry(0.16, 0.012, 0.1), new THREE.MeshStandardMaterial({ roughness: 0.9 }), n);
  const cols = [0x6a5a3a, 0x3a2a1a, 0x8a1a1a, 0xb0a890, 0x2a3a1a, 0x4a3a2a];
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler();
  for (let i = 0; i < n; i++) {
    const x = (Math.random() * 2 - 1) * (hw - 1), z = z1 + Math.random() * (z0 - z1);
    Q.setFromEuler(E.set(0, Math.random() * 6.3, 0));
    const s = 0.6 + Math.random() * 1.4;
    M.compose(V(x, 0.01, z), Q, V(s, 1, s));
    m.setMatrixAt(i, M);
    m.setColorAt(i, new THREE.Color(cols[i % cols.length]));
  }
  m.receiveShadow = true;
  scene.add(m);
}
