import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { getFinals, getToday, peekFinals, peekToday } from '../lib/api';
import { FAKE_TOPICS } from '../data/fakeTopics';

const PREP_DURATION_MS = 10_000;
const ENGAGE_PULSE_MS = 200;
const ARC_RADIUS = 68;
const ARC_CIRCUMFERENCE = 2 * Math.PI * ARC_RADIUS;

type Phase = 'cold' | 'final';

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

type Props = {
  phase: Phase;
};

export default function PrepScreen({ phase }: Props) {
  const { index } = useParams<{ index: string }>();
  const promptIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  const [remaining, setRemaining] = useState(10);
  const [engaging, setEngaging] = useState(false);

  // Prompt text comes from the API for both phases, with fixture fallback.
  // Cold cache is populated by Home during Begin; finals cache fills on first
  // FinalPrep mount.
  const fakeTopic = FAKE_TOPICS[(promptIndex - 1) % FAKE_TOPICS.length]!;
  const initialReal =
    phase === 'cold'
      ? (peekToday()?.prompts.find((p) => p.order_index === promptIndex - 1)
          ?.cold_prompt_text ?? null)
      : (peekFinals()?.prompts.find((p) => p.order_index === promptIndex - 1)
          ?.final_prompt_text ?? null);
  const [realText, setRealText] = useState<string | null>(initialReal);

  useEffect(() => {
    if (realText != null) return;
    let cancelled = false;
    const fetcher = phase === 'cold' ? getToday() : getFinals();
    fetcher
      .then((r) => {
        if (cancelled) return;
        const p = r.prompts.find((pp) => pp.order_index === promptIndex - 1);
        if (p) {
          setRealText(
            'cold_prompt_text' in p ? p.cold_prompt_text : p.final_prompt_text,
          );
        }
      })
      .catch(() => {
        // Network or auth error — silently fall back to fixture text.
      });
    return () => {
      cancelled = true;
    };
  }, [phase, promptIndex, realText]);

  const promptText =
    realText ?? (phase === 'cold' ? fakeTopic.coldPrompt : fakeTopic.finalPrompt);
  const headerLabel =
    phase === 'cold'
      ? `Prompt ${promptIndex} / ${promptCount}`
      : `Final · ${promptIndex} of ${promptCount}`;
  const countdownLabel =
    phase === 'cold' ? `Mic engages in ${remaining}s` : `${remaining}s`;
  const promptSizeClass = phase === 'cold' ? 'text-[28px]' : 'text-[24px]';
  const promptLeadingClass = phase === 'cold' ? 'leading-[1.05]' : 'leading-[1.1]';

  useEffect(() => {
    const startedAt = Date.now();
    let navigateTimeout: number | null = null;

    const tick = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const r = Math.max(0, Math.ceil((PREP_DURATION_MS - elapsed) / 1000));
      setRemaining(r);

      if (elapsed >= PREP_DURATION_MS) {
        window.clearInterval(tick);
        setEngaging(true);
        navigateTimeout = window.setTimeout(() => {
          navigate(`/${phase}/record/${promptIndex}`, {
            state: { promptCount, includeRepeat },
            replace: true,
          });
        }, ENGAGE_PULSE_MS);
      }
    }, 200);

    return () => {
      window.clearInterval(tick);
      if (navigateTimeout !== null) window.clearTimeout(navigateTimeout);
    };
  }, [navigate, phase, promptIndex, promptCount, includeRepeat]);

  return (
    <div className="min-h-screen w-full bg-paper text-ink flex flex-col">
      <div className="mx-auto w-full max-w-[420px] px-6 pt-12 pb-10 flex flex-col flex-1">
        <header>
          <div className="tiny-label">{headerLabel}</div>
          <div
            className={`mt-3.5 ${promptSizeClass} font-semibold tracking-[-0.025em] ${promptLeadingClass}`}
          >
            {promptText}
          </div>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center">
          <div className="relative w-[140px] h-[140px]">
            <svg
              viewBox="0 0 140 140"
              width="140"
              height="140"
              className="absolute inset-0"
              aria-hidden
            >
              <circle
                cx="70"
                cy="70"
                r={ARC_RADIUS}
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                opacity="0.2"
              />
              <circle
                cx="70"
                cy="70"
                r={ARC_RADIUS}
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeDasharray={ARC_CIRCUMFERENCE}
                strokeDashoffset={ARC_CIRCUMFERENCE}
                transform="rotate(-90 70 70)"
                className="animate-prep-arc"
              />
            </svg>

            <div
              className={[
                'absolute inset-0 flex items-center justify-center origin-center',
                engaging ? 'animate-prep-engage' : '',
              ].join(' ')}
            >
              <div className="w-[70px] h-[70px] rounded-full bg-ink" />
            </div>
          </div>

          <div className="mt-6 tiny-label" aria-live="polite">
            {remaining > 0 ? countdownLabel : 'Recording'}
          </div>
        </main>
      </div>
    </div>
  );
}
