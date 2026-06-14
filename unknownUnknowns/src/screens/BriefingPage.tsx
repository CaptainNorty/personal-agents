import { renderInline } from '../lib/inline';
import type { BriefingItem } from '../lib/types';

/** Parse the assembled briefing markdown.
 *
 * Layout is:
 *   # {topic_title}
 *
 *   {acknowledgment paragraph}
 *
 *   {body paragraph 1}
 *   ...
 *
 * The acknowledgment is rendered with italic emphasis so the "you said X,
 * here's Y" beat lands visibly without competing with the body's own
 * inline italics.
 */
function parseBriefingMd(md: string): {
  title: string;
  acknowledgment: string | null;
  paragraphs: string[];
} {
  const lines = md.split('\n');
  const titleLineIdx = lines.findIndex((l) => l.trim().startsWith('# '));
  const title =
    titleLineIdx >= 0
      ? lines[titleLineIdx]!.trim().replace(/^#\s+/, '').trim()
      : 'Briefing';
  const afterTitle = lines
    .slice(titleLineIdx + 1)
    .join('\n')
    .trim();
  const blocks = afterTitle
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
  const acknowledgment = blocks[0] ?? null;
  const paragraphs = blocks.slice(1);
  return { title, acknowledgment, paragraphs };
}

type Props = {
  item: BriefingItem | null;
  index: number; // 1-based
  total: number;
  isLast: boolean;
  nextReady: boolean;
  onAdvance: () => void;
};

export default function BriefingPage({
  item,
  index,
  total,
  isLast,
  nextReady,
  onAdvance,
}: Props) {
  const ready = item?.briefing_md != null;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <header className="mt-5 flex-shrink-0">
        <div className="tiny-label">
          Briefing · {index} of {total}
        </div>
        {ready && (
          <h1 className="mt-1.5 text-[22px] font-bold tracking-[-0.025em] leading-[1.05]">
            {parseBriefingMd(item!.briefing_md!).title}
          </h1>
        )}
      </header>

      {/* Body */}
      <main className="flex-1 mt-5 overflow-y-auto min-h-0">
        {ready ? (
          (() => {
            const { acknowledgment, paragraphs } = parseBriefingMd(
              item!.briefing_md!,
            );
            return (
              <div className="space-y-3.5 text-[17px] leading-[1.55] text-ink/85 max-w-[34ch] sm:max-w-[42ch]">
                {acknowledgment && (
                  <p className="italic text-ink/95">
                    {renderInline(acknowledgment)}
                  </p>
                )}
                {paragraphs.map((para, i) => (
                  <p key={i}>{renderInline(para)}</p>
                ))}
              </div>
            );
          })()
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="text-[15px] opacity-60">
              Writing this briefing…
            </div>
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
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-5 flex justify-center flex-shrink-0">
        {isLast ? (
          <button
            onClick={onAdvance}
            disabled={!ready}
            className="w-full max-w-[260px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80 disabled:opacity-40"
          >
            Final challenges →
          </button>
        ) : nextReady ? (
          <button
            onClick={onAdvance}
            disabled={!ready}
            className="w-full max-w-[260px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80 disabled:opacity-40"
          >
            Continue
          </button>
        ) : (
          <button
            disabled
            className="inline-flex items-center gap-2 tiny-label opacity-40 px-4 py-3"
            aria-label="Next briefing is still being written"
          >
            Next is writing
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
