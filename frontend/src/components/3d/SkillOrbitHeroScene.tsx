import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { detectWebGLSupport } from '../../utils/webgl';
import { FastForward, Sparkles, Orbit, Cpu, ShieldAlert, FileCheck2, BarChart3, Radio } from 'lucide-react';

interface SkillOrbitHeroSceneProps {
  isIntroMode: boolean;
  onFinishIntro: () => void;
  className?: string;
}

export const SkillOrbitHeroScene: React.FC<SkillOrbitHeroSceneProps> = ({
  isIntroMode,
  onFinishIntro,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState<boolean>(true);
  const [introTransitioning, setIntroTransitioning] = useState<boolean>(false);
  const [introFinished, setIntroFinished] = useState<boolean>(!isIntroMode);

  // Mouse / Pointer Parallax State
  const mouseRef = useRef<{ x: number; y: number; targetX: number; targetY: number }>({
    x: 0,
    y: 0,
    targetX: 0,
    targetY: 0,
  });

  const handleSkip = useCallback(() => {
    setIntroTransitioning(true);
    setTimeout(() => {
      setIntroFinished(true);
      onFinishIntro();
    }, 600);
  }, [onFinishIntro]);

  useEffect(() => {
    const support = detectWebGLSupport();
    if (!support.supported) {
      setHasWebGL(false);
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    let width = container.clientWidth || window.innerWidth;
    let height = container.clientHeight || 550;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, isIntroMode ? 10.5 : 7.2);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, support.isLowPowerDevice ? 1.5 : 2));
    container.appendChild(renderer.domElement);

    // 2. Lights
    const coreLight = new THREE.PointLight(0x00f2fe, 4, 25);
    coreLight.position.set(0, 0, 0);
    scene.add(coreLight);

    const ambientLight = new THREE.AmbientLight(0x1e1b4b, 1.5);
    scene.add(ambientLight);

    const rimLight = new THREE.DirectionalLight(0x8b5cf6, 2.5);
    rimLight.position.set(5, 5, 4);
    scene.add(rimLight);

    // 3. Central Glowing Cyan Core
    const coreGroup = new THREE.Group();
    scene.add(coreGroup);

    const coreGeo = new THREE.SphereGeometry(0.75, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.95,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreGroup.add(coreMesh);

    // Core Outer Pulsing Shell
    const coreShellGeo = new THREE.SphereGeometry(0.95, 32, 32);
    const coreShellMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
    });
    const coreShellMesh = new THREE.Mesh(coreShellGeo, coreShellMat);
    coreGroup.add(coreShellMesh);

    // 4. Futuristic Wireframe Cube / Chip
    const cubeBoxGeo = new THREE.BoxGeometry(2.2, 2.2, 2.2);
    const cubeEdgesGeo = new THREE.EdgesGeometry(cubeBoxGeo);
    const cubeLineMat = new THREE.LineBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.75,
      linewidth: 1.5,
    });
    const cubeMesh = new THREE.LineSegments(cubeEdgesGeo, cubeLineMat);
    coreGroup.add(cubeMesh);

    // Concentric Inner Wireframe Box
    const innerBoxGeo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const innerEdgesGeo = new THREE.EdgesGeometry(innerBoxGeo);
    const innerLineMat = new THREE.LineBasicMaterial({
      color: 0x8b5cf6,
      transparent: true,
      opacity: 0.5,
    });
    const innerCubeMesh = new THREE.LineSegments(innerEdgesGeo, innerLineMat);
    coreGroup.add(innerCubeMesh);

    // Corner Micro-chips
    const cornerGeo = new THREE.BoxGeometry(0.18, 0.18, 0.18);
    const cornerMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    const cornerOffsets = [
      [1.1, 1.1, 1.1], [-1.1, 1.1, 1.1], [1.1, -1.1, 1.1], [-1.1, -1.1, 1.1],
      [1.1, 1.1, -1.1], [-1.1, 1.1, -1.1], [1.1, -1.1, -1.1], [-1.1, -1.1, -1.1],
    ];
    cornerOffsets.forEach(([cx, cy, cz]) => {
      const cMesh = new THREE.Mesh(cornerGeo, cornerMat);
      cMesh.position.set(cx, cy, cz);
      coreGroup.add(cMesh);
    });

    // 5. Tilted Elliptical Rings with Orbiting Particles
    const ringsGroup = new THREE.Group();
    scene.add(ringsGroup);

    // Cyan Particles Ring (Ring 1)
    const ring1Count = 120;
    const ring1Geo = new THREE.BufferGeometry();
    const ring1Pos = new Float32Array(ring1Count * 3);
    const ring1Angles = new Float32Array(ring1Count);

    const aX1 = 3.6;
    const bY1 = 1.9;

    for (let i = 0; i < ring1Count; i++) {
      ring1Angles[i] = (i / ring1Count) * Math.PI * 2;
      ring1Pos[i * 3] = Math.cos(ring1Angles[i]) * aX1;
      ring1Pos[i * 3 + 1] = Math.sin(ring1Angles[i]) * bY1;
      ring1Pos[i * 3 + 2] = 0;
    }
    ring1Geo.setAttribute('position', new THREE.BufferAttribute(ring1Pos, 3));
    const ring1Mat = new THREE.PointsMaterial({
      color: 0x00f2fe,
      size: 0.08,
      transparent: true,
      opacity: 0.85,
    });
    const ring1Points = new THREE.Points(ring1Geo, ring1Mat);
    ring1Points.rotation.x = Math.PI / 3.2;
    ring1Points.rotation.y = 0.25;
    ringsGroup.add(ring1Points);

    // Magenta Particles Ring (Ring 2)
    const ring2Count = 100;
    const ring2Geo = new THREE.BufferGeometry();
    const ring2Pos = new Float32Array(ring2Count * 3);
    const ring2Angles = new Float32Array(ring2Count);

    const aX2 = 4.2;
    const bY2 = 2.3;

    for (let i = 0; i < ring2Count; i++) {
      ring2Angles[i] = (i / ring2Count) * Math.PI * 2;
      ring2Pos[i * 3] = Math.cos(ring2Angles[i]) * aX2;
      ring2Pos[i * 3 + 1] = Math.sin(ring2Angles[i]) * bY2;
      ring2Pos[i * 3 + 2] = 0;
    }
    ring2Geo.setAttribute('position', new THREE.BufferAttribute(ring2Pos, 3));
    const ring2Mat = new THREE.PointsMaterial({
      color: 0xec4899, // Magenta
      size: 0.09,
      transparent: true,
      opacity: 0.8,
    });
    const ring2Points = new THREE.Points(ring2Geo, ring2Mat);
    ring2Points.rotation.x = -Math.PI / 3.8;
    ring2Points.rotation.y = -0.35;
    ringsGroup.add(ring2Points);

    // 6. Five Connected Adaptive Interview Intelligence Agent Nodes
    const agentsGroup = new THREE.Group();
    scene.add(agentsGroup);

    const agentConfigs = [
      { name: 'Planner Agent', color: 0x00f2fe, angle: 0 },
      { name: 'Adaptive Interviewer', color: 0x8b5cf6, angle: (Math.PI * 2) / 5 },
      { name: 'Answer Evaluator', color: 0x10b981, angle: (Math.PI * 4) / 5 },
      { name: 'Interview Integrity', color: 0xf59e0b, angle: (Math.PI * 6) / 5 },
      { name: 'Decision Intelligence', color: 0x38bdf8, angle: (Math.PI * 8) / 5 },
    ];

    const agentOrbitRadius = 3.2;
    const agentMeshes: THREE.Mesh[] = [];

    agentConfigs.forEach((cfg) => {
      const nodeGeo = new THREE.SphereGeometry(0.25, 20, 20);
      const nodeMat = new THREE.MeshBasicMaterial({
        color: cfg.color,
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);

      // Node halo ring
      const haloGeo = new THREE.RingGeometry(0.32, 0.38, 24);
      const haloMat = new THREE.MeshBasicMaterial({
        color: cfg.color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.7,
      });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      nodeMesh.add(haloMesh);

      const x = Math.cos(cfg.angle) * agentOrbitRadius;
      const y = Math.sin(cfg.angle) * agentOrbitRadius * 0.7;
      const z = Math.sin(cfg.angle * 2) * 0.5;
      nodeMesh.position.set(x, y, z);

      agentsGroup.add(nodeMesh);
      agentMeshes.push(nodeMesh);
    });

    // Constellation lines connecting the 5 agents to each other and to the core
    const connectionLinesCount = 5 + 5; // 5 to core + 5 between nodes
    const connPos = new Float32Array(connectionLinesCount * 2 * 3);
    const connGeo = new THREE.BufferGeometry();
    connGeo.setAttribute('position', new THREE.BufferAttribute(connPos, 3));
    const connMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.35,
    });
    const connectionLines = new THREE.LineSegments(connGeo, connMat);
    scene.add(connectionLines);

    // 7. Parallax & Mouse Listeners
    const handlePointerMove = (e: MouseEvent | TouchEvent) => {
      let clientX = 0;
      let clientY = 0;
      if ('touches' in e && e.touches.length > 0) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      } else if ('clientX' in e) {
        clientX = (e as MouseEvent).clientX;
        clientY = (e as MouseEvent).clientY;
      }

      const normX = (clientX / window.innerWidth) * 2 - 1;
      const normY = -(clientY / window.innerHeight) * 2 + 1;
      mouseRef.current.targetX = normX * 0.65;
      mouseRef.current.targetY = normY * 0.45;
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });
    window.addEventListener('touchmove', handlePointerMove, { passive: true });

    const handleWindowResize = () => {
      if (!container) return;
      width = container.clientWidth || window.innerWidth;
      height = container.clientHeight || 550;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', handleWindowResize);

    // 8. Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();
    let introStartTime = Date.now();
    const introDurationMs = 4500; // 4.5 seconds intro sequence

    const animate = () => {
      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      // Smooth camera parallax damping
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      // Intro camera zoom push-in
      if (!introFinished) {
        const introElapsed = Date.now() - introStartTime;
        const progress = Math.min(1, introElapsed / introDurationMs);
        camera.position.z = 10.5 - progress * 3.3; // Push from 10.5 to 7.2
        camera.position.x = mouseRef.current.x + Math.sin(elapsed * 0.5) * 0.2;
        camera.position.y = mouseRef.current.y + Math.cos(elapsed * 0.5) * 0.15;

        if (progress >= 1 && !introTransitioning) {
          handleSkip();
        }
      } else {
        camera.position.x = mouseRef.current.x;
        camera.position.y = mouseRef.current.y;
        camera.position.z = 7.2;
      }
      camera.lookAt(0, 0, 0);

      // Rotate Wireframe Cube and Core
      cubeMesh.rotation.x = elapsed * 0.35;
      cubeMesh.rotation.y = elapsed * 0.45;
      innerCubeMesh.rotation.x = -elapsed * 0.25;
      innerCubeMesh.rotation.y = -elapsed * 0.35;

      // Pulse Core Scale & Glow
      const corePulse = 1.0 + Math.sin(elapsed * 3.5) * 0.06;
      coreMesh.scale.set(corePulse, corePulse, corePulse);
      coreLight.intensity = 3.5 + Math.sin(elapsed * 4) * 0.8;

      // Animate Orbiting Particles on Rings
      const pPos1 = ring1Geo.attributes.position.array as Float32Array;
      for (let i = 0; i < ring1Count; i++) {
        ring1Angles[i] += delta * 0.6;
        pPos1[i * 3] = Math.cos(ring1Angles[i]) * aX1;
        pPos1[i * 3 + 1] = Math.sin(ring1Angles[i]) * bY1;
      }
      ring1Geo.attributes.position.needsUpdate = true;

      const pPos2 = ring2Geo.attributes.position.array as Float32Array;
      for (let i = 0; i < ring2Count; i++) {
        ring2Angles[i] -= delta * 0.5;
        pPos2[i * 3] = Math.cos(ring2Angles[i]) * aX2;
        pPos2[i * 3 + 1] = Math.sin(ring2Angles[i]) * bY2;
      }
      ring2Geo.attributes.position.needsUpdate = true;

      // Animate 5 Connected Agent Nodes Orbit
      const currentPositions: THREE.Vector3[] = [];
      agentMeshes.forEach((mesh, idx) => {
        const baseAngle = agentConfigs[idx].angle;
        const currentAngle = baseAngle + elapsed * 0.25;
        const x = Math.cos(currentAngle) * agentOrbitRadius;
        const y = Math.sin(currentAngle) * (agentOrbitRadius * 0.65);
        const z = Math.sin(currentAngle * 2) * 0.6;
        mesh.position.set(x, y, z);
        currentPositions.push(new THREE.Vector3(x, y, z));
      });

      // Update Connection Lines (Core-to-Agent + Agent-to-Agent ring)
      const linePositions = connGeo.attributes.position.array as Float32Array;
      let ptr = 0;

      // 5 lines from core (0,0,0) to each agent
      for (let i = 0; i < 5; i++) {
        const pos = currentPositions[i];
        linePositions[ptr++] = 0;
        linePositions[ptr++] = 0;
        linePositions[ptr++] = 0;
        linePositions[ptr++] = pos.x;
        linePositions[ptr++] = pos.y;
        linePositions[ptr++] = pos.z;
      }

      // 5 lines connecting adjacent agents
      for (let i = 0; i < 5; i++) {
        const p1 = currentPositions[i];
        const p2 = currentPositions[(i + 1) % 5];
        linePositions[ptr++] = p1.x;
        linePositions[ptr++] = p1.y;
        linePositions[ptr++] = p1.z;
        linePositions[ptr++] = p2.x;
        linePositions[ptr++] = p2.y;
        linePositions[ptr++] = p2.z;
      }
      connGeo.attributes.position.needsUpdate = true;

      // Pulsing connection opacity
      connMat.opacity = 0.25 + Math.sin(elapsed * 2.5) * 0.12;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('touchmove', handlePointerMove);
      window.removeEventListener('resize', handleWindowResize);

      if (container && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      // Clean disposal
      coreGeo.dispose();
      coreMat.dispose();
      coreShellGeo.dispose();
      coreShellMat.dispose();
      cubeBoxGeo.dispose();
      cubeEdgesGeo.dispose();
      cubeLineMat.dispose();
      innerBoxGeo.dispose();
      innerEdgesGeo.dispose();
      innerLineMat.dispose();
      cornerGeo.dispose();
      cornerMat.dispose();
      ring1Geo.dispose();
      ring1Mat.dispose();
      ring2Geo.dispose();
      ring2Mat.dispose();
      connGeo.dispose();
      connMat.dispose();
      renderer.dispose();
    };
  }, [handleSkip, introFinished, introTransitioning, isIntroMode]);

  // CSS Fallback if WebGL is disabled or unsupported
  if (!hasWebGL) {
    return (
      <div className={`relative w-full h-[420px] rounded-3xl bg-white border border-cyan-500/20 overflow-hidden flex flex-col items-center justify-center p-6 ${className}`}>
        {/* Hologram Rings */}
        <div className="absolute w-72 h-72 rounded-full border border-cyan-500/30 animate-spin-slow" />
        <div className="absolute w-84 h-48 rounded-full border border-violet-500/30 rotate-45" />

        {/* Central Core */}
        <div className="relative z-10 w-24 h-24 rounded-2xl border-2 border-cyan-400 bg-cyan-950/40 flex items-center justify-center shadow-glow-cyan animate-pulse">
          <div className="w-10 h-10 rounded-full bg-cyan-400 shadow-[0_0_20px_#00f2fe]" />
        </div>

        {/* 5 Agent Badges */}
        <div className="relative z-10 flex flex-wrap items-center justify-center gap-2 mt-8 text-[11px] font-mono">
          <span className="px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">1. Planner</span>
          <span className="px-2.5 py-1 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/40">2. Interviewer</span>
          <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">3. Evaluator</span>
          <span className="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">4. Integrity</span>
          <span className="px-2.5 py-1 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/40">5. Decision</span>
        </div>

        <div className="absolute bottom-4 text-xs font-mono text-slate-500">
          CSS Hologram Mode (WebGL Accelerated Fallback Active)
        </div>
      </div>
    );
  }

  return (
    <div className={`relative w-full overflow-hidden select-none ${className}`}>
      {/* 3D Canvas Mount Point */}
      <div
        ref={containerRef}
        className="w-full h-[460px] sm:h-[540px] lg:h-[600px] cursor-grab active:cursor-grabbing"
      />

      {/* Floating Skip Intro / Transition Controls */}
      {!introFinished && (
        <div className="absolute top-4 right-4 z-30">
          <button
            onClick={handleSkip}
            className="group flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#f4f3ee]/85 backdrop-blur-md border border-cyan-400/40 text-cyan-300 text-xs font-mono hover:bg-cyan-500/20 transition-all duration-300 shadow-glow-cyan"
          >
            <span>Skip Intro</span>
            <FastForward className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      )}

      {/* 5-Agent Interactive Badges Bar overlayed in Hero Scene */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-4xl px-4 pointer-events-none">
        <div className="flex flex-wrap items-center justify-center gap-2 bg-white/80 backdrop-blur-md p-2 rounded-2xl border border-slate-800 text-[11px] font-mono shadow-2xl">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>Agent 1: Planner</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-violet-500/15 text-violet-300 border border-violet-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
            <span>Agent 2: Adaptive</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Agent 3: Evaluator</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>Agent 4: Integrity</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/15 text-sky-300 border border-sky-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
            <span>Agent 5: Decision</span>
          </div>
        </div>
      </div>

      {/* Luminous Bloom Flare Transition Overlay */}
      {introTransitioning && (
        <div className="absolute inset-0 z-40 bg-gradient-to-t from-[#050814] via-cyan-400/10 to-white/20 pointer-events-none transition-opacity duration-700 opacity-90 animate-pulse" />
      )}
    </div>
  );
};
