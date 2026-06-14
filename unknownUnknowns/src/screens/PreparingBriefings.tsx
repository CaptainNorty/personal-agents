import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getBriefings, kickOffBriefingGeneration } from '../lib/api';

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

const POLL_INTERVAL_MS = 2_000;
const MAX_WAIT_SECONDS = 180; // Give up after 3 minutes — server-side wait + LLM call

/**
 * Bridge screen between last cold record and the briefing reading phase.
 *
 * Behavior:
 *   1. Fires POST /briefings/generate (idempotent — fine if already done).
 *   2. Polls GET /briefings every 2s until the FIRST briefing is ready
 *      (status !== 'pending') or timeout.
 *   3. Shows "N of M ready" so the wait feels active.
 *   4. Hands off to /briefing/1 as soon as the first is ready; BriefingFlow
 *      keeps polling for the rest and shows them progressively.
 *
 * The visual treatment matches the cold→cold interstitial (off-white,
 * tiny-label + display number + progress) so it reads as another
 * "transitioning" beat, just longer and with real signal.
 */
export default function PreparingBriefings() {
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
        const data = await getBriefings({ forceRefresh: true });
        if (cancelled) return;
        const readyCount = data.briefings.filter(
          (b) => b.briefing_md !== null,
        ).length;
        setReady(readyCount);
        setTotal(data.briefings.length);
        // Hand off as soon as the FIRST briefing is ready, not the whole set.
        // BriefingFlow keeps polling and reveals the rest progressively.
        if (data.status !== 'pending') {
          // Brief beat so the count lands visually, then proceed.
          window.setTimeout(() => {
            if (!cancelled) {
              navigate('/briefing/1', { state: { promptCount, includeRepeat } });
            }
          }, 600);
          return;
        }
      } catch (err) {
        // Transient errors are fine — keep polling. Persistent ones surface
        // via the timeout path.
        console.warn('[uu] briefings poll error:', err);
      }
      elapsed += POLL_INTERVAL_MS / 1_000;
      if (elapsed >= MAX_WAIT_SECONDS) {
        if (!cancelled) {
          setError(
            "Couldn't finish preparing your briefings in time. Tap to retry.",
          );
        }
        return;
      }
      pollTimer = window.setTimeout(tick, POLL_INTERVAL_MS);
    }

    // Kick off generation, then start polling regardless of how that returns
    // (idempotent: if it's already complete, the first poll catches that).
    kickOffBriefingGeneration().catch((err) => {
      console.warn('[uu] kickoff error:', err);
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
        <div className="tiny-label mb-5">Preparing your briefings</div>
        <div className="text-[22px] font-semibold tracking-[-0.02em] leading-[1.1] text-center tabular-nums">
          {ready} of {total} ready
        </div>
        <div className="mt-2.5 text-[13px] opacity-60">
          {ready < total
            ? 'Listening to what you said and writing what comes next…'
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
