import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getScores, kickOffScoring } from '../lib/api';

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

const POLL_INTERVAL_MS = 2_000;
const MAX_WAIT_SECONDS = 240; // 4 min — scoring has 2 transcripts × wait + LLM

/**
 * Bridge between the last final record and the score reveal. Same visual
 * treatment as PreparingBriefings (off-white + thinking dots) so the user
 * recognizes "the model is working" without surprises.
 */
export default function PreparingScores() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  const [ready, setReady] = useState(0);
  const [total, setTotal] = useState<number>(promptCount);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: number | null = null;
    let elapsed = 0;

    async function tick() {
      if (cancelled) return;
      try {
        const data = await getScores({ forceRefresh: true });
        if (cancelled) return;
        const readyCount = data.scores.filter((s) => s.is_ready).length;
        setReady(readyCount);
        setTotal(data.scores.length);
        // Hand off as soon as the FIRST topic is scored, not the whole set.
        // ScoreFlow keeps polling and reveals the rest progressively.
        if (data.status !== 'pending') {
          window.setTimeout(() => {
            if (!cancelled) {
              navigate('/scores/1', { state: { promptCount, includeRepeat } });
            }
          }, 600);
          return;
        }
      } catch (err) {
        console.warn('[uu] scores poll error:', err);
      }
      elapsed += POLL_INTERVAL_MS / 1_000;
      if (elapsed >= MAX_WAIT_SECONDS) {
        if (!cancelled) {
          setError(
            "Couldn't finish scoring in time. Tap to retry.",
          );
        }
        return;
      }
      pollTimer = window.setTimeout(tick, POLL_INTERVAL_MS);
    }

    kickOffScoring().catch((err) => {
      console.warn('[uu] scoring kickoff error:', err);
    });
    pollTimer = window.setTimeout(tick, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (pollTimer !== null) window.clearTimeout(pollTimer);
    };
  }, [navigate, promptCount, includeRepeat]);

  return (
    <div
      className="min-h-screen w-full flex flex-col text-ink"
      style={{ backgroundColor: '#fafafa' }}
    >
      <div className="mx-auto w-full max-w-[420px] px-6 flex flex-col flex-1 items-center justify-center">
        <div className="tiny-label mb-5">Scoring your work</div>
        <div className="text-[22px] font-semibold tracking-[-0.02em] leading-[1.1] text-center tabular-nums">
          {ready} of {total} ready
        </div>
        <div className="mt-2.5 text-[13px] opacity-60">
          {ready < total
            ? 'Comparing what you said cold to what you said after the briefing…'
            : 'Almost there.'}
        </div>
        <div className="mt-9 flex gap-[7px]" aria-hidden>
          <span className="animate-thinking-dot block w-[7px] h-[7px] bg-ink rounded-full" />
          <span
            className="animate-thinking-dot block w-[7px] h-[7px] bg-ink rounded-full"
            style={{ animationDelay: '160ms' }}
          />
          <span
            className="animate-thinking-dot block w-[7px] h-[7px] bg-ink rounded-full"
            style={{ animationDelay: '320ms' }}
          />
        </div>
        {error && (
          <button
            onClick={() => window.location.reload()}
            className="mt-9 text-[13px] underline underline-offset-4 opacity-70"
          >
            {error}
          </button>
        )}
      </div>
    </div>
  );
}
