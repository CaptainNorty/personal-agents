# Progressive Briefings & Scores — Code Plan (IDEAS #5)

Show briefing 1 the moment it's ready while 2 & 3 keep generating; let the
user tab between them via buttons at the top that double as a
ready/generating indicator. Same treatment for scores. Written to also
handle the future **One Daily Challenge** shape (count = 1).

## TL;DR
- **Backend: no changes.** `GET /sessions/today/briefings` and
  `/sessions/today/scores` already return per-item readiness
  (`briefing_md !== null` / `is_ready`) plus `status: pending|partial|complete`
  and `pending_count`. Everything we need is on the wire.
- **Frontend: restructure** the briefing and score phases from "gate until all
  ready → one screen per index (remounted per index)" into a **persistent flow
  container** that holds the polled list and renders the current index from the
  URL. This is what lets polling state survive tab-switching, and what makes
  the count-agnostic (1 vs 3) behavior fall out for free.

## Current behavior (why it blocks)
- `PreparingBriefings.tsx` polls and only navigates to `/briefing/1` when
  `status === 'complete'` — i.e. **all** briefings done. Same for
  `PreparingScores.tsx` → `/scores/1`.
- `App.tsx` wraps `Briefing`/`Score` in `BriefingByIndex`/`ScoreByIndex` with
  `key={index}` to **force a remount per index**. That deliberately throws away
  component state between `/briefing/1` → `/briefing/2`, so any polling started
  in the screen dies on navigation.
- `Briefing.tsx` / `Score.tsx` fetch once on mount; if the item isn't ready they
  fall back to **fixture content** (`FAKE_TOPICS` / `FAKE_SCORES`), which would
  silently show fake data instead of a real "still generating" state.

## Target behavior
1. Enter the flow as soon as the **first** item (order_index 0) is ready — not
   when all are.
2. A **top nav row of pills**, one per item, that is simultaneously: the
   progress indicator, the readiness indicator (ready vs still-generating), and
   the navigator (tap a ready pill to jump to it). Replaces the current dots.
3. The current page renders real content if ready, else an inline
   **"writing this briefing…/scoring…"** state (thinking dots), and lights up
   automatically when it lands (polling keeps running in the container).
