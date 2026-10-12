/**
 * Adaptive Interview Intelligence — 3D Interactive Orbit & Effects Engine
 * Reuses Three.js Orbit Scene, Harmonic Sine Wave Canvas, and 3D Tilt Physics
 */

import * as THREE from '/static/three.module.js';

// --- 1. THREE.JS 3D ORBIT SCENE ---
export function initOrbit3DScene() {
  const container = document.getElementById('hero-3d-stage');
  if (!container) return;

  // WebGL Availability Check
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) {
    console.info('[3D] WebGL not supported, falling back to CSS hologram.');
    return;
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const width = container.clientWidth || 380;
  const height = container.clientHeight || 280;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
  camera.position.set(0, 0, 9);

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
  keyLight.position.set(4, 5, 6);
  scene.add(keyLight);

  const limePointLight = new THREE.PointLight(0xc6ee2e, 2.5, 10);
  limePointLight.position.set(0, 0, 0);
  scene.add(limePointLight);

  const system = new THREE.Group();
  scene.add(system);

  // Core Solid: Glossy Charcoal Sphere with Clearcoat
  const coreGeo = new THREE.SphereGeometry(0.85, 48, 48);
  const coreMat = new THREE.MeshPhysicalMaterial({
    color: 0x1b1c17,
    metalness: 0.5,
    roughness: 0.2,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
  });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  system.add(coreMesh);

  // Emissive Lime Equator Band
  const bandGeo = new THREE.TorusGeometry(0.92, 0.028, 16, 96);
  const bandMat = new THREE.MeshStandardMaterial({
    color: 0xc6ee2e,
    emissive: 0xc6ee2e,
    emissiveIntensity: 0.8,
  });
  const bandMesh = new THREE.Mesh(bandGeo, bandMat);
  bandMesh.rotation.x = Math.PI / 2;
  system.add(bandMesh);

  // Wireframe Outer Shell (Concentric Icosahedron)
  const shellGeo = new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.15, 2));
  const shellMat = new THREE.LineBasicMaterial({
    color: 0xc6ee2e,
    transparent: true,
    opacity: 0.55,
  });
  const shellMesh = new THREE.LineSegments(shellGeo, shellMat);
  system.add(shellMesh);

  // Tilted Orbit Plane & 3 Guide Rings
  const orbitGroup = new THREE.Group();
  orbitGroup.rotation.set(0.5, 0, -0.25);
  system.add(orbitGroup);

  [2.0, 2.7, 3.4].forEach((radius, idx) => {
    const pts = [];
    const segments = 96;
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(theta) * radius, 0, Math.sin(theta) * radius));
    }
    const ringGeo = new THREE.BufferGeometry().setFromPoints(pts);
    const ringMat = new THREE.LineBasicMaterial({
      color: 0xc6ee2e,
      transparent: true,
      opacity: 0.28 - idx * 0.07,
    });
    orbitGroup.add(new THREE.Line(ringGeo, ringMat));
  });

  // 5 Floating Agent Solid Geometries
  // 1: Icosahedron (Planner)
  // 2: Torus Knot (Interviewer)
  // 3: Octahedron (Evaluator)
  // 4: Torus (Integrity)
  // 5: Dodecahedron (Decision)
  const agentSolids = [];
  const geos = [
    new THREE.IcosahedronGeometry(0.24, 0),
    new THREE.TorusKnotGeometry(0.16, 0.05, 48, 8),
    new THREE.OctahedronGeometry(0.26, 0),
    new THREE.TorusGeometry(0.18, 0.05, 12, 24),
    new THREE.DodecahedronGeometry(0.24, 0),
  ];
  const orbitRadii = [2.0, 2.7, 2.0, 3.4, 2.7];
  const speeds = [0.8, -0.6, 1.1, -0.5, 0.7];

  geos.forEach((geo, i) => {
    const mat = new THREE.MeshPhysicalMaterial({
      color: 0xc6ee2e,
      roughness: 0.25,
      metalness: 0.2,
      clearcoat: 1.0,
      emissive: 0xc6ee2e,
      emissiveIntensity: 0.15,
    });
    const mesh = new THREE.Mesh(geo, mat);
    orbitGroup.add(mesh);
    agentSolids.push({
      mesh,
      radius: orbitRadii[i],
      speed: speeds[i],
      angle: (i / geos.length) * Math.PI * 2,
    });
  });

  // Mouse Parallax
  const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  const onPointerMove = (e) => {
    if (reduceMotion) return;
    const rect = container.getBoundingClientRect();
    mouse.targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 1.5;
    mouse.targetY = -((e.clientY - rect.top) / rect.height - 0.5) * 1.2;
  };
  window.addEventListener('pointermove', onPointerMove);

  // Resize handler
  const onResize = () => {
    const w = container.clientWidth || 380;
    const h = container.clientHeight || 280;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };
  window.addEventListener('resize', onResize);

  // Animation Loop
  let reqId;
  const clock = new THREE.Clock();

  function animate() {
    reqId = requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const time = clock.getElapsedTime();

    if (!reduceMotion) {
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;
      system.rotation.y = time * 0.25 + mouse.x * 0.6;
      system.rotation.x = 0.15 + mouse.y * 0.5;
      shellMesh.rotation.y -= delta * 0.35;
      shellMesh.rotation.z += delta * 0.18;
    }

    // Orbit the 5 agent nodes
    agentSolids.forEach((item) => {
      item.angle += item.speed * delta * (reduceMotion ? 0 : 1);
      item.mesh.position.set(
        Math.cos(item.angle) * item.radius,
        Math.sin(item.angle * 2) * 0.15,
        Math.sin(item.angle) * item.radius
      );
      item.mesh.rotation.x += delta * 0.8;
      item.mesh.rotation.y += delta * 1.0;
    });

    renderer.render(scene, camera);
  }

  animate();
}

