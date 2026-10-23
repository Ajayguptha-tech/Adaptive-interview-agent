import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { AudioLines, BarChart3, FileText, MessageSquareText } from 'lucide-react';

function makeGlowTexture(): THREE.Texture {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext('2d');
  if (!context) {
    return new THREE.Texture();
  }
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.2, 'rgba(255,255,255,.72)');
  gradient.addColorStop(0.55, 'rgba(255,255,255,.2)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

function seededRandom(seed = 19) {
  let value = seed;
  return () => {
    value |= 0;
    value = (value + 0x6d2b79f5) | 0;
    let result = Math.imul(value ^ (value >>> 15), 1 | value);
    result = (result + Math.imul(result ^ (result >>> 7), 61 | result)) ^ result;
    return ((result ^ (result >>> 14)) >>> 0) / 4294967296;
  };
}

interface OrbitGroup {
  orbit: THREE.Group;
  speed: number;
  offset: number;
}

export default function IntelligenceVisual() {
  const visualRef = useRef<HTMLDivElement>(null);
  const mountRef = useRef<HTMLDivElement>(null);
  const parallaxRef = useRef({ x: 0, y: 0 });
  const [useFallback, setUseFallback] = useState(false);

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (
      event.pointerType !== 'mouse' ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
      !window.matchMedia('(pointer: fine)').matches
    ) {
      return;
    }

    if (!visualRef.current) return;
    const bounds = visualRef.current.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    parallaxRef.current = { x, y };
    visualRef.current.style.setProperty('--parallax-x', `${x * 9}px`);
    visualRef.current.style.setProperty('--parallax-y', `${y * 7}px`);
  };

  const resetParallax = () => {
    parallaxRef.current = { x: 0, y: 0 };
    if (visualRef.current) {
      visualRef.current.style.setProperty('--parallax-x', '0px');
      visualRef.current.style.setProperty('--parallax-y', '0px');
    }
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const compactQuery = window.matchMedia('(max-width: 700px)');
    const isCompact = compactQuery.matches;
    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: !isCompact,
        powerPreference: 'high-performance',
      });
    } catch {
      setUseFallback(true);
      return undefined;
    }

    setUseFallback(false);
    let isDisposed = false;
    let contextLost = false;
    let inView = true;
    let isRunning = false;
    let animationFrame = 0;
    let lastFrame = 0;

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isCompact ? 1.35 : 1.8));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.14;
    renderer.domElement.className = 'orb-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    camera.position.set(0, 0.05, 7.3);

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    const room = new RoomEnvironment();
    const environmentTarget = pmremGenerator.fromScene(room, 0.04);
    scene.environment = environmentTarget.texture;
    if (typeof (room as any).dispose === 'function') (room as any).dispose();
    pmremGenerator.dispose();

    scene.add(new THREE.HemisphereLight(0xf4faff, 0xc8c4e3, 2.15));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
    keyLight.position.set(4, 5, 6);
    scene.add(keyLight);
    const blueLight = new THREE.PointLight(0x8fd7ff, 13, 12);
    blueLight.position.set(-3.2, 2.1, 4);
    scene.add(blueLight);
    const violetLight = new THREE.PointLight(0xd2bcff, 11, 11);
    violetLight.position.set(3, -1.4, 3);
    scene.add(violetLight);

    const root = new THREE.Group();
    root.rotation.set(-0.08, -0.12, 0.06);
    scene.add(root);

    const sphereSegments = isCompact ? 56 : 88;
    const innerCoreMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xa9dcf5,
      roughness: 0.22,
      metalness: 0.02,
      transmission: 0.18,
      thickness: 0.9,
      transparent: true,
      opacity: 0.82,
      clearcoat: 1,
      clearcoatRoughness: 0.16,
      emissive: 0x82c7ed,
      emissiveIntensity: 0.08,
      envMapIntensity: 1.05,
    });
    const innerCore = new THREE.Mesh(
      new THREE.SphereGeometry(0.88, sphereSegments, sphereSegments),
      innerCoreMaterial,
    );
    root.add(innerCore);

    const coreMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xe7f7ff,
      roughness: 0.1,
      metalness: 0,
      transmission: 0.62,
      thickness: 1.25,
      transparent: true,
      opacity: 0.68,
      clearcoat: 1,
      clearcoatRoughness: 0.08,
      iridescence: 0.32,
      iridescenceIOR: 1.3,
      iridescenceThicknessRange: [120, 420],
      envMapIntensity: 1.2,
      depthWrite: false,
    });
    const core = new THREE.Mesh(new THREE.SphereGeometry(1.26, sphereSegments, sphereSegments), coreMaterial);
    core.renderOrder = 2;
    root.add(core);

    const rimMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uBlue: { value: new THREE.Color(0x79c9ef) },
        uViolet: { value: new THREE.Color(0xb6a1e5) },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vViewDirection;
        void main() {
          vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
          vNormal = normalize(normalMatrix * normal);
          vViewDirection = normalize(-viewPosition.xyz);
          gl_Position = projectionMatrix * viewPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 uBlue;
        uniform vec3 uViolet;
        varying vec3 vNormal;
        varying vec3 vViewDirection;
        void main() {
          float rim = pow(1.0 - max(dot(vNormal, vViewDirection), 0.0), 2.6);
          vec3 color = mix(uBlue, uViolet, clamp(vNormal.y * 0.5 + 0.5, 0.0, 1.0));
          gl_FragColor = vec4(color, rim * 0.46);
        }
      `,
      transparent: true,
      depthWrite: false,
    });
    const rim = new THREE.Mesh(new THREE.SphereGeometry(1.285, sphereSegments, sphereSegments), rimMaterial);
    rim.renderOrder = 3;
    root.add(rim);

    const glowTexture = makeGlowTexture();
    const orbitGroups: OrbitGroup[] = [];
    const ringConfigurations = [
      { radius: 1.63, color: 0x69b6ee, opacity: 0.6, rotation: [1.12, 0.15, 0.2] as [number, number, number], speed: 0.2, offset: 0.4 },
      { radius: 1.9, color: 0xab96df, opacity: 0.5, rotation: [0.65, 0.6, -0.45] as [number, number, number], speed: -0.14, offset: 2.2 },
      { radius: 2.13, color: 0x77cfc4, opacity: 0.4, rotation: [1.45, -0.25, 0.7] as [number, number, number], speed: 0.11, offset: 4.1 },
      { radius: 1.78, color: 0x94c8ed, opacity: 0.3, rotation: [0.15, 1.1, 0.1] as [number, number, number], speed: -0.17, offset: 5.4 },
    ];

    ringConfigurations.forEach((configuration, index) => {
      const ringGroup = new THREE.Group();
      ringGroup.rotation.set(configuration.rotation[0], configuration.rotation[1], configuration.rotation[2]);
      const orbit = new THREE.Group();
      orbit.rotation.z = configuration.offset;
      ringGroup.add(orbit);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(configuration.radius, index === 0 ? 0.011 : 0.008, 8, isCompact ? 144 : 220),
        new THREE.MeshBasicMaterial({
          color: configuration.color,
          transparent: true,
          opacity: configuration.opacity,
          depthWrite: false,
        }),
      );
      orbit.add(ring);

      const satelliteMaterial = new THREE.MeshPhysicalMaterial({
        color: configuration.color,
        roughness: 0.16,
        metalness: 0.03,
        clearcoat: 1,
        emissive: configuration.color,
        emissiveIntensity: 0.08,
      });
      const satelliteGeometry = index === 1
        ? new THREE.OctahedronGeometry(0.1, 0)
        : new THREE.SphereGeometry(index === 2 ? 0.052 : 0.064, 20, 20);
      const satellite = new THREE.Mesh(satelliteGeometry, satelliteMaterial);
      satellite.position.set(configuration.radius, 0, 0);
      orbit.add(satellite);

      const glow = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: glowTexture,
          color: configuration.color,
          transparent: true,
          opacity: 0.5,
          depthWrite: false,
        }),
      );
      glow.scale.setScalar(index === 1 ? 0.42 : 0.34);
      satellite.add(glow);

      if (index === 0 || index === 2) {
        const secondSatellite = satellite.clone();
        secondSatellite.position.set(-configuration.radius, 0, 0);
        secondSatellite.scale.setScalar(0.72);
        orbit.add(secondSatellite);
      }

      root.add(ringGroup);
      orbitGroups.push({ orbit, speed: configuration.speed, offset: configuration.offset });
    });

    const random = seededRandom();
    const particleCount = isCompact ? 58 : 105;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const particlePalette = [
      new THREE.Color(0x7db9e6),
      new THREE.Color(0xb29bdc),
      new THREE.Color(0x79cfc2),
    ];

    for (let index = 0; index < particleCount; index += 1) {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const radius = 1.75 + random() * 1.15;
      positions[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[index * 3 + 2] = radius * Math.cos(phi) * 0.65;
      const color = particlePalette[Math.floor(random() * particlePalette.length)];
      colors[index * 3] = color.r;
      colors[index * 3 + 1] = color.g;
      colors[index * 3 + 2] = color.b;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({
        size: 0.032,
        transparent: true,
        opacity: 0.55,
        vertexColors: true,
        sizeAttenuation: true,
        depthWrite: false,
      }),
    );
    root.add(particles);

    const renderScene = (time: number) => {
      const t = time * 0.001;
      const pointer = parallaxRef.current;
      root.rotation.y += (-0.12 + Math.sin(t * 0.22) * 0.1 + pointer.x * 0.13 - root.rotation.y) * 0.035;
      root.rotation.x += (-0.08 + Math.cos(t * 0.18) * 0.035 - pointer.y * 0.1 - root.rotation.x) * 0.035;
      innerCore.rotation.y = t * 0.08;
      innerCore.rotation.x = t * 0.035;
      const pulse = 1 + Math.sin(t * 0.85) * 0.014;
      innerCore.scale.setScalar(pulse);
      core.rotation.y = -t * 0.025;
      particles.rotation.y = t * 0.026;
      particles.rotation.z = -t * 0.012;
      orbitGroups.forEach(({ orbit, speed, offset }) => {
        orbit.rotation.z = offset + t * speed;
      });
      renderer.render(scene, camera);
    };

    const animate = (time: number) => {
      if (!isRunning) return;
      if (!isCompact || time - lastFrame >= 1000 / 45) {
        renderScene(time);
        lastFrame = time;
      }
      animationFrame = window.requestAnimationFrame(animate);
    };

    const updatePlayback = () => {
      const shouldAnimate = !isDisposed && !contextLost && !reducedMotionQuery.matches && inView && !document.hidden;
      if (shouldAnimate && !isRunning) {
        isRunning = true;
        animationFrame = window.requestAnimationFrame(animate);
      } else if (!shouldAnimate && isRunning) {
        isRunning = false;
        window.cancelAnimationFrame(animationFrame);
      }
      if (reducedMotionQuery.matches && !contextLost) {
        renderScene(1400);
      }
    };

    const resize = () => {
      if (!mount) return;
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderScene(performance.now());
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);
    resize();

    const intersectionObserver = new IntersectionObserver(
      ([entry]) => {
        inView = entry.isIntersecting;
        updatePlayback();
      },
      { threshold: 0.02 },
    );
    intersectionObserver.observe(mount);

    const handleVisibility = () => updatePlayback();
    const handleMotionPreference = () => updatePlayback();
    const handleContextLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      setUseFallback(true);
      updatePlayback();
    };
    const handleContextRestored = () => {
      contextLost = false;
      setUseFallback(false);
      resize();
      updatePlayback();
    };

    document.addEventListener('visibilitychange', handleVisibility);
    reducedMotionQuery.addEventListener('change', handleMotionPreference);
    renderer.domElement.addEventListener('webglcontextlost', handleContextLost);
    renderer.domElement.addEventListener('webglcontextrestored', handleContextRestored);
    updatePlayback();

    return () => {
      isDisposed = true;
      isRunning = false;
      window.cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      document.removeEventListener('visibilitychange', handleVisibility);
      reducedMotionQuery.removeEventListener('change', handleMotionPreference);
      renderer.domElement.removeEventListener('webglcontextlost', handleContextLost);
      renderer.domElement.removeEventListener('webglcontextrestored', handleContextRestored);

      const geometries = new Set<THREE.BufferGeometry>();
      const materials = new Set<THREE.Material>();
      scene.traverse((object: any) => {
        if (object.geometry) geometries.add(object.geometry);
        if (object.material) {
          const objectMaterials = Array.isArray(object.material) ? object.material : [object.material];
          objectMaterials.forEach((material: THREE.Material) => materials.add(material));
        }
      });
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      glowTexture.dispose();
      environmentTarget.dispose();
      renderer.dispose();
      if (mount && mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={visualRef}
      className="intelligence-visual"
      onPointerMove={handlePointerMove}
      onPointerLeave={resetParallax}
      role="img"
      aria-label="An animated intelligence orb with orbital rings and floating elements for resume analysis, question generation, voice interaction, and performance evaluation."
    >
      <div className="visual-aura" aria-hidden="true" />
      <div className="visual-grid" aria-hidden="true" />
      <div className="orb-shadow" aria-hidden="true" />
      <div ref={mountRef} className="orb-mount" aria-hidden="true" />
      {useFallback && (
        <div className="orb-fallback" aria-hidden="true">
          <div className="fallback-core" />
          <span className="fallback-ring fallback-ring-one" />
          <span className="fallback-ring fallback-ring-two" />
          <span className="fallback-ring fallback-ring-three" />
          <span className="fallback-satellite fallback-satellite-one" />
          <span className="fallback-satellite fallback-satellite-two" />
        </div>
      )}

      <div className="glass-chip-wrap chip-resume" aria-hidden="true">
        <div className="glass-chip">
          <span className="chip-icon chip-icon-blue"><FileText size={18} strokeWidth={1.7} /></span>
          <span className="chip-copy"><strong>Resume analysis</strong><span>Skills & experience</span></span>
          <span className="chip-check"><span /></span>
        </div>
      </div>
      <div className="glass-chip-wrap chip-question" aria-hidden="true">
        <div className="glass-chip">
          <span className="chip-icon chip-icon-violet"><MessageSquareText size={18} strokeWidth={1.7} /></span>
          <span className="chip-copy"><strong>Question generation</strong><span>Personalized prompts</span></span>
        </div>
      </div>
      <div className="glass-chip-wrap chip-voice" aria-hidden="true">
        <div className="glass-chip">
          <span className="chip-icon chip-icon-mint"><AudioLines size={18} strokeWidth={1.7} /></span>
          <span className="chip-copy">
            <strong>Voice interaction</strong>
            <span className="voice-wave"><i /><i /><i /><i /><i /></span>
          </span>
        </div>
      </div>
      <div className="glass-chip-wrap chip-insight" aria-hidden="true">
        <div className="glass-chip">
          <span className="chip-icon chip-icon-cyan"><BarChart3 size={18} strokeWidth={1.7} /></span>
          <span className="chip-copy"><strong>Performance evaluation</strong><span>Clear, focused feedback</span></span>
        </div>
      </div>
      <span className="visual-spark visual-spark-one" aria-hidden="true" />
      <span className="visual-spark visual-spark-two" aria-hidden="true" />
      <span className="visual-spark visual-spark-three" aria-hidden="true" />
    </div>
  );
}
