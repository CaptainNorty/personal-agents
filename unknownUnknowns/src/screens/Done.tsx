import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { completeSession } from '../lib/api';
import { timeUntilMidnight } from '../lib/time';

type LocationState = {
  promptCount?: 1 | 2 | 3;
};

/** "Three times" / "twice" / "once" — descriptive, never evaluative. */
function describeSession(n: number): string[] {
  const times = n === 1 ? 'once' : n === 2 ? 'twice' : 'three times';
  const things = n === 1 ? 'one thing' : n === 2 ? 'two things' : 'three things';
  return [
    `You spoke ${times}.`,
    `You read ${things}.`,
    `You spoke ${times} again.`,
  ];
}

export default function Done() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;

  const [countdown, setCountdown] = useState(timeUntilMidnight);
  useEffect(() => {
    const t = window.setInterval(() => {
      setCountdown(timeUntilMidnight());
    }, 60_000);
    return () => window.clearInterval(t);
  }, []);

  // Fire the end-of-session POST once on mount: marks today done, updates
  // streak, kicks off tomorrow's content generation in the background.
  // Surface the returned streak count; fall back to a placeholder otherwise.
  const [streak, setStreak] = useState<number>(0);
  useEffect(() => {
    let cancelled = false;
    completeSession()
      .then((r) => {
        if (!cancelled) setStreak(r.streak_count);
      })
      .catch((err: Error) => {
        // Non-fatal — Home will retry next time the user opens the app.
        console.warn('[uu] complete failed:', err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const lines = describeSession(promptCount);

  return (
    <div className="min-h-screen w-full bg-paper text-ink flex flex-col">
      <div className="mx-auto w-full max-w-[420px] px-6 pt-14 pb-8 flex flex-col flex-1">
        <header className="flex flex-col items-center">
          <div
            className="text-[34px] font-extrabold leading-none tracking-[-0.04em] select-none"
            aria-label="Unknown Unknowns"
          >
            UU
          </div>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center text-center">
          <div className="text-[24px] font-semibold tracking-[-0.025em] leading-[1.1]">
            Done.
          </div>
          <div className="mt-4 max-w-[220px] text-[15px] leading-[1.5] text-ink/85">
            {lines.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
          <div className="mt-7 text-[11px] font-medium tracking-[0.04em]">
            {streak === 0 ? 'First day' : `${streak}-day streak`}
          </div>
          <div className="mt-1 tiny-label opacity-50">
            New unknowns in {countdown}
          </div>
        </main>

        <footer className="flex justify-center">
          <button
            onClick={() => navigate('/', { replace: true })}
            className="tiny-label opacity-40 px-4 py-2"
            aria-label="Close"
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}