4. Footer is a real **Continue** button (folds in IDEAS #2 for these screens):
   enabled when the next item is ready, otherwise a disabled "next is still
   being written…" that auto-enables when it lands. Last item → "Final
   challenges →" / "Continue ›".
5. **Count-agnostic.** Everything drives off the server list length, so count=1
   (One Daily Challenge) collapses cleanly: no pills, single page, direct
   continue. count=2/3 work the same way with 2/3 pills.

## Architecture change: persistent flow containers

Replace per-index remounting with one mounted container per phase that reads
`:index` from the URL.

```
/briefing/:index  → <BriefingFlow/>   (mounted once for the whole phase)
/scores/:index    → <ScoreFlow/>      (mounted once for the whole phase)
```

`BriefingFlow` owns:
- `items` (the polled `BriefingItem[]`), `status`, `pendingCount`
- the **polling loop** (forceRefresh every 2s until `status==='complete'` or
  max-wait), started on mount, surviving index changes because the instance is
  not remounted when only the route param changes
- one-time `kickOffBriefingGeneration()` on mount (idempotent server-side)

It renders:
- `<SegmentNav items=… current=… onSelect=…/>` (shared component, see below)
- `<BriefingPage key={index} item={items[index-1] ?? null} …/>` — keyed by
  index so the read-animation/scroll resets per page, but the *container's*
  poll state persists.

`ScoreFlow` is the exact analog with `TopicScoreItem[]` and `is_ready`.

> Because React Router keeps the same element mounted when only `:index`
> changes, we **delete the `key={index}` wrappers** (`BriefingByIndex` /
> `ScoreByIndex`) in `App.tsx`. The per-page reset moves to the inner
> `key={index}` on `<BriefingPage>` / `<ScorePage>`.

## New shared component: `SegmentNav`
`src/components/SegmentNav.tsx`

```ts
type Segment = { index: number; ready: boolean; label?: string };
type Props = {
  segments: Segment[];
  current: number;          // 1-based
  onSelect: (index: number) => void;
};
```
- Renders a centered row of pills. States:
  - **current**: filled/high-contrast
  - **ready, not current**: outlined, tappable
  - **generating**: dimmed + tiny pulsing dot, `disabled`
- `segments.length <= 1` → render nothing (One Daily Challenge: no nav needed).
- Used by both `BriefingFlow` and `ScoreFlow`. Replaces the two ad-hoc
  "progress dots" blocks currently duplicated in `Briefing.tsx`/`Score.tsx`.

## New shared hook: polling
`src/lib/useProgressivePoll.ts` (or two thin wrappers in `api.ts`)

```ts
useProgressivePoll<T>({
  fetch: (opts:{forceRefresh:boolean}) => Promise<{items:T[]; status:Status}>,
  isComplete: (s:Status)=> s==='complete',
  intervalMs: 2000,
  maxWaitMs,
}) => { items, status, error, retry }
```
- Polls with `forceRefresh:true` until complete or timeout; stops on complete.
- Returns the latest `items` so pills + current page reflect newest readiness.
- Briefings maxWait ~180s, scores ~240s (mirror current constants).

`getBriefings`/`getScores` already cache only when complete — fine. (Optional
nicety: also cache `partial` so a mid-flow refresh repaints pills instantly;
not required, container refetches on mount in <1s.)

## File-by-file changes

### `src/App.tsx`
- Remove `BriefingByIndex` / `ScoreByIndex` wrappers (and the `key` hack).
- Routes become `:index → <BriefingFlow/>` and `:index → <ScoreFlow/>`.

### `src/screens/PreparingBriefings.tsx`
- Change the gate: navigate to `/briefing/1` as soon as the **first** briefing
  is ready (`data.briefings[0]?.briefing_md != null`, equivalently
  `status !== 'pending'`) instead of `status === 'complete'`.
- Keep firing `kickOffBriefingGeneration()` + the "N of M ready" beat.
- (BriefingFlow continues polling for the rest after handoff.)
- *Alternative considered:* drop this screen entirely and show briefing 1's
  generating state inline in BriefingFlow. Keeping the screen is the smaller,
  lower-risk change and preserves the branded "preparing" beat; recommend
  keeping it.

### `src/screens/PreparingScores.tsx`
- Same one-line gate change: hand off on first `is_ready` (`status !== 'pending'`)
  instead of `complete`.

### `src/screens/Briefing.tsx` → split into `BriefingFlow.tsx` + `BriefingPage.tsx`
- `BriefingFlow`: owns poll + kickoff; derives `total` from
  `max(items.length, state.promptCount ?? 1)`; renders `SegmentNav` + current
  `BriefingPage`.
- `BriefingPage`: pure presentation of one `BriefingItem | null`:
  - ready → existing `parseBriefingMd` + render (unchanged markup/animation)
  - not ready → inline "Writing this briefing…" (thinking-dots, same visual
    language as PreparingBriefings)
  - **Remove the `FAKE_TOPICS` fallback from the live path** (it masks real
    state). Keep fixtures for dev/storybook only.
- Footer: `Continue` button.
  - next ready → enabled, navigates `/briefing/{i+1}`
  - next not ready → disabled "Next briefing is still being written…" + dot;
    auto-enables when poll flips it ready
  - last index → "Final challenges →" (always enabled; finals don't depend on
    briefings)
- Swipe (`useLeftSwipe`): gate so it only advances when next is ready.

### `src/screens/Score.tsx` → split into `ScoreFlow.tsx` + `ScorePage.tsx`
- Same structure with `TopicScoreItem` / `is_ready`.
- `ScorePage` not ready → "Scoring this topic…" inline state (keep the count-up
  animations once real data lands).
- Remove `FAKE_SCORES` from the live path.
- Footer `Continue`; last → "Continue ›" → `/done`.

### `src/lib/types.ts`
- No changes (shapes already carry readiness + status).

### `src/lib/api.ts`
- No required changes. Optional: cache `partial` responses too (see above).

## One Daily Challenge (count = 1) — how each piece collapses
- Server returns a 1-element `briefings`/`scores` list → `total = 1`.
- `SegmentNav` returns null (≤1 segment) → no tab row, no back/forth.
- Flow renders the single page; footer is the terminal action
  ("Final challenge →" / "Continue ›").
- `PreparingBriefings/Scores` "first ready == only ready == complete" → handoff
  works unchanged.
- Nothing hardcodes 3; `promptCount` from `location.state` is only a *fallback*
  for `total` before the first fetch. (If we later make the daily challenge
  global/shared content, that's a content-generation change; this UI already
  won't care how many items come back.)

## Edge cases & decisions
- **Out-of-order readiness** (briefing 2 ready before 1): pills reflect actual
  readiness; we still *land* on index 1 first (read-in-order). A later pill that
  isn't ready is disabled until it lands.
- **Refresh mid-flow**: container refetches on mount; pills show generating for
  ~<1s until first response. (Optional partial-cache removes even that flicker.)
- **Timeout / error**: keep the existing retry affordance, surfaced in the flow
  (per-page generating state escalates to a "tap to retry" after maxWait).
- **Direct deep-link to `/briefing/3`** before it's ready: shows that page's
  generating state; pill for 3 disabled-but-current; auto-renders on land.
- **IDEAS #2 (Swipe→Continue)** is folded in for these two screens as a
  byproduct of the footer rewrite. The Record screen's version was already done
  separately.

## Implementation order (incremental, each step shippable)
1. `SegmentNav` component (pure, testable in isolation).
2. `useProgressivePoll` hook.
3. `BriefingFlow` + `BriefingPage`; wire route; delete `BriefingByIndex`.
4. Flip `PreparingBriefings` gate to first-ready.
5. Repeat 3–4 for `ScoreFlow`/`ScorePage` + `PreparingScores`.
6. Remove fixture fallbacks from live paths.
7. `npx tsc --noEmit` + manual run: 3-prompt happy path, slow-#2 path
   (verify #1 shows while #2 pill spins, then #2 lights up), refresh mid-flow,
   and a simulated count=1 session.

## Test checklist
- [ ] 3-prompt: land on briefing 1 before 2/3 done; pills show 2/3 generating.
- [ ] Tap a generating pill = no-op; tap a ready pill = jumps; current keeps
      polling and lights remaining pills.
- [ ] Footer Continue disabled until next ready, then enables itself.
- [ ] Scores mirror all of the above.
- [ ] count=1: no pills, single page, direct terminal Continue.
- [ ] Refresh on `/briefing/2` recovers without showing fixtures.
- [ ] `tsc --noEmit` clean.
```
