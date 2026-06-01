import { Fragment, useEffect, useState, type ReactNode } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { getScores, peekScores } from '../lib/api';
import { useLeftSwipe } from '../lib/swipe';
import { FAKE_TOPICS } from '../data/fakeTopics';
import { FAKE_SCORES } from '../data/fakeScores';
import type { TopicScoreItem } from '../lib/types';

const NET_DELTA_DURATION = 600;
const METRIC_COUNT_DURATION = 600;
const ROW_STAGGER_MS = 80;

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

/** Animate a number from 0 to `target` over `durationMs` after `delayMs`,
 * ease-out cubic. Snaps to exact target at the end to avoid drift. */
function useCountUp(target: number, durationMs: number, delayMs: number): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let raf = 0;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      if (elapsed < delayMs) {
        raf = requestAnimationFrame(tick);
        return;
      }
      const progress = Math.min(1, (elapsed - delayMs) / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        setValue(target);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs, delayMs]);

  return value;
}

/** Format a signed number with a fixed sign anchored to the target. */
function formatSigned(displayed: number, target: number, decimals: number): string {
  const abs = Math.abs(displayed).toFixed(decimals);
  if (target > 0) return `+${abs}`;
  if (target < 0) return `−${abs}`;
  return abs;
}

function formatRowDelta(displayed: number, target: number): string {
  const abs = Math.abs(Math.round(displayed));
  if (target > 0) return `+${abs}`;
  if (target < 0) return `−${abs} ▾`;
  return '0';
}

/** Minimal inline-italic renderer: *foo* → <em>foo</em>. Same as Briefing.tsx. */
function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*[^*\n]+\*)/g);
  return parts.map((part, i) => {
    if (part.length > 2 && part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

type RowProps = {
  label: string;
  cold: number;
  final: number;
  delta: number;
  rowIndex: number;
};

function MetricRow({ label, cold, final, delta, rowIndex }: RowProps) {
  const delayMs = rowIndex * ROW_STAGGER_MS;
  const coldV = useCountUp(cold, METRIC_COUNT_DURATION, delayMs);
  const finalV = useCountUp(final, METRIC_COUNT_DURATION, delayMs);
  const deltaV = useCountUp(delta, METRIC_COUNT_DURATION, delayMs);

  return (
    <div
      className="animate-score-row-in grid grid-cols-[1fr_2rem_2rem_2.75rem] gap-2.5 py-2 items-baseline text-[11px] border-t border-ink/30 first:border-t-0"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      <span className="font-medium opacity-80 tracking-[0.02em]">{label}</span>
      <span className="text-right tabular-nums opacity-55">{Math.round(coldV)}</span>
      <span className="text-right tabular-nums opacity-55">{Math.round(finalV)}</span>
      <span className="text-right tabular-nums tracking-[-0.01em] font-extrabold">
        {formatRowDelta(deltaV, delta)}
      </span>
    </div>
  );
}

export default function Score() {
  const { index } = useParams<{ index: string }>();
  const topicIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  // Try cache synchronously; fetch on mount if a refresh recovery is needed.
  const initial =
    peekScores()?.scores.find((s) => s.order_index === topicIndex - 1) ?? null;
  const [realScore, setRealScore] = useState<TopicScoreItem | null>(initial);

  useEffect(() => {
    if (realScore?.is_ready) return;
    let cancelled = false;
    getScores()
      .then((data) => {
        if (cancelled) return;
        const found = data.scores.find((s) => s.order_index === topicIndex - 1);
        if (found?.is_ready) setRealScore(found);
      })
      .catch(() => {
        // Silent fallback to fixture data.
      });
    return () => {
      cancelled = true;
    };
  }, [topicIndex, realScore]);

  // Pick source: real per-topic block if ready, else fixture.
  const fixtureTopic = FAKE_TOPICS[(topicIndex - 1) % FAKE_TOPICS.length]!;
  const fixtureScore = FAKE_SCORES[(topicIndex - 1) % FAKE_SCORES.length]!;

  let title: string;
  let netDelta: number;
  let metrics: { label: string; cold: number; final: number; delta: number }[];
  let notes: string | null;

  if (realScore?.is_ready) {
    title = realScore.topic_title;
    netDelta = realScore.net_delta ?? 0;
    metrics = realScore.metrics;
    notes = realScore.notes_md;
  } else {
    title = fixtureTopic.topicTitle;
    netDelta = fixtureScore.netDelta;
    metrics = fixtureScore.metrics;
    notes = null;
  }

  const isLast = topicIndex >= promptCount;
  const netDeltaV = useCountUp(netDelta, NET_DELTA_DURATION, 0);

  const advance = () => {
    const nextRoute = isLast ? '/done' : `/scores/${topicIndex + 1}`;
    navigate(nextRoute, { state: { promptCount, includeRepeat } });
  };

  const swipeHandlers = useLeftSwipe(advance);

  return (
    <div
      className="h-dvh w-full bg-paper text-ink flex flex-col"
      {...swipeHandlers}
    >
      <div className="mx-auto w-full max-w-[420px] px-6 pt-8 pb-6 flex flex-col flex-1 min-h-0 overflow-y-auto">
        {/* Progress dots */}
        <div className="flex justify-center gap-1.5">
          {Array.from({ length: promptCount }).map((_, i) => (
            <span
              key={i}
              className={[
                'block w-[18px] h-[2px] bg-ink',
                i === topicIndex - 1 ? 'opacity-100' : 'opacity-25',
              ].join(' ')}
            />
          ))}
        </div>

        {/* Topic header */}
        <header className="mt-5 flex-shrink-0">
          <div className="tiny-label">
            Topic {topicIndex} / {promptCount}
          </div>
          <h1 className="mt-1 text-[22px] font-bold tracking-[-0.025em] leading-[1.05]">
            {title}
          </h1>
        </header>

        {/* Big net change */}
        <section className="mt-5 flex-shrink-0">
          <div className="tiny-label opacity-50">Net change</div>
          <div className="mt-0.5 text-[64px] font-extrabold leading-[0.9] tracking-[-0.05em] tabular-nums">
            {formatSigned(netDeltaV, netDelta, 1)}
          </div>
        </section>

        {/* Ledger */}
        <section className="mt-6 flex-shrink-0">
          <div className="grid grid-cols-[1fr_2rem_2rem_2.75rem] gap-2.5 pb-1.5 border-b border-ink text-[9px] font-semibold tracking-[0.14em] uppercase opacity-45">
            <span></span>
            <span className="text-right">Cold</span>
            <span className="text-right">Final</span>
            <span className="text-right">Δ</span>
          </div>

          <div>
            {metrics.map((m, i) => (
              <MetricRow
                key={m.label}
                label={m.label}
                cold={m.cold}
                final={m.final}
                delta={m.delta}
                rowIndex={i}
              />
            ))}
          </div>
        </section>

        {/* Notes — personalized commentary that explains what's behind the numbers */}
        {notes && (
          <section className="mt-5 text-[14px] leading-[1.55] text-ink/85 italic max-w-[40ch]">
            {renderInline(notes)}
          </section>
        )}

        {/* Footer */}
        <footer className="mt-auto pt-6 flex justify-center">
          <button
            onClick={advance}
            className="tiny-label opacity-50 px-4 py-2"
            aria-label={isLast ? 'Continue' : `Continue to topic ${topicIndex + 1}`}
          >
            {isLast ? 'Continue ›' : 'Swipe ›'}
          </button>
        </footer>
      </div>
    </div>
  );
}