// --- 2. HARMONIC SINE-WAVE RIBBON CANVAS ---
export function initHarmonicSineWave() {
  const canvas = document.getElementById('sine-wave-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  let step = 0;
  function draw() {
    step += 0.015;
    ctx.clearRect(0, 0, width, height);

    // Wave 1: Electric Lime
    ctx.beginPath();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(198, 238, 46, 0.08)';
    for (let x = 0; x < width; x += 10) {
      const y = Math.sin(x * 0.003 + step) * 60 + Math.cos(x * 0.0015 - step * 0.5) * 30 + height * 0.45;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Wave 2: Cyan Ambient
    ctx.beginPath();
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = 'rgba(0, 242, 254, 0.06)';
    for (let x = 0; x < width; x += 10) {
      const y = Math.sin(x * 0.0025 - step * 0.8) * 50 + Math.cos(x * 0.002 + step * 0.3) * 40 + height * 0.52;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    requestAnimationFrame(draw);
  }

  draw();
}

// --- 3. 3D CARD TILT PHYSICS (Pointer-driven perspective) ---
export function initCardTiltPhysics() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  const tiltCards = document.querySelectorAll(
    '.hero-card, .profile-summary-card, .eligibility-card, .config-card, .question-card, .feedback-card, .report-card, .score-circle'
  );

  tiltCards.forEach((card) => {
    card.classList.add('tilt-interactive');
    card.addEventListener('pointermove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `perspective(900px) rotateX(${-y * 5}deg) rotateY(${x * 5}deg) translateZ(4px)`;
    });

    card.addEventListener('pointerleave', () => {
      card.style.transform = '';
    });
  });
}

// Auto-run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initOrbit3DScene();
    initHarmonicSineWave();
    initCardTiltPhysics();
  });
} else {
  initOrbit3DScene();
  initHarmonicSineWave();
  initCardTiltPhysics();
}
