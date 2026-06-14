/**
 * Top-of-screen navigator shared by the briefing and score flows.
 *
 * Each segment is one item (briefing or topic). The row triples as:
 *   • progress indicator (which one you're on)
 *   • readiness indicator (ready vs still generating)
 *   • navigator (tap a ready segment to jump to it)
 *
 * Collapses to nothing for a single-item session (the future "One Daily
 * Challenge" shape) — there's nothing to navigate between.
 */

export type Segment = {
  index: number; // 1-based
  ready: boolean;
};

type Props = {
  segments: Segment[];
  current: number; // 1-based
  onSelect: (index: number) => void;
};

export default function SegmentNav({ segments, current, onSelect }: Props) {
  if (segments.length <= 1) return null;

  return (
    <div className="flex justify-center gap-1.5" role="tablist">
      {segments.map((seg) => {
        const isCurrent = seg.index === current;
        const selectable = seg.ready && !isCurrent;

        const cls = isCurrent
          ? 'bg-ink text-paper'
          : seg.ready
            ? 'border border-ink/30 text-ink/70'
            : 'border border-ink/15 text-ink/30';

        return (
          <button
            key={seg.index}
            role="tab"
            aria-selected={isCurrent}
            disabled={!selectable}
            onClick={() => selectable && onSelect(seg.index)}
            className={[
              'h-[26px] min-w-[34px] px-2.5 rounded-full text-[11px] font-medium tabular-nums',
              'inline-flex items-center justify-center gap-1 select-none transition-colors',
              cls,
            ].join(' ')}
            aria-label={
              seg.ready
                ? `Go to ${seg.index}`
                : `${seg.index} — still generating`
            }
          >
            {seg.index}
            {!seg.ready && (
              <span
                className="animate-thinking-dot block w-[4px] h-[4px] rounded-full bg-current opacity-70"
                aria-hidden
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
