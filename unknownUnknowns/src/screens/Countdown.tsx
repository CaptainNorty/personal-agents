import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const GLYPHS = ['3', '2', '1', 'GO'] as const;
const STEP_MS = 1000;

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

export default function Countdown() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;

  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index >= GLYPHS.length) {
      navigate('/cold/prep/1', {
        replace: true,
        state: { promptCount, includeRepeat: state.includeRepeat ?? false },
      });
      return;
    }
    const t = window.setTimeout(() => setIndex((i) => i + 1), STEP_MS);
    return () => window.clearTimeout(t);
  }, [index, navigate, promptCount, state.includeRepeat]);

  if (index >= GLYPHS.length) return null;

  const glyph = GLYPHS[index];

  return (
    <div className="min-h-screen w-full bg-ink text-paper flex flex-col">
      <main className="flex-1 flex items-center justify-center">
        <div
          key={index}
          className="animate-countdown font-sans font-extrabold leading-[0.85] tracking-[-0.06em] text-[200px]"
          aria-live="polite"
        >
          {glyph}
        </div>
      </main>
      <footer className="pb-10 flex justify-center">
        <span className="text-[10px] font-semibold tracking-[0.18em] uppercase opacity-50">
          Prompt 1 of {promptCount}
        </span>
      </footer>
    </div>
  );
}
