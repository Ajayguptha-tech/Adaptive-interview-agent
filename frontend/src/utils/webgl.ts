/**
 * WebGL Capability Detection & Hardware Profiling Utility
 */

export interface WebGLSupport {
  supported: boolean;
  isWebGL2: boolean;
  gpuRenderer?: string;
  isLowPowerDevice: boolean;
}

export function detectWebGLSupport(): WebGLSupport {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return {
      supported: false,
      isWebGL2: false,
      isLowPowerDevice: true,
    };
  }

  // Check reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Check hardware concurrency / mobile heuristic
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  const cores = navigator.hardwareConcurrency || 4;
  const isLowPowerDevice = isMobile || cores <= 2 || prefersReducedMotion;

  try {
    const canvas = document.createElement('canvas');
    let gl: WebGLRenderingContext | WebGL2RenderingContext | null = null;
    let isWebGL2 = false;

    // Try WebGL2 first
    gl = canvas.getContext('webgl2') as WebGL2RenderingContext | null;
    if (gl) {
      isWebGL2 = true;
    } else {
      gl = (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    }

    if (!gl) {
      return {
        supported: false,
        isWebGL2: false,
        isLowPowerDevice,
      };
    }

    // Read debug renderer info if available
    let gpuRenderer: string | undefined;
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (debugInfo) {
      gpuRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
    }

    return {
      supported: true,
      isWebGL2,
      gpuRenderer,
      isLowPowerDevice,
    };
  } catch (e) {
    return {
      supported: false,
      isWebGL2: false,
      isLowPowerDevice,
    };
  }
}
