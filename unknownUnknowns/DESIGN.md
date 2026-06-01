# Unknown Unknowns (UU) — Design & Architecture

A daily learning PWA built around the **Illusion of Explanatory Depth**: passive reading creates the feeling of understanding without the substance. Speaking forces linearization of thought, which exposes the gaps.

Each day, the user cold-records short explanations of 1–3 prompts, reads short briefings, then re-records new "final challenge" prompts on the same topics. Scoring is held until the end so the cold recordings stay cold.

---

## Product concept

- **Cold honesty over passive reading.** The 60–90 second cold recording is the IoED-busting mechanic. Everything else is built to preserve its purity.
- **Three prompt categories per day:** Cultural / Repeat / Technical.
  - *Cultural*: history, art, geography, civic knowledge, etc.
  - *Technical*: science, engineering, math, systems.
  - *Repeat*: a prompt from a prior day, used to track longitudinal improvement on the same input.
- **Briefings are hybrid: planned overnight, written in-the-moment.** The night before, we generate a tight **curriculum** for each topic — 4–5 bullet points that *must* be covered. After the cold recording, an LLM call takes `{ curriculum_bullets, cold_transcript }` and writes the full briefing — opening with 1–2 sentences acknowledging where the user landed relative to the curriculum ("you danced around the wavelength point but missed why violet doesn't dominate"), then teaching the bullets. The curriculum anchors quality so the briefing can't drift off the topic; the day-of generation gives the briefing the feel of a tutor responding, not a textbook. Acknowledgment stays **descriptive, never evaluative** — no previewed scores, no judgments leaked from the score reveal.
- **Final challenges test transfer, not memorization.** Each final challenge is a *new angle* on the same topic, answerable from the briefing. (E.g., briefing covers Rayleigh scattering; final challenge asks "so why is the sky not violet, since violet scatters even more?")
- **Scores are held until the very end.** All cold recordings → all briefings → all final challenges → THEN a climactic before/after score reveal across all topics.

---

## Daily user flow (locked in)

1. **Home / Landing.** Single CTA: "Play today's game." Streak count + date visible.
2. **Session settings.** User picks number of prompts (1 / 2 / 3, default 3) and toggles "include repeat topic" (on/off, available from day 2 onward). Defaults remember last choice.
3. **Countdown.** 3 → 2 → 1 → GO.
4. **Prompt 1, prep (10s) → record (60–90s).** Big animated record indicator with live waveform.
5. **Prompt 2, prep → record.** (Transcription of prompt 1 starts in background.)
6. **Prompt 3, prep → record.** (Transcription of prompt 2 starts in background.)
7. **Brief "preparing" beat.** Backend transcribes any remaining cold recordings and generates all N briefings in parallel from `{ curriculum_bullets, cold_transcript }`. Frontend polls; typically 5–15 seconds. Single wait moment for the whole batch, not N separate waits.
8. **Briefing 1 → Briefing 2 → Briefing 3.** Three swipeable markdown screens. This is the learning phase.
9. **Final Challenge 1, prep → record.**
10. **Final Challenge 2, prep → record.**
11. **Final Challenge 3, prep → record.**
12. **Scoring screen.** Background work: LLM scores all 6 recordings against the curricula in a single batched call.
13. **Score reveal.** For each topic: cold score vs final score across 3–5 metrics (coverage, accuracy, structure, depth, clarity), with deltas prominently displayed. Animated number count-ups. Regressions shown honestly.
14. **Completion.** "You're done for the day." Streak count + tomorrow's tease.

### Why this ordering

- **Recording all cold answers before any feedback** preserves the cold-honesty principle. If the user sees a score between prompts, they start *performing* instead of *revealing*.
- **Reading three briefings, then doing three final challenges** creates retrieval-practice interference — a desirable difficulty that improves durable retention (Bjork). Easier ordering (briefing → final → briefing → final) is less effective.
- **Saving scores for the end** turns the score reveal into the climactic moment of the session. It also lets us batch all LLM scoring into one call, cheaper and faster than per-prompt scoring.

---

## Variable session length

