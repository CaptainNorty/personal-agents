/**
 * Placeholder topic content. Each topic carries the cold prompt, the briefing,
 * and the final-challenge prompt (a *new angle* on the same topic, answerable
 * from the briefing — tests transfer, not recall).
 *
 * Replace with content fetched from /api/v1/uu/sessions/today once the backend
 * generation pipeline is wired up.
 *
 * `briefingParagraphs` may include *italic* markers — rendered inline by
 * Briefing.tsx.
 */
export type FakeTopic = {
  topicTitle: string;
  coldPrompt: string;
  finalPrompt: string;
  briefingTitle: string;
  briefingParagraphs: string[];
};

export const FAKE_TOPICS: FakeTopic[] = [
  {
    topicTitle: 'Why the sky is blue',
    coldPrompt: 'Why is the sky blue?',
    finalPrompt: 'Why does the sun look red at sunset?',
    briefingTitle: 'Rayleigh scattering & the blue sky',
    briefingParagraphs: [
      'The sky is blue not because air is blue, but because air *scatters* short wavelengths much more aggressively than long ones. The effect is called Rayleigh scattering.',
      "When sunlight enters the atmosphere, photons collide with nitrogen and oxygen molecules — particles vastly smaller than the wavelength of visible light. Rayleigh's law says scattering intensity scales as 1/λ⁴, which means blue light (~470nm) is scattered about ten times more than red (~700nm).",
      'The sky looks blue rather than violet — even though violet scatters more — because the sun emits less violet, our eyes are less sensitive to it, and some of it is absorbed in the upper atmosphere.',
      'At sunset, sunlight travels through a much longer column of air to reach you. The blue has already scattered out sideways into other patches of sky, leaving the reds and oranges to dominate the direct path.',
    ],
  },
  {
    topicTitle: 'Entropy, briefly',
    coldPrompt: 'What is entropy?',
    finalPrompt:
      'If entropy always increases, how did the universe start in such a low-entropy state?',
    briefingTitle: 'Entropy, briefly',
    briefingParagraphs: [
      'Entropy is, at root, a count: the number of microscopic configurations a system could be in while still looking the same macroscopically. A shuffled deck has more possible orderings than a sorted one, so it has higher entropy.',
      'The second law of thermodynamics says that the total entropy of an isolated system tends to *increase* over time. It is not a fundamental law in the way conservation of energy is — it is a statistical one. Going from low-entropy to high-entropy states is overwhelmingly more likely simply because there are so many more high-entropy configurations available.',
      'This statistical asymmetry is widely thought to be the source of the *arrow of time* — why we remember the past and not the future, why eggs scramble but do not unscramble.',
      'A common slogan is "entropy is disorder," which is loose. More precisely: entropy is uncertainty about microscopic state given a macroscopic description. Sometimes this lines up with what we intuitively call disorder; sometimes it does not.',
    ],
  },
  {
    topicTitle: 'Treaty of Westphalia',
    coldPrompt: 'What was the Treaty of Westphalia?',
    finalPrompt:
      'Why did later historians call Westphalia the birth of state sovereignty if the treaties did not say so?',
    briefingTitle: 'Westphalia: state sovereignty, 1648',
    briefingParagraphs: [
      "The Peace of Westphalia (1648) was actually two treaties — Münster and Osnabrück — that ended the Thirty Years' War, the most destructive European conflict before the twentieth century.",
      "It is often credited, somewhat too cleanly, with founding the modern state system. What it actually did was acknowledge *cuius regio, eius religio* — rulers, not popes, would determine religious practice within their borders — and extend that principle to the empire's many smaller polities.",
      "The cleaner claim, made by later historians and political theorists, is that Westphalia established the principle of *state sovereignty*: that political authority is bounded by territory, and that other states should not intervene in a state's internal affairs.",
      'Critics point out that "Westphalian sovereignty" as a coherent doctrine was largely retrofitted in the 19th and 20th centuries. The actual 1648 settlements were messier — about Protestant rights and Habsburg power as much as any general principle.',
    ],
  },
];
