# Prompt for Claude Design — Unknown Unknowns PWA

Copy everything below this line and paste into Claude Design.

---

I'm designing a mobile-first PWA called **Unknown Unknowns (UU)**. It's a daily learning app built around the Illusion of Explanatory Depth: each day the user records short verbal explanations of 2–3 prompts cold, reads briefings, then re-records on new angles of the same topics. Speaking forces linearization of thought, which exposes "I sort of know this" gaps that passive reading hides.

## Visual identity

**Uber-style. Pure black and white. Aggressive minimalism.** Heavy negative space. One sans-serif typeface for everything. No gradients, no drop shadows, no decorative chrome. Corners either sharp or *barely* rounded (4px max). If color appears at all, it's purposeful and singular — a single accent stroke or state indicator, not decoration.

The app should feel closer to a luxury financial product than a learning app. Confident, quiet, serious. Never cheerful in a way that papers over weakness, because the product is fundamentally about *cold honesty* — admitting what you don't know.

## Brand

- **Wordmark:** "Unknown Unknowns"
- **Logo:** a "UU" mark. Sharp geometric construction. Two letters, possibly overlapped, mirrored, or stacked. Should feel like a confident insignia. 2–3 directions please.

## Typography

- One sans-serif (suggest: Inter, Söhne, Neue Haas Grotesk, or your pick — explain why).
- Tight tracking on display sizes.
- Display sizes for: prompt text, countdown numbers, score numbers.
- Body size for: briefing markdown (long-form-publication treatment — generous line height, comfortable measure).
- UI label size for: settings, navigation, secondary metadata.

## Mobile-first

Designed for iPhone Safari, added to home screen as a PWA. Full-bleed black-or-white screens. Should feel like a focused tool, not a website. No browser chrome implied.

## Screens to design (in order)

**1. Home / Landing.** White background. UU logo top-center. Single primary CTA centered: **"Play today's game"** (open to better copy). Below the CTA, small text: streak count + today's date. If today is already complete, the CTA changes to a quiet "Completed — back tomorrow" state with the day's results visible below.

**2. Session settings.** Two large tap targets:
- Number of prompts: 1 / 2 / 3 (default 3)
- Toggle: "Include a repeat topic" (on/off, only available from day 2)
- A "Start" button.
Two taps max to start.

**3. Countdown.** Black background. Massive single number: "3" → "2" → "1" → "GO". Center-aligned, generous size. Single number on screen at a time.

**4. Prompt + 10s prep.** White background. Prompt rendered in *large* display type (e.g., "Why is the sky blue?"). Below the prompt: a circular countdown ring (10s) wrapped around the record button. Recording starts automatically when the ring completes — the transition should feel inevitable.

**5. Recording screen.** Black background. Maximalist recording state:
- Massive circular record indicator at center, breathing/pulsing subtly.
- Live waveform visualization driven by mic input (this is the key feedback element — makes it unambiguously clear audio is being captured).
- Elapsed time counter (target 60–90s).
- A single subtle "stop" affordance for early termination, not prominent.

**6. Repeat steps 4–5** for prompts 2 and 3.

**7. Briefing screens (3 total).** Clean transition into reading mode. White background. Markdown rendered with long-form-publication treatment: generous line height, comfortable measure (~65 characters), no decorative chrome. Each briefing is one screen, swipeable forward. Progress dots at top ("1 of 3", "2 of 3", "3 of 3"). Reading is the *point* of these screens — design should disappear.

**8. Final challenge screens.** Repeat the prompt → 10s prep → record flow (steps 4–5) for three "final challenge" prompts. These are new prompts on the same topics, designed to test transfer of what was just read.

**9. Score reveal — the climax.** This is the moment the design should peak at. For each topic (3 screens, swipeable):
- The topic title.
- The cold-recording score: 3–5 metrics (coverage, accuracy, structure, depth, clarity), each 1–10.
- The final-recording score: same metrics.
- The **delta** for each metric, prominently displayed.
- Animated number count-ups on reveal.
- Use a single accent color (or just heavier type weight) for improvement. If a metric went *down*, show it honestly — don't hide regressions; that's part of the cold-honesty principle.

**10. Completion.** "You're done for the day." Streak count + tomorrow's tease ("New topics unlock in [X hours]"). Quiet, confident close.

## UX principles to honor

- **The product is about cold honesty.** Design should never feel cheerful or congratulatory in a way that papers over weakness. Regressions are shown, not buried.
- **Recording moments should feel ritualistic** — big buttons, no easy backout, deliberate transitions. The countdown and prep-ring exist to set tone, not just gate the action.
- **Phase transitions should be deliberate.** The user should feel they're moving through a sequence (record → learn → re-record → reveal), not flipping between screens.
- **No gamification noise.** No badges, no level-ups, no confetti. The streak is enough.

## Deliverables

- High-fidelity mockups of every numbered screen above (iPhone Safari frame).
- 2–3 directions for the "UU" logo.
- Type system spec: typeface choice + sizes for display / body briefing / UI labels.
- Color system spec: black, white, and an accent (tell me what it is and where it's used).
- Motion / animation guidance for: countdown, recording pulse + waveform, briefing screen transitions, score reveal count-ups.

Ask anything that's ambiguous — copy in particular is up for grabs.
