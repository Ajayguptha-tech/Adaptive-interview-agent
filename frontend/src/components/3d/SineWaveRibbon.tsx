import React, { useEffect, useRef } from 'react';

export const SineWaveRibbon: React.FC<{ className?: string }> = ({ className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let step = 0;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const speed = prefersReducedMotion ? 0.003 : 0.015;

    const handleResize = () => {
      canvas.width = canvas.parentElement?.clientWidth || window.innerWidth;
      canvas.height = canvas.parentElement?.clientHeight || 400;
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const render = () => {
      step += speed;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;
      const midY = height * 0.5;

      // Draw Ribbon 1: Cyan harmonic wave
      ctx.beginPath();
      ctx.lineWidth = 2;
      const gradCyan = ctx.createLinearGradient(0, 0, width, 0);
      gradCyan.addColorStop(0, 'rgba(0, 242, 254, 0)');
      gradCyan.addColorStop(0.3, 'rgba(0, 242, 254, 0.35)');
      gradCyan.addColorStop(0.7, 'rgba(139, 92, 246, 0.4)');
      gradCyan.addColorStop(1, 'rgba(0, 242, 254, 0)');
      ctx.strokeStyle = gradCyan;

      for (let x = 0; x <= width; x += 6) {
        const y = midY + 
          Math.sin(x * 0.0035 + step) * 45 + 
          Math.sin(x * 0.007 - step * 0.8) * 20;
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // Draw Ribbon 2: Electric violet counter-wave
      ctx.beginPath();
      ctx.lineWidth = 1.5;
      const gradViolet = ctx.createLinearGradient(0, 0, width, 0);
      gradViolet.addColorStop(0, 'rgba(139, 92, 246, 0)');
      gradViolet.addColorStop(0.4, 'rgba(139, 92, 246, 0.3)');
      gradViolet.addColorStop(0.8, 'rgba(236, 72, 153, 0.25)');
      gradViolet.addColorStop(1, 'rgba(139, 92, 246, 0)');
      ctx.strokeStyle = gradViolet;

      for (let x = 0; x <= width; x += 6) {
        const y = midY + 
          Math.sin(x * 0.0045 - step * 1.2) * 35 + 
          Math.cos(x * 0.008 + step) * 25;
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className={`absolute inset-0 pointer-events-none overflow-hidden z-0 opacity-70 ${className}`}>
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  );
};
