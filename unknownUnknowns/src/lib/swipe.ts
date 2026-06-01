import { useRef, type PointerEvent } from 'react';

const SWIPE_THRESHOLD_PX = 50;

/**
 * Attach to any element: `<div {...useLeftSwipe(advance)}>…</div>`.
 *
 * Fires `onSwipe` when the pointer travels horizontally left by at least
 * SWIPE_THRESHOLD_PX, with the horizontal motion dominating vertical (so
 * vertical scrolling doesn't accidentally trigger the swipe). Tap-on-button
 * still works as a fallback — those gestures don't satisfy the threshold.
 */
export function useLeftSwipe(onSwipe: () => void) {
  const start = useRef<{ x: number; y: number } | null>(null);
  return {
    onPointerDown: (e: PointerEvent) => {
      start.current = { x: e.clientX, y: e.clientY };
    },
    onPointerUp: (e: PointerEvent) => {
      const begin = start.current;
      start.current = null;
      if (begin === null) return;
      const dx = e.clientX - begin.x;
      const dy = e.clientY - begin.y;
      if (Math.abs(dx) > Math.abs(dy) && dx < -SWIPE_THRESHOLD_PX) {
        onSwipe();
      }
    },
    onPointerCancel: () => {
      start.current = null;
    },
  };
}
