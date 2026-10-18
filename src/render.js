import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const VHS = {
  uniforms: {
    tDiffuse: { value: null },
    time: { value: 0 },
    grain: { value: 0.06 },
    aberration: { value: 0.0015 },
    red: { value: 0 },
    fade: { value: 0 },
    warp: { value: 0 },
    tracking: { value: 0.15 },
    pulse: { value: 0 },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float time, grain, aberration, red, fade, warp, tracking, pulse;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
      vec2 uv = vUv;
      // tape wobble + tracking band
      float band = smoothstep(0.0, 0.02, abs(fract(uv.y * 0.5 - time * 0.07) - 0.5) - 0.47);
      uv.x += (hash(vec2(floor(uv.y * 240.0), floor(time * 30.0))) - 0.5) * 0.004 * tracking * (1.0 - band) * 6.0;
      uv.x += sin(uv.y * 30.0 + time * 3.0) * 0.0008 * (1.0 + warp * 8.0);
      // heartbeat pulse zooms slightly
      vec2 c = uv - 0.5; uv = 0.5 + c * (1.0 - pulse * 0.015);
      float ab = aberration * (1.0 + warp * 6.0) + length(c) * 0.002;
      vec3 col;
      col.r = texture2D(tDiffuse, uv + vec2(ab, 0.0)).r;
      col.g = texture2D(tDiffuse, uv).g;
      col.b = texture2D(tDiffuse, uv - vec2(ab, 0.0)).b;
      // scanlines and grain
      col *= 0.92 + 0.08 * sin(vUv.y * 900.0);
      col += (hash(vUv * vec2(1931.0, 917.0) + time) - 0.5) * grain;
      // vignette (tightens with danger)
      float v = smoothstep(0.85 - pulse * 0.15, 0.25, length(c * vec2(1.1, 1.0)));
      col *= mix(0.25, 1.0, v);
      // desaturate + slight green/teal tape cast
      float l = dot(col, vec3(0.299, 0.587, 0.114));
      col = mix(vec3(l), col, 0.72) * vec3(0.96, 1.0, 0.98);
      col = mix(col, vec3(l * 1.4, l * 0.15, l * 0.1) + vec3(0.25, 0.0, 0.0), red);
      col *= 1.0 - fade;
      gl_FragColor = vec4(col, 1.0);
    }`,
};

export class Renderer {
  constructor(canvas) {
    const r = (this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' }));
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.15;
    r.outputColorSpace = THREE.SRGBColorSpace;
    this.scale = 0.6; // render below native resolution for the PS1/VHS look
    this.camera = new THREE.PerspectiveCamera(72, 1, 0.05, 85);
    this.scene = new THREE.Scene();
    this.composer = new EffectComposer(r);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.vhs = new ShaderPass(VHS);
    this.composer.addPass(this.vhs);
    this.composer.addPass(new OutputPass());
    this.u = this.vhs.uniforms;
    this.resize();
    addEventListener('resize', () => this.resize());
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    const pr = Math.min(devicePixelRatio, 2) * this.scale;
    this.renderer.setPixelRatio(pr);
    this.renderer.setSize(w, h, false);
    this.composer.setPixelRatio(pr);
    this.composer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  /** low | mid | high: internal resolution and shadow quality. */
  setQuality(q, flashlight) {
    this.scale = { low: 0.45, mid: 0.6, high: 0.8 }[q] ?? 0.6;
    const shadows = q !== 'low';
    if (this.renderer.shadowMap.enabled !== shadows) {
      this.renderer.shadowMap.enabled = shadows;
      this.scene.traverse((o) => { if (o.material) [].concat(o.material).forEach((m) => (m.needsUpdate = true)); });
    }
    if (flashlight) {
      flashlight.castShadow = shadows;
      const size = q === 'high' ? 1024 : 512;
      if (flashlight.shadow.mapSize.x !== size) {
        flashlight.shadow.mapSize.set(size, size);
        flashlight.shadow.map?.dispose(); flashlight.shadow.map = null;
      }
    }
    this.resize();
  }

  render(time) {
    this.u.time.value = time;
    this.composer.render();
  }
}
