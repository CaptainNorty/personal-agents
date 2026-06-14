import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { getScores, kickOffScoring, peekScores } from '../lib/api';
import { useProgressivePoll } from '../lib/useProgressivePoll';
import { useLeftSwipe } from '../lib/swipe';
import SegmentNav from '../components/SegmentNav';
import ScorePage from './ScorePage';
import type { TopicScoreItem } from '../lib/types';

const MAX_WAIT_MS = 240_000;

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

/**
 * Persistent container for the score-reveal phase. Mirrors BriefingFlow:
 * holds the polled topic-score list, keeps polling as the user tabs between
 * topics, and surfaces each topic's score the moment it's graded rather than
 * blocking on the whole session. Count-agnostic for the One Daily Challenge
 * shape.
 */
export default function ScoreFlow() {
  const { index } = useParams<{ index: string }>();
  const topicIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 1;
  const includeRepeat = state.includeRepeat ?? false;

  const { items, error, retry } = useProgressivePoll<TopicScoreItem>({
    fetcher: async (o) => {
      const data = await getScores(o);
      return { items: data.scores, status: data.status };
    },
    kickoff: kickOffScoring,
    initialItems: peekScores()?.scores ?? [],
    maxWaitMs: MAX_WAIT_MS,
  });

  const sorted = [...items].sort((a, b) => a.order_index - b.order_index);
  const total = Math.max(sorted.length, promptCount, 1);

  const itemFor = (i: number) =>
    sorted.find((s) => s.order_index === i - 1) ?? null;
  const isReady = (i: number) => itemFor(i)?.is_ready === true;

  const current = itemFor(topicIndex);
  const isLast = topicIndex >= total;
  const nextReady = isLast || isReady(topicIndex + 1);

  const advance = () => {
    if (isLast) {
      navigate('/done', { state: { promptCount, includeRepeat } });
    } else if (nextReady) {
      navigate(`/scores/${topicIndex + 1}`, {
        state: { promptCount, includeRepeat },
      });
    }
  };

  const goTo = (i: number) =>
    navigate(`/scores/${i}`, { state: { promptCount, includeRepeat } });

  const swipeHandlers = useLeftSwipe(advance);

  const segments = Array.from({ length: total }, (_, i) => ({
    index: i + 1,
    ready: isReady(i + 1),
  }));

  return (
    <div className="h-dvh w-full bg-paper text-ink flex flex-col" {...swipeHandlers}>
      <div className="mx-auto w-full max-w-[420px] px-6 pt-8 pb-6 flex flex-col flex-1 min-h-0">
        <SegmentNav segments={segments} current={topicIndex} onSelect={goTo} />

        {error ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <p className="text-[14px] opacity-70 max-w-[260px]">
              Couldn't finish scoring. {error}
            </p>
            <button
              onClick={retry}
              className="mt-6 text-[13px] underline underline-offset-4 opacity-70"
            >
              Try again
            </button>
          </div>
        ) : (
          <ScorePage
            key={topicIndex}
            item={current}
            index={topicIndex}
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
