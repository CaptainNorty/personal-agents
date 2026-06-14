import { Fragment, type ReactNode } from 'react';

/** Minimal inline-italic renderer: *foo* → <em>foo</em>.
 * Shared by the briefing and score screens. */
export function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*[^*\n]+\*)/g);
  return parts.map((part, i) => {
    if (part.length > 2 && part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}
