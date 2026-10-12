import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { detectWebGLSupport } from '../../utils/webgl';

export const MiniGlassOrb: React.FC<{ className?: string }> = ({ className = '' }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    const support = detectWebGLSupport();
    if (!support.supported) {
      setHasWebGL(false);
      return;
    }

    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 56;
    const height = container.clientHeight || 56;

    // Three.js Scene
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 3.2;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'low-power',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Glass Orb Outer Sphere
    const orbGeometry = new THREE.SphereGeometry(0.9, 32, 32);
    const orbMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x00f2fe,
      metalness: 0.1,
      roughness: 0.1,
      transmission: 0.85,
      thickness: 0.8,
      transparent: true,
      opacity: 0.9,
      emissive: 0x003344,
    });
    const orbMesh = new THREE.Mesh(orbGeometry, orbMaterial);
    scene.add(orbMesh);

    // Glowing Inner Core
    const coreGeometry = new THREE.SphereGeometry(0.35, 16, 16);
    const coreMaterial = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
    });
    const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(coreMesh);

    // Light
    const pointLight = new THREE.PointLight(0x00f2fe, 2, 10);
    pointLight.position.set(1.5, 2, 2);
    scene.add(pointLight);

    const ambientLight = new THREE.AmbientLight(0x38bdf8, 1);
    scene.add(ambientLight);

    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      orbMesh.rotation.y = elapsed * 0.8;
      orbMesh.rotation.x = Math.sin(elapsed * 0.5) * 0.2;

      const scalePulse = 0.35 + Math.sin(elapsed * 2.5) * 0.05;
      coreMesh.scale.set(scalePulse, scalePulse, scalePulse);

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      orbGeometry.dispose();
      orbMaterial.dispose();
      coreGeometry.dispose();
      coreMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  if (!hasWebGL) {
    return (
      <div className={`relative w-12 h-12 rounded-full bg-gradient-to-tr from-cyan-500/30 to-violet-500/20 border border-cyan-400/40 shadow-glow-cyan flex items-center justify-center ${className}`}>
        <div className="w-4 h-4 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_12px_#00f2fe]" />
      </div>
    );
  }

  return (
    <div
      ref={mountRef}
      className={`w-12 h-12 sm:w-14 sm:h-14 inline-block align-middle cursor-pointer transition-transform hover:scale-110 drop-shadow-[0_0_15px_rgba(0,242,254,0.5)] ${className}`}
      title="Adaptive Interview Intelligence Neural Core"
    />
  );
};
