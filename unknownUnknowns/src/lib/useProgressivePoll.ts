/**
 * Generic progressive poller for the briefing and score flows.
 *
 * Fires an optional one-time kickoff, then polls `fetcher` (with
 * forceRefresh so the cache can't serve a stale `pending` forever) every
 * `intervalMs` until status is 'complete' or `maxWaitMs` elapses. Returns the
 * latest items each tick so the UI can light up segments as they land — the
 * whole point of "show briefing 1 while 2 & 3 are still generating".
 *
 * Lives in a persistent flow container (BriefingFlow / ScoreFlow) so polling
 * survives navigation between items — it is NOT restarted per index.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type PollStatus = 'pending' | 'partial' | 'complete';

type Fetched<T> = { items: T[]; status: PollStatus };

type Options<T> = {
  fetcher: (o: { forceRefresh: boolean }) => Promise<Fetched<T>>;
  kickoff?: () => Promise<unknown>;
  initialItems?: T[];
  intervalMs?: number;
  maxWaitMs?: number;
};

export function useProgressivePoll<T>({
  fetcher,
  kickoff,
  initialItems = [],
  intervalMs = 2_000,
  maxWaitMs = 180_000,
}: Options<T>): {
  items: T[];
  status: PollStatus;
  error: string | null;
  retry: () => void;
} {
  const [items, setItems] = useState<T[]>(initialItems);
  const [status, setStatus] = useState<PollStatus>(
    initialItems.length > 0 ? 'partial' : 'pending',
  );
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  // Keep the latest fetcher/kickoff without retriggering the effect each render.
  const fetcherRef = useRef(fetcher);
  const kickoffRef = useRef(kickoff);
  fetcherRef.current = fetcher;
  kickoffRef.current = kickoff;

  const retry = useCallback(() => {
    setError(null);
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: number | null = null;
    let elapsed = 0;

    async function tick() {
      if (cancelled) return;
      try {
        const data = await fetcherRef.current({ forceRefresh: true });
        if (cancelled) return;
        setItems(data.items);
        setStatus(data.status);
        if (data.status === 'complete') return; // stop polling
      } catch (err) {
        // Transient errors are fine — keep polling; persistent ones hit the
        // timeout path below.
        console.warn('[uu] progressive poll error:', err);
      }
      elapsed += intervalMs;
      if (elapsed >= maxWaitMs) {
        if (!cancelled) setError('Taking longer than expected.');
        return;
      }
      timer = window.setTimeout(tick, intervalMs);
    }

    // Kick off generation (idempotent server-side), then start polling
    // regardless of how kickoff resolves — the first poll catches an
    // already-complete state.
    kickoffRef.current?.().catch((err) => {
      console.warn('[uu] kickoff error:', err);
    });
    timer = window.setTimeout(tick, intervalMs);

    return () => {
      cancelled = true;
      if (timer !== null) window.clearTimeout(timer);
    };
    // `attempt` re-arms the loop on retry.
  }, [attempt, intervalMs, maxWaitMs]);

  return { items, status, error, retry };
}