- **Prompt count: 1 / 2 / 3** (user picks at session start; default 3).
- **Repeat toggle:** on/off, only available day 2+.
- **Day 1 special case:** 2 prompts (cultural + technical), no repeat available. UX messaging makes the missing repeat slot feel earned ("come back tomorrow — your first repeat unlocks then").
- Backend always *generates* the full default (e.g., 3 prompts) the night before; the user chooses how many to consume.

---

## Perfect-score edge case (v1)

Even if the cold recording scores 10/10, the user still reads the briefing and does the final challenge. Reasons:
- LLM scoring is noisy; 10/10 ≠ perfect knowledge.
- Consistency of ritual is what makes daily habits stick.
- Branching paths create unpredictability, which is a habit-killer.

**v2+ idea:** "challenge mode" — high cold score triggers a harder final challenge ("explain to a hostile expert").

---

## End-of-session generation

When the user finishes today's score reveal, the backend kicks off generation of *tomorrow's* content:
- Pick topic categories (cultural / technical / repeat-from-history).
- Generate each cold prompt.
- Generate the **curriculum bullets** for each (a tight 4–5 point list — the concepts the briefing must cover). *Not* the full briefing prose; that's deferred until the day of, when we also have the cold transcript.
- Generate the final-challenge prompt for each, constrained to be answerable from the curriculum bullets.

**Why end-of-session instead of a nightly cron:**
- No timezone handling needed.
- No "did the user show up today?" check — if they didn't finish a session, no new content is generated, so they pick up where they left off.
- Simpler infra: no scheduler, no cron, no missed-run debugging.

---

## Architecture overview

| Layer | Tech | Notes |
|---|---|---|
| Frontend | Vite + React + `vite-plugin-pwa` | Mobile-first, installable to iOS home screen. |
| Hosting | Firebase Hosting | Free, HTTPS by default (required for `MediaRecorder` on iOS Safari). |
| Auth | Firebase Auth | Persistent login (refresh tokens in IndexedDB). User stays signed in until manual sign-out. |
| API | FastAPI (existing app) | New module: `app/unknownUnknowns/`. Sibling to `app/bots/`. |
| DB | AWS RDS (existing PostgreSQL) | New tables added via SQLAlchemy `Base.metadata.create_all()` on startup. |
| Audio storage | AWS S3 (new bucket) | Frontend uploads directly via presigned PUT URLs — bytes never touch FastAPI. |
| Transcription | Claude or Whisper | TBD; reuses patterns from existing `app/common/audio.py`. |
| Generation/Scoring | Claude via existing `app/common/llm.py` | Overnight: cold prompts + curriculum bullets + final prompts. Day-of: briefings (post-cold-record, parallel batch). End-of-day: scoring (single batched call across all 6 recordings). |

### Auth flow

1. Frontend uses Firebase Auth SDK; user signs in once (Google or email).
2. On each API request, frontend attaches `Authorization: Bearer <firebase_id_token>`.
3. Backend dependency (`app/common/auth.py`, new) verifies the token with Firebase Admin SDK, returns the `User` row keyed by Firebase UID.
4. Refresh token persists in IndexedDB → user stays logged in indefinitely.

### Upload flow

1. Frontend: `POST /api/v1/uu/uploads/presigned` → backend returns `{ url, s3_key }` valid for ~5 min.
2. Frontend: `PUT` the audio Blob directly to S3.
3. Frontend: `POST /api/v1/uu/recordings { s3_key, prompt_id, kind: "cold" | "final" }` → backend stores row, queues transcription.
4. Backend: transcribes from S3 key, stores transcript on the recording row.

**S3 doesn't use security groups** — it's IAM-attached, not network-attached. The bucket needs:
- Block public access ON.
- CORS configured for the frontend origin (allow `PUT`, `GET` from `https://*.web.app` or wherever).
- IAM user/role with `s3:PutObject`, `s3:GetObject` on the bucket.

---

## Database schema (initial sketch)

