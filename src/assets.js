import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const MODELS = [
  'grinny', 'hornman', 'horse', 'director',
  'booth', 'arch', 'carousel', 'lamp', 'bench', 'fence', 'trash', 'crate', 'balloon_cart', 'popcorn',
  'fuse', 'fusebox', 'battery', 'cassette', 'keycard', 'generator', 'receiver', 'lever', 'gate_handle',
  'coaster_gate', 'coaster_track', 'coaster_support', 'coaster_car', 'ferris', 'funhouse', 'staff_door',
  'jackbox', 'deadtree', 'plush_pile', 'bridge',
  'circus_tent', 'bumper_arena', 'bumper_car', 'teacups', 'cotton_candy', 'striker', 'billboard', 'signpost',
  'mapboard', 'trashbags', 'turnstile', 'circus_wagon', 'stall_tent', 'coaster_hill',
  'clawpack_full', 'clawhands',
];

const CH2_ZONES = ['zone_a_entry', 'zone_b_lockers', 'zone_c_sewing', 'zone_d_packing', 'zone_e_warehouse', 'zone_f_core', 'zone_seams'];

/** Chapter 2: the underground factory chunks plus the few props and creatures it needs. */
export const CH2_MODELS = [
  ...CH2_ZONES.map((z) => `ch2/${z}`),
  'seamstress', 'giggler', 'joy_jar', 'name_tag', 'director',
  'battery', 'cassette', 'lever', 'clawpack_full', 'clawhands',
];

// already authored dark and worn for the factory: keep their materials as they are
const KEEP_MATERIALS = new Set([...CH2_ZONES.map((z) => `ch2/${z}`), 'seamstress', 'giggler', 'joy_jar', 'name_tag', 'director']);

const cache = {};

/**
 * Blender bakes per-material surface data into vertex colour "Surf":
 * R = roughness, G = metalness, B = emission mask. Feed it into the standard shader.
 */
function upgradeMaterial(mat) {
  mat.vertexColors = false;
  mat.userData.emit = { value: 1.0 };
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uEmit = mat.userData.emit;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec4 surf;\nvarying vec4 vSurf;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvSurf = surf;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec4 vSurf;\nuniform float uEmit;')
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = clamp(vSurf.r, 0.06, 1.0);')
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = vSurf.g * 0.85;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * vSurf.b * uEmit * 1.6;');
  };
  mat.customProgramCacheKey = () => 'surf';
}

function prepare(root, keepMaterials = false) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    const g = o.geometry;
    // models authored with real PBR materials (no baked "Surf" colour) keep them untouched
    if (!g.attributes.color && !g.attributes.surf) {
      const m = o.material;
      if (!m.userData.weathered && !keepMaterials) {
        // studio-clean product materials: tone down to sit in the grimy, flashlight-lit park
        m.userData.weathered = true;
        m.color.multiplyScalar(m.metalness > 0.6 ? 0.4 : 0.5);
        m.roughness = Math.min(1, m.roughness + 0.3);
        m.metalness *= 0.75;
      }
      if (m.map) m.map.anisotropy = 4;
      return;
    }
    if (g.attributes.color && !g.attributes.surf) {
      g.setAttribute('surf', g.attributes.color);
      g.deleteAttribute('color');
    }
    if (o.material.map) o.material.map.anisotropy = 4;
    upgradeMaterial(o.material);
  });
}

export async function loadAll(onProgress, names = MODELS) {
  const loader = new GLTFLoader();
  let done = 0;
  await Promise.all(names.map(async (name) => {
    const gltf = await loader.loadAsync(`${import.meta.env.BASE_URL}models/${name}.glb`);
    prepare(gltf.scene, KEEP_MATERIALS.has(name));
    cache[name] = gltf;
    done++;
    onProgress?.(done / names.length);
  }));
}

/** JSON data that ships next to the models (zone colliders, lights, markers). */
export async function loadJSON(path) {
  const r = await fetch(`${import.meta.env.BASE_URL}models/${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

/** Fresh instance of a model. Materials are shared unless `uniqueMaterials` is set. */
export function spawn(name, { uniqueMaterials = false } = {}) {
  const gltf = cache[name];
  if (!gltf) throw new Error('model not loaded: ' + name);
  const obj = SkeletonUtils.clone(gltf.scene);
  if (uniqueMaterials) {
    obj.traverse((o) => {
      if (o.isMesh) {
        const src = o.material;
        o.material = src.clone();
        if (o.geometry.attributes.surf) upgradeMaterial(o.material);
      }
    });
  }
  obj.userData.animations = gltf.animations;
  return obj;
}

/** Animation mixer for a spawned model; play(name, {once}) crossfades to one of its clips. */
export function animator(obj) {
  const mixer = new THREE.AnimationMixer(obj);
  const acts = Object.fromEntries((obj.userData.animations || []).map((c) => [c.name, mixer.clipAction(c)]));
  let current = null;
  return {
    mixer,
    play(name, { once = false, fade = 0.3 } = {}) {
      const a = acts[name];
      if (!a) return;
      a.reset().setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
      a.clampWhenFinished = once;
      a.fadeIn(fade).play();
      if (current && current !== a) current.fadeOut(fade);
      current = a;
    },
  };
}

export function part(obj, name) {
  return obj.getObjectByName(name);
}

/** Set the emissive strength for every mesh in an object (needs uniqueMaterials for per-instance). */
export function setEmit(obj, value) {
  obj.traverse((o) => { if (o.isMesh && o.material.userData.emit) o.material.userData.emit.value = value; });
}

export function tint(obj, color) {
  obj.traverse((o) => { if (o.isMesh) o.material.color.set(color); });
}
