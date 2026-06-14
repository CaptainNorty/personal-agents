# UnknownUnknowns — Ideas / TODO before sharing with friends & family

## 1. Final challenge grading mismatch
The final challenge recording is currently judged against the **same criteria as the first prompt**, even though it's a different question. This produces unfair deductions.

**Example:** First prompt is *"Why is the sky blue?"* — I answer well, explaining Rayleigh scattering and the 1/λ⁴ dependence. Final prompt is *"So why is the sky red at sunset?"* — I answer the follow-up but don't re-mention 1/λ⁴, and get docked points for omitting it, even though I covered it in the first answer.

**Open question:** Should the final challenge measure:
- (a) my ability to answer the **first question** again (i.e. carry forward all prior criteria), or
- (b) **just the follow-up** on its own merits (criteria regenerated for the new question)?

Need to decide which before fixing.

## 2. Replace "Swipe" with a "Continue" button
The markdown pages (and I think the score screens) say **"SWIPE"**, but the interaction is actually a tap — no swipe needed. Swap the "Swipe" affordance for a button labeled **"Continue"**.

## 3. Daily Challenge + Leaderboard (idea, not a must-fix)
Everyone in the world gets the **same question on the same day**, and scores appear on a leaderboard on the home page. Turns the daily session into a shared/competitive moment.

## 4. History on the home page (idea)
Let users scroll a history on the home page — e.g. "you answered two days ago, yesterday, today." Open question: do we **reveal the questions/topics** in the history, or **obfuscate** them (so users don't get spoilers if they share devices / talk with friends)? Design depends on which way we go.

## 5. Progressive briefings & scores (P1)
Today the app shows a loading state for the markdown briefings even when 2 of 3 have already been generated. Same pattern on scores — you have to wait for all final challenges to be graded before you can see any.

**Desired behavior:** as soon as the first briefing is ready, show it. At the top of the page indicate that briefings 2 and 3 are still transcribing/evaluating, and let the user tab back and forth between briefings as they come in. Same exact treatment for scores — surface the first final challenge's score as soon as it's graded; don't block on the others.

## 6. New home page: Daily Challenge + topic-specific dailies
Reimagine the home page with **"Daily Challenge"** at the top, and below it a **horizontally-scrolling row** of topic-specific daily questions:
- Daily history challenge
- Daily Fermi problem
- Daily pop culture question
- Daily literature question
- Daily software engineering challenge
- …etc.

Intent: the **main Daily Challenge** is the headline thing everyone does, and the topic dailies are optional extras for users who want more.

## 7. "Today's Results" section on home page
Home page shows a **Today's Results** section listing the prompts the user answered today alongside their scores. Quick recap of the day without digging into history. (Related to [[idea 4 history]] but scoped to *today only*.)

## 8. Default prompt count to 2 instead of 3
On the home page, change the default selection from **3 prompts → 2 prompts**. Three prompts can take 10+ minutes end-to-end, which is overwhelming for first-time users. Two is a friendlier on-ramp; power users can still bump to 3.

## 9. `last_completed_date` UTC bug (investigate)
Double-check how `last_completed_date` is being populated. Repro: completed 3 questions **last night**, but the database shows **today's date** as my `last_completed_date`. Smells like a UTC vs. local-timezone issue — likely storing the UTC date at write time instead of the user's local date. (Note: there was a recent "Fixed Timezone Issue" commit — verify whether this path was covered or is a separate code site.)

## 10. Admin/owner-only views (for Adam)
A separate home page — or extra tabs only visible to me — exposing operational/owner views, e.g.:
- **All users + streaks** — see who's playing and how consistently.
- **Stats** — aggregate usage, completion rates, score distributions, etc.
- **"New user" preview** — render the home page as a brand-new user would see it, even after I've already completed today's questions (so I can QA the first-run experience without resetting my account).

Gate by user identity (just me) rather than a separate build.

## 11. Replace "Tap and Hold to Finish Recording" with an explicit confirm flow
The current **"Tap and Hold to Finish Recording"** gesture is too finicky — easy to think you're done when you're not (this is probably also why the first-answer submit felt broken to me).

**New flow:**
1. While recording, show a single **"I'm done"** button.
2. On tap, replace it with **two side-by-side buttons**:
   - **"Not done yet"** — secondary style
   - **"Continue"** — primary action button (primary styling)
3. Recording screen background is black, so the buttons should probably both be white-on-black, with the primary distinguished by fill/weight rather than color hue.

Removes the hold gesture entirely in favor of an explicit two-tap confirm.

## 12. Rework the scores page / scoring model
The scores page is **not great** — it's unclear how the scoring actually works. This is entangled with [[idea 1 final-challenge grading mismatch]] — until we decide what the final challenge is measuring, the score display can't really land.

**One proposal:** combine before & after scores per category and divide by 2 → final score out of 10 in each category.
- *Downside:* if you bomb the first question (0s) but nail the final, you cap at **5/10** in each category. That feels punishing and probably isn't the message we want.

**Not sold on this model** — needs more thought. Options to explore:
- Show before/after separately rather than collapsing.
- Weight the final more heavily (e.g. 30/70) so improvement is rewarded.
- Score the final only against follow-up-specific criteria (per option (b) in [[idea 1]]) and show "delta" instead of an averaged number.

## 13. Share results
A **Share** button on the results screen that copies a shareable summary to the clipboard — something the user can paste into a text/DM to friends. (Think Wordle-style spoiler-free recap: scores per category, maybe topic, no answers given away. Exact format TBD.)

## 14. First-time user onboarding / explainer page
If a user has **never done this before**, show a short explainer page first that walks through the loop:
1. **Record your answer** to the prompt.
2. **Read the briefing** generated from your answer.
3. **Answer the final question** — an adjacent follow-up to the first.

Shown once on first run; skippable / dismissible after.

## 15. Safari (iOS) sign-in failure: "missing initial state" (bug)
A user trying to sign in on **Safari on his phone** saw:

> Unable to process request due to missing initial state. This may happen if browser sessionStorage is inaccessible or accidentally cleared. Some specific scenarios are - 1) Using IDP-Initiated SAML SSO. 2) Using signInWithRedirect in a storage-partitioned browser environment.

This is a **Firebase Auth** error. iOS Safari partitions/clears `sessionStorage`, which breaks `signInWithRedirect` (the redirect flow can't recover its initial state). Fixes to investigate:
- Switch to **`signInWithPopup`** instead of `signInWithRedirect` (popup avoids the storage-partition round-trip).
- Or follow Firebase's [guidance for signInWithRedirect in storage-partitioned browsers](https://firebase.google.com/docs/auth/web/redirect-best-practices) (host auth on the same domain / proxy the `__/auth/` handlers so it's first-party).
- Verify our auth helper isn't being torn down before the redirect resolves.

## 16. Speed up transcription by parallel-chunking the audio (perf)
First prompt took **~3 minutes** to load for a user. His suggestion (which he's done on another project):

> If you're having it transcribe, one thing you can do is split up the audio file and have multiple processes transcribe and then just combine the result strings and then send the result in for LLM processing. I had to do this for a different project and it was way faster.

I.e. **split the recording into chunks, transcribe them in parallel, concatenate the result strings in order, then send the combined transcript into the LLM step.** Should cut perceived latency significantly. Pairs well with [[idea 5 progressive briefings]] (show each briefing as soon as it's ready). Watch for: chunk boundaries cutting words mid-syllable (use small overlaps or silence-based splits), and preserving ordering when combining.
