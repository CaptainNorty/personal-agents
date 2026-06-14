import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  getBriefings,
  kickOffBriefingGeneration,
  peekBriefings,
} from '../lib/api';
import { useProgressivePoll } from '../lib/useProgressivePoll';
import { useLeftSwipe } from '../lib/swipe';
import SegmentNav from '../components/SegmentNav';
import BriefingPage from './BriefingPage';
import type { BriefingItem } from '../lib/types';

const MAX_WAIT_MS = 180_000;

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

/**
 * Persistent container for the briefing-reading phase. Mounted once for the
 * whole phase: it holds the polled briefing list and keeps polling as the
 * user tabs between items, so later briefings light up while an earlier one
 * is being read. The current index comes from the URL (`/briefing/:index`).
 *
 * Count-agnostic: the segment count is driven by the server list length, so a
 * single-item ("One Daily Challenge") session collapses to one page with no
 * top nav and a direct "Final challenge →".
 */
export default function BriefingFlow() {
  const { index } = useParams<{ index: string }>();
  const briefingIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 1;
  const includeRepeat = state.includeRepeat ?? false;

  const { items, error, retry } = useProgressivePoll<BriefingItem>({
    fetcher: async (o) => {
      const data = await getBriefings(o);
      return { items: data.briefings, status: data.status };
    },
    kickoff: kickOffBriefingGeneration,
    initialItems: peekBriefings()?.briefings ?? [],
    maxWaitMs: MAX_WAIT_MS,
  });

  // Order defensively; the server returns order_index-sorted but don't rely on it.
  const sorted = [...items].sort((a, b) => a.order_index - b.order_index);
  const total = Math.max(sorted.length, promptCount, 1);

  const itemFor = (i: number) =>
    sorted.find((b) => b.order_index === i - 1) ?? null;
  const isReady = (i: number) => itemFor(i)?.briefing_md != null;

  const current = itemFor(briefingIndex);
  const isLast = briefingIndex >= total;
  const nextReady = isLast || isReady(briefingIndex + 1);

  const advance = () => {
    if (isLast) {
      navigate('/final/prep/1', { state: { promptCount, includeRepeat } });
    } else if (nextReady) {
      navigate(`/briefing/${briefingIndex + 1}`, {
        state: { promptCount, includeRepeat },
      });
    }
  };

  const goTo = (i: number) =>
    navigate(`/briefing/${i}`, { state: { promptCount, includeRepeat } });

  const swipeHandlers = useLeftSwipe(advance);

  const segments = Array.from({ length: total }, (_, i) => ({
    index: i + 1,
    ready: isReady(i + 1),
  }));

  return (
    <div className="h-dvh w-full bg-paper text-ink flex flex-col" {...swipeHandlers}>
      <div className="mx-auto w-full max-w-[420px] px-6 pt-8 pb-6 flex flex-col flex-1 min-h-0">
        <SegmentNav segments={segments} current={briefingIndex} onSelect={goTo} />

        {error ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <p className="text-[14px] opacity-70 max-w-[260px]">
              Couldn't finish preparing your briefings. {error}
            </p>
            <button
              onClick={retry}
              className="mt-6 text-[13px] underline underline-offset-4 opacity-70"
            >
              Try again
            </button>
          </div>
        ) : (
          <BriefingPage
            key={briefingIndex}
            item={current}
            index={briefingIndex}
            total={total}
            isLast={isLast}
            nextReady={nextReady}
            onAdvance={advance}
          />
        )}
      </div>
    </div>
  );
}
