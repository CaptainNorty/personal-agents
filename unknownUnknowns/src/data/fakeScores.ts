/**
 * Placeholder per-topic scores used while the backend scoring pipeline doesn't
 * exist yet. Each topic has a net delta and 5 metric scores (cold + final,
 * each 1–10, with explicit delta). Replace with content fetched from
 * /api/v1/uu/sessions/today/scores once the LLM grading is wired.
 *
 * Values mirror the wireframe storyboard:
 *   topic 1: improving (+1.4) with a clarity regression
 *   topic 2: mixed (+0.8) with a structure regression
 *   topic 3: net negative (−0.2) — three regressions, shown honestly
 */
export type MetricKey = 'Coverage' | 'Accuracy' | 'Structure' | 'Depth' | 'Clarity';

export type MetricScore = {
  label: MetricKey;
  cold: number;
  final: number;
  delta: number;
};

export type FakeScore = {
  netDelta: number;
  metrics: MetricScore[];
};

export const FAKE_SCORES: FakeScore[] = [
  {
    netDelta: 1.4,
    metrics: [
      { label: 'Coverage', cold: 4, final: 7, delta: 3 },
      { label: 'Accuracy', cold: 6, final: 8, delta: 2 },
      { label: 'Structure', cold: 5, final: 6, delta: 1 },
      { label: 'Depth', cold: 3, final: 5, delta: 2 },
      { label: 'Clarity', cold: 7, final: 6, delta: -1 },
    ],
  },
  {
    netDelta: 0.8,
    metrics: [
      { label: 'Coverage', cold: 5, final: 7, delta: 2 },
      { label: 'Accuracy', cold: 4, final: 6, delta: 2 },
      { label: 'Structure', cold: 6, final: 5, delta: -1 },
      { label: 'Depth', cold: 5, final: 6, delta: 1 },
      { label: 'Clarity', cold: 5, final: 6, delta: 1 },
    ],
  },
  {
    netDelta: -0.2,
    metrics: [
      { label: 'Coverage', cold: 6, final: 7, delta: 1 },
      { label: 'Accuracy', cold: 5, final: 4, delta: -1 },
      { label: 'Structure', cold: 6, final: 5, delta: -1 },
      { label: 'Depth', cold: 4, final: 5, delta: 1 },
      { label: 'Clarity', cold: 7, final: 6, delta: -1 },
    ],
  },
];
