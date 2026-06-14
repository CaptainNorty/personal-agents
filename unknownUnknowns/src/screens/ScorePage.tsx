import { useEffect, useState } from 'react';
import { renderInline } from '../lib/inline';
import type { TopicScoreItem } from '../lib/types';

const NET_DELTA_DURATION = 600;
const METRIC_COUNT_DURATION = 600;
const ROW_STAGGER_MS = 80;

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

type Props = {
  item: TopicScoreItem | null;
  index: number; // 1-based
  total: number;
  isLast: boolean;
  nextReady: boolean;
  onAdvance: () => void;
};

export default function ScorePage({
  item,
  index,
  total,
  isLast,
  nextReady,
  onAdvance,
}: Props) {
  const ready = item?.is_ready === true;
  const netDelta = ready ? (item!.net_delta ?? 0) : 0;
  const netDeltaV = useCountUp(netDelta, NET_DELTA_DURATION, 0);

  if (!ready) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <header className="mt-5 flex-shrink-0">
          <div className="tiny-label">
            Topic {index} / {total}
          </div>
        </header>
        <main className="flex-1 flex flex-col items-center justify-center text-center">
          <div className="text-[15px] opacity-60">Scoring this topic…</div>
          <div className="mt-6 flex gap-[7px]" aria-hidden>
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
        </main>
        <footer className="mt-5 flex justify-center flex-shrink-0">
          <button
            disabled
            className="inline-flex items-center gap-2 tiny-label opacity-40 px-4 py-3"
          >
            Scoring
            <span
              className="animate-thinking-dot block w-[5px] h-[5px] bg-ink rounded-full"
              aria-hidden
            />
          </button>
        </footer>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-y-auto">
      {/* Topic header */}
      <header className="mt-5 flex-shrink-0">
        <div className="tiny-label">
          Topic {index} / {total}
        </div>
        <h1 className="mt-1 text-[22px] font-bold tracking-[-0.025em] leading-[1.05]">
          {item!.topic_title}
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
          {item!.metrics.map((m, i) => (
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
      {item!.notes_md && (
        <section className="mt-5 text-[14px] leading-[1.55] text-ink/85 italic max-w-[40ch]">
          {renderInline(item!.notes_md)}
        </section>
      )}

      {/* Footer */}
      <footer className="mt-auto pt-6 flex justify-center">
        {isLast ? (
          <button
            onClick={onAdvance}
            className="tiny-label opacity-50 px-4 py-2"
            aria-label="Continue"
          >
            Continue ›
          </button>
        ) : nextReady ? (
          <button
            onClick={onAdvance}
            className="tiny-label opacity-50 px-4 py-2"
            aria-label={`Continue to topic ${index + 1}`}
          >
            Continue ›
          </button>
        ) : (
          <button
            disabled
            className="inline-flex items-center gap-2 tiny-label opacity-40 px-4 py-2"
            aria-label="Next topic is still being scored"
          >
            Next is scoring
            <span
              className="animate-thinking-dot block w-[5px] h-[5px] bg-ink rounded-full"
              aria-hidden
            />
          </button>
        )}
      </footer>
    </div>
  );
}
