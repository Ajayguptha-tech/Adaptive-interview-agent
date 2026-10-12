import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { detectWebGLSupport } from '../../utils/webgl';

/** Shared with the page: which agent (0-4) is highlighted, or -1 for none. */
export const sceneState = { focus: -1 };

const LIME = 0xc6ee2e;
const CHAR = 0x1b1c17;

/** Where the system sits while a `data-stage` section is under the viewport centre line. */
const STAGES: Record<string, { x: number; s: number }> = {
  right: { x: 2.7, s: 1 },
  left: { x: -2.7, s: 1 },
  center: { x: 0, s: 0.6 },
};

const AGENT_GEOS: (() => THREE.BufferGeometry)[] = [
  () => new THREE.IcosahedronGeometry(0.36, 0), // Planner
  () => new THREE.TorusKnotGeometry(0.22, 0.075, 96, 14), // Interviewer
  () => new THREE.OctahedronGeometry(0.4, 0), // Evaluator
  () => new THREE.TorusGeometry(0.28, 0.09, 16, 40), // Integrity
  () => new THREE.DodecahedronGeometry(0.36, 0), // Decision
];
const RADII = [2.4, 3.2, 2.4, 4.0, 3.2];

export const OrbitScene: React.FC = () => {
  const hostRef = useRef<HTMLDivElement>(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const support = detectWebGLSupport();
    if (!support.supported) { setFallback(true); return; }
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const disposables: { dispose(): void }[] = [];
    const own = <T extends { dispose(): void }>(o: T): T => { disposables.push(o); return o; };

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, support.isLowPowerDevice ? 1.5 : 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = envTex;
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.z = 11;
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(4, 5, 6);
    scene.add(key);

    const sys = new THREE.Group();
    scene.add(sys);

    // Candidate core: glossy charcoal sphere, lime band, lime wire shell
    const core = new THREE.Mesh(
      own(new THREE.SphereGeometry(0.95, 64, 64)),
      own(new THREE.MeshPhysicalMaterial({ color: CHAR, metalness: 0.5, roughness: 0.2, clearcoat: 1, clearcoatRoughness: 0.1 })),
    );
    sys.add(core);
    const shell = new THREE.LineSegments(
      own(new THREE.WireframeGeometry(own(new THREE.IcosahedronGeometry(1.25, 2)))),
      own(new THREE.LineBasicMaterial({ color: LIME, transparent: true, opacity: 0.6 })),
    );
    sys.add(shell);
    const band = new THREE.Mesh(
      own(new THREE.TorusGeometry(1.03, 0.03, 12, 96)),
      own(new THREE.MeshStandardMaterial({ color: LIME, emissive: LIME, emissiveIntensity: 0.6 })),
    );
    band.rotation.x = Math.PI / 2;
    sys.add(band);

    // Tilted orbit plane with three guide rings
    const orbit = new THREE.Group();
    orbit.rotation.set(0.5, 0, -0.28);
    sys.add(orbit);
    [2.4, 3.2, 4.0].forEach((r, i) => {
      const pts: THREE.Vector3[] = [];
      for (let k = 0; k <= 128; k++) {
        const a = (k / 128) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
      }
      orbit.add(new THREE.Line(
        own(new THREE.BufferGeometry().setFromPoints(pts)),
        own(new THREE.LineBasicMaterial({ color: CHAR, transparent: true, opacity: 0.22 - i * 0.05 })),
      ));
    });

    // Five agent solids
    const nodes = AGENT_GEOS.map((mk, i) => {
      const g = own(mk());
      const mat = own(new THREE.MeshPhysicalMaterial({ color: LIME, roughness: 0.25, metalness: 0.1, clearcoat: 1, emissive: LIME, emissiveIntensity: 0 }));
      const m = new THREE.Mesh(g, mat);
      if (i !== 1 && i !== 3) {
        m.add(new THREE.LineSegments(own(new THREE.EdgesGeometry(g)), own(new THREE.LineBasicMaterial({ color: CHAR }))));
      }
      orbit.add(m);
      return m;
    });

    // Links from each agent to the core, plus lime "evidence" pulses travelling inward
    const linkPos = new Float32Array(5 * 2 * 3);
    const linkGeo = own(new THREE.BufferGeometry());
    linkGeo.setAttribute('position', new THREE.BufferAttribute(linkPos, 3));
    orbit.add(new THREE.LineSegments(linkGeo, own(new THREE.LineBasicMaterial({ color: CHAR, transparent: true, opacity: 0.3 }))));
    const pulseGeo = own(new THREE.SphereGeometry(0.07, 12, 12));
    const pulseMat = own(new THREE.MeshBasicMaterial({ color: LIME }));
    const pulses = nodes.map(() => { const p = new THREE.Mesh(pulseGeo, pulseMat); orbit.add(p); return p; });

    // Dust
    const dustPos = new Float32Array(360 * 3);
    for (let i = 0; i < 360; i++) {
      const r = 5 + Math.random() * 5, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      dustPos.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)], i * 3);
    }
    const dustGeo = own(new THREE.BufferGeometry());
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dust = new THREE.Points(dustGeo, own(new THREE.PointsMaterial({ color: CHAR, size: 0.035, transparent: true, opacity: 0.45 })));
    scene.add(dust);

    // Input + layout
    const pointer = { x: 0, y: 0 };
    const onPointer = (e: PointerEvent) => {
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.y = -((e.clientY / window.innerHeight) * 2 - 1);
    };
    let narrow = false;
    const onResize = () => {
      const w = window.innerWidth, h = window.innerHeight;
      narrow = w < 900;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    if (!reduce) window.addEventListener('pointermove', onPointer, { passive: true });
    window.addEventListener('resize', onResize);
    onResize();

    let stage = 'right';
    let boost = 0;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        const next = e.target.getAttribute('data-stage');
        if (e.isIntersecting && next && next !== stage) { stage = next; boost = reduce ? 0 : 2.5; }
      });
    }, { rootMargin: '-50% 0px -50% 0px' });
    document.querySelectorAll('[data-stage]').forEach((el) => io.observe(el));

    const cur = { x: STAGES.right.x, y: 0, s: 1 };
    const clock = new THREE.Clock();
    let t = 0, spin = 0, raf = 0;
    const tmp = new THREE.Vector3();

    const loop = () => {
      raf = requestAnimationFrame(loop);
      if (document.hidden) return;
      const dt = Math.min(clock.getDelta(), 0.05);
      if (!reduce) t += dt;
      const k = 1 - Math.exp(-dt * 3);
      const st = STAGES[stage] ?? STAGES.right;
      cur.x += ((narrow ? 0 : st.x) - cur.x) * k;
      cur.y += ((narrow ? 1.9 : 0) - cur.y) * k;
      cur.s += ((narrow ? st.s * 0.7 : st.s) - cur.s) * k;
      boost *= Math.exp(-dt * 1.5);
      spin += dt * (0.15 + boost);

      sys.position.set(cur.x, cur.y, 0);
      sys.scale.setScalar(cur.s);
      sys.rotation.y = spin;
      sys.rotation.x += (pointer.y * 0.25 - sys.rotation.x) * k;
      camera.position.x += (pointer.x * 0.6 - camera.position.x) * k;
      camera.lookAt(0, 0, 0);
      shell.rotation.set(t * 0.2, t * 0.3, 0);
      core.rotation.y = -t * 0.4;
      dust.rotation.y = t * 0.02;

      nodes.forEach((m, i) => {
        const a = t * (0.35 - i * 0.03) + (i * Math.PI * 2) / 5;
        m.position.set(Math.cos(a) * RADII[i], Math.sin(t + i) * 0.25, Math.sin(a) * RADII[i]);
        m.rotation.set(t * 0.6 + i, t * 0.4, 0);
        const on = sceneState.focus === i;
        m.scale.setScalar(m.scale.x + ((on ? 1.7 : 1) - m.scale.x) * k);
        const mat = m.material as THREE.MeshPhysicalMaterial;
        mat.emissiveIntensity += ((on ? 0.7 : 0) - mat.emissiveIntensity) * k;

        linkPos.set([0, 0, 0, m.position.x, m.position.y, m.position.z], i * 6);
        const p = (t * 0.45 + i * 0.2) % 1;
        tmp.copy(m.position).multiplyScalar(1 - p);
        pulses[i].position.copy(tmp);
        pulses[i].scale.setScalar(Math.sin(p * Math.PI) * (on ? 1.8 : 1) + 0.01);
      });
      linkGeo.attributes.position.needsUpdate = true;
      renderer.render(scene, camera);
    };
    loop();

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      window.removeEventListener('pointermove', onPointer);
      window.removeEventListener('resize', onResize);
      disposables.forEach((d) => d.dispose());
      envTex.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <div ref={hostRef} aria-hidden="true" className="fixed inset-0 z-0 pointer-events-none opacity-60 lg:opacity-100">
      {fallback && <div className="absolute right-[10%] top-1/4 h-80 w-80 rounded-full bg-[#c6ee2e]/40 blur-3xl" />}
    </div>
  );
};

export default OrbitScene;