```python
# app/unknownUnknowns/models.py

class User(Base, BaseModel):
    firebase_uid: str (unique, indexed)
    email: str | None
    streak_count: int (default 0)
    last_completed_date: date | None
    prefs: JSONB  # last-chosen prompt count, repeat toggle, etc.

class DailySession(Base, BaseModel):
    user_id: FK -> User
    session_date: date (unique with user_id)
    completed_at: datetime | None

class Prompt(Base, BaseModel):
    session_id: FK -> DailySession
    category: enum("cultural", "technical", "repeat")
    order_index: int  # 0, 1, 2
    cold_prompt_text: str
    curriculum_bullets: JSONB  # generated overnight — list[str], 4-5 entries
    briefing_md: str | None    # generated post-cold-record from bullets + transcript
    briefing_generated_at: datetime | None
    final_prompt_text: str
    source_prompt_id: FK -> Prompt (nullable, set when category="repeat")

class Recording(Base, BaseModel):
    prompt_id: FK -> Prompt
    kind: enum("cold", "final")
    s3_key: str
    transcript: str | None
    transcribed_at: datetime | None

class Score(Base, BaseModel):
    recording_id: FK -> Recording (unique)
    coverage: int  # 1-10
    accuracy: int
    structure: int
    depth: int
    clarity: int
    notes_md: str  # personalized feedback
```

---

## API endpoints (initial sketch)

All routes mounted under `/api/v1/uu/` and protected by Firebase auth dependency.

| Method | Path | Purpose |
|---|---|---|
| GET | `/me` | Current user + streak + today's session state |
| POST | `/sessions/today/start` | Initialize today's session with chosen settings (prompt count, repeat on/off) |
| GET | `/sessions/today` | Get today's prompts (without briefings/final challenges leaked) |
| POST | `/uploads/presigned` | Get presigned S3 PUT URL |
| POST | `/recordings` | Register a recording (cold or final) for a prompt |
| POST | `/sessions/today/briefings/generate` | Kick off post-cold-record briefing generation (curriculum + transcripts → briefings, in parallel) |
| GET | `/sessions/today/briefings` | Poll: returns briefings once generated, or a `pending` status while the day-of LLM call is running |
| GET | `/sessions/today/final-prompts` | Get final challenge prompts (unlocked after all briefings viewed) |
| POST | `/sessions/today/complete` | Trigger scoring + generate tomorrow's content |
| GET | `/sessions/today/scores` | Get scored results for the reveal screen |

---

## Frontend visual direction

- **Uber-style.** Black and white. Aggressive minimalism. Heavy negative space.
- One sans-serif typeface. Generous sizes at key moments (prompt, countdown, score).
- No gradients, no shadows, no decorative chrome.
- Single accent color (TBD), used sparingly — for state changes, deltas in score reveal.
- The recording moment should feel ritualistic. Big record icon, breathing/pulsing animation, live waveform from `AudioContext.analyser`.

---

## Open questions / decisions deferred

- **Transcription provider:** Whisper API vs Claude vs other? Latency matters since scoring depends on transcripts being ready.
- **Topic source for prompts:** Pure LLM generation, or seeded from user interests / a curated topic pool? Topic quality is the product's ceiling.
- **What makes a prompt eligible for the "repeat" slot?** All past prompts, only ones the user scored below a threshold on, only ones N days old? v1 = random from any past prompt, refine later.
- **CORS tightening:** Currently `allow_origins=["*"]` in `app/main.py:39`. Tighten to deployed frontend origin before going live.
- **Logo:** "UU" mark — sharp geometric construction. Brief to be sent to Claude Design separately.
- **Sign-in UI:** Google sign-in only for v1, or also email? Single-button Google is the lowest-friction start.

---

## File layout (proposed)

```
personal-agents/
├── app/                          # existing FastAPI app
│   ├── unknownUnknowns/          # NEW: backend module for UU
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── router.py             # /api/v1/uu/* routes
│   │   ├── agent.py              # prompt/briefing/score generation
│   │   ├── generator.py          # end-of-session content generation
│   │   └── storage.py            # S3 presigned URL helpers
│   ├── common/
│   │   └── auth.py               # NEW: Firebase ID token verification dep
│   └── ...
├── unknownUnknowns/              # NEW: frontend PWA (Vite + React)
│   ├── DESIGN.md                 # this file
│   ├── package.json
│   ├── vite.config.ts
│   ├── public/
│   └── src/
└── ...
```
