import { describe, it, expect } from 'vitest';

describe('Adaptive Interview Intelligence Session Timing & Controls', () => {
  it('formats session timer seconds accurately into mm:ss', () => {
    const formatTimer = (sec: number | null) => {
      if (sec === null) return '--:--';
      const m = Math.floor(sec / 60).toString().padStart(2, '0');
      const s = (sec % 60).toString().padStart(2, '0');
      return `${m}:${s}`;
    };

    expect(formatTimer(2400)).toBe('40:00');
    expect(formatTimer(1805)).toBe('30:05');
    expect(formatTimer(65)).toBe('01:05');
    expect(formatTimer(9)).toBe('00:09');
    expect(formatTimer(0)).toBe('00:00');
    expect(formatTimer(null)).toBe('--:--');
  });

  it('correctly tracks pause and resume timer progression simulation', () => {
    let timeRemaining = 2400;
    let isPaused = false;

    const tick = () => {
      if (!isPaused && timeRemaining > 0) {
        timeRemaining -= 1;
      }
    };

    // 5 seconds tick while active
    for (let i = 0; i < 5; i++) tick();
    expect(timeRemaining).toBe(2395);

    // Pause session
    isPaused = true;
    for (let i = 0; i < 5; i++) tick();
    // Time remaining should NOT decrement while paused
    expect(timeRemaining).toBe(2395);

    // Resume session
    isPaused = false;
    for (let i = 0; i < 3; i++) tick();
    expect(timeRemaining).toBe(2392);
  });
});
