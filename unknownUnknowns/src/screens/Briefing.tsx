import { Fragment, useEffect, useState, type ReactNode } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { getBriefings, peekBriefings } from '../lib/api';
import { useLeftSwipe } from '../lib/swipe';
import { FAKE_TOPICS } from '../data/fakeTopics';
import type { BriefingItem } from '../lib/types';

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

/** Minimal inline-italic renderer: *foo* → <em>foo</em>. */
function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*[^*\n]+\*)/g);
  return parts.map((part, i) => {
    if (part.length > 2 && part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

/** Parse the assembled briefing markdown.
 *
 * Layout is:
 *   # {topic_title}
 *
 *   {acknowledgment paragraph}
 *
 *   {body paragraph 1}
 *
 *   {body paragraph 2}
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
  const afterTitle = lines.slice(titleLineIdx + 1).join('\n').trim();
  const blocks = afterTitle
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
  const acknowledgment = blocks[0] ?? null;
  const paragraphs = blocks.slice(1);
  return { title, acknowledgment, paragraphs };
}

export default function Briefing() {
  const { index } = useParams<{ index: string }>();
  const briefingIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  // Try cache synchronously, fall back to fetching on mount if refresh-recovery.
  const initial =
    peekBriefings()?.briefings.find((b) => b.order_index === briefingIndex - 1) ??
    null;
  const [realBriefing, setRealBriefing] = useState<BriefingItem | null>(initial);

  useEffect(() => {
    if (realBriefing?.briefing_md) return;
    let cancelled = false;
    getBriefings()
      .then((data) => {
        if (cancelled) return;
        if (data.status !== 'pending') {
          const found = data.briefings.find(
            (b) => b.order_index === briefingIndex - 1,
          );
          if (found) setRealBriefing(found);
        }
      })
      .catch(() => {
        // Silent fallback to fixture.
      });
    return () => {
      cancelled = true;
    };
  }, [briefingIndex, realBriefing]);

  // Pick source: real markdown if available, otherwise fixture.
  const fixture = FAKE_TOPICS[(briefingIndex - 1) % FAKE_TOPICS.length]!;
  let title: string;
  let acknowledgment: string | null;
  let paragraphs: string[];
  if (realBriefing?.briefing_md) {
    const parsed = parseBriefingMd(realBriefing.briefing_md);
    title = parsed.title;
    acknowledgment = parsed.acknowledgment;
    paragraphs = parsed.paragraphs;
  } else {
    title = fixture.briefingTitle;
    acknowledgment = null;
    paragraphs = fixture.briefingParagraphs;
  }

  const isLast = briefingIndex >= promptCount;

  const advance = () => {
    const nextRoute = isLast ? '/final/prep/1' : `/briefing/${briefingIndex + 1}`;
    navigate(nextRoute, { state: { promptCount, includeRepeat } });
  };

  const swipeHandlers = useLeftSwipe(advance);

  return (
    <div
      className="h-dvh w-full bg-paper text-ink flex flex-col"
      {...swipeHandlers}
    >
      <div className="mx-auto w-full max-w-[420px] px-6 pt-8 pb-6 flex flex-col flex-1 min-h-0">
        {/* Progress dots */}
        <div className="flex justify-center gap-1.5">
          {Array.from({ length: promptCount }).map((_, i) => (
            <span
              key={i}
              className={[
                'block w-[18px] h-[2px] bg-ink',
                i === briefingIndex - 1 ? 'opacity-100' : 'opacity-25',
              ].join(' ')}
            />
          ))}
        </div>

        {/* Header */}
        <header className="mt-5 flex-shrink-0">
          <div className="tiny-label">
            Briefing · {briefingIndex} of {promptCount}
          </div>
          <h1 className="mt-1.5 text-[22px] font-bold tracking-[-0.025em] leading-[1.05]">
            {title}
          </h1>
        </header>

        {/* Body */}
        <main className="flex-1 mt-5 overflow-y-auto min-h-0">
          <div className="space-y-3.5 text-[17px] leading-[1.55] text-ink/85 max-w-[34ch] sm:max-w-[42ch]">
            {acknowledgment && (
              <p className="italic text-ink/95">{renderInline(acknowledgment)}</p>
            )}
            {paragraphs.map((para, i) => (
              <p key={i}>{renderInline(para)}</p>
            ))}
          </div>
        </main>

        {/* Footer */}
        <footer className="mt-5 flex justify-center flex-shrink-0">
          {isLast ? (
            <button
              onClick={advance}
              className="w-full max-w-[260px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80"
            >
              Final challenges →
            </button>
          ) : (
            <button
              onClick={advance}
              className="tiny-label opacity-50 px-4 py-2"
              aria-label={`Continue to briefing ${briefingIndex + 1}`}
            >
              Swipe ›
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
