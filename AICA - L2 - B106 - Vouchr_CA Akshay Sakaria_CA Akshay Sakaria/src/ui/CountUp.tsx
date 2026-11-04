import { useEffect, useRef, useState } from 'react';

/** Animates a number from its previous value to the new one (ease-out, ~700 ms). Respects reduced motion. */
export function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const [shown, setShown] = useState(value);
  const from = useRef(0);
  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { setShown(value); return; }
    const start = performance.now(), a = from.current, b = value;
    let raf = 0;
    const step = (t: number) => {
      const k = Math.min((t - start) / 700, 1);
      const eased = 1 - Math.pow(1 - k, 3);
      setShown(a + (b - a) * eased);
      if (k < 1) raf = requestAnimationFrame(step); else from.current = b;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{format(shown)}</>;
}
