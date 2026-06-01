/**
 * Typed client for the Unknown Unknowns backend.
 *
 * Calls go to `/api/v1/uu/*` and are proxied to the FastAPI server in dev
 * (see vite.config.ts). In prod the same paths will hit the deployed backend.
 *
 * Caching: `getToday()` results are kept in module memory and mirrored to
 * sessionStorage so multiple screens within the same session don't re-fetch,
 * and refresh recovers the cached prompts without a network round-trip.
 */

import { auth } from './firebase';
import type {
  BriefingGenerateResponse,
  BriefingsResponse,
  CompleteSessionResponse,
  MeResponse,
  ScoresResponse,
  ScoringGenerateResponse,
  SessionStartResponse,
  TodayFinalsResponse,
  TodaySessionResponse,
} from './types';

/** Base URL for UU endpoints. In dev (`npm run dev`), the default relative
 * path hits the Vite proxy → localhost:8000. In prod builds the
 * `.env.production` override points at the deployed backend. */
const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1/uu';
const TODAY_CACHE_KEY = 'uu.today';
const FINALS_CACHE_KEY = 'uu.finals';
const BRIEFINGS_CACHE_KEY = 'uu.briefings';
const SCORES_CACHE_KEY = 'uu.scores';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Attach Firebase ID token if the user is signed in. getIdToken auto-
  // refreshes if the cached token is near expiry (~5 min before).
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const user = auth.currentUser;
  if (user) {
    try {
      const token = await user.getIdToken();
      headers.Authorization = `Bearer ${token}`;
    } catch (err) {
      console.warn('[uu] getIdToken failed:', err);
    }
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(
      `${res.status} ${res.statusText}${body ? `: ${body}` : ''}`,
      res.status,
    );
  }
  return (await res.json()) as T;
}

/** Drop every cached response — used on sign-out so a new user doesn't see
 * the previous user's prompts/briefings/scores from sessionStorage. */
export function clearAllCaches(): void {
  clearTodayCache();
  clearFinalsCache();
  clearBriefingsCache();
  clearScoresCache();
}

export function getMe(): Promise<MeResponse> {
  return request<MeResponse>('/me');
}

export function startToday(
  promptCount: 1 | 2 | 3,
  includeRepeat: boolean,
): Promise<SessionStartResponse> {
  return request<SessionStartResponse>('/sessions/today/start', {
    method: 'POST',
    body: JSON.stringify({
      prompt_count: promptCount,
      include_repeat: includeRepeat,
    }),
  });
}

let todayCache: TodaySessionResponse | null = null;

function readStorage(): TodaySessionResponse | null {
  try {
    const raw = sessionStorage.getItem(TODAY_CACHE_KEY);
    return raw ? (JSON.parse(raw) as TodaySessionResponse) : null;
  } catch {
    return null;
  }
}

function writeStorage(data: TodaySessionResponse): void {
  try {
    sessionStorage.setItem(TODAY_CACHE_KEY, JSON.stringify(data));
  } catch {
    // sessionStorage can throw under quota / private mode — non-fatal.
  }
}

/** Synchronous read of the cache (memory or sessionStorage). Returns null if
 * nothing's cached. Useful for screens that want to render the prompt
 * immediately without showing a loading flash. */
export function peekToday(): TodaySessionResponse | null {
  if (todayCache) return todayCache;
  const stored = readStorage();
  if (stored) todayCache = stored;
  return todayCache;
}

export async function getToday(
  options: { forceRefresh?: boolean } = {},
): Promise<TodaySessionResponse> {
  if (!options.forceRefresh) {
    const cached = peekToday();
    if (cached) return cached;
  }
  const data = await request<TodaySessionResponse>('/sessions/today');
  todayCache = data;
  writeStorage(data);
  return data;
}

export function clearTodayCache(): void {
  todayCache = null;
  try {
    sessionStorage.removeItem(TODAY_CACHE_KEY);
  } catch {
    // non-fatal
  }
}

// ---------- Finals cache (mirror of today cache) ----------
//
// Same semantics: module memory + sessionStorage mirror, peek for sync read,
// async fetch that warms both. Populated on first read from any screen that
// needs final-challenge prompts.

let finalsCache: TodayFinalsResponse | null = null;

function readFinalsStorage(): TodayFinalsResponse | null {
  try {
    const raw = sessionStorage.getItem(FINALS_CACHE_KEY);
    return raw ? (JSON.parse(raw) as TodayFinalsResponse) : null;
  } catch {
    return null;
  }
}

function writeFinalsStorage(data: TodayFinalsResponse): void {
  try {
    sessionStorage.setItem(FINALS_CACHE_KEY, JSON.stringify(data));
  } catch {
    // non-fatal
  }
}

export function peekFinals(): TodayFinalsResponse | null {
  if (finalsCache) return finalsCache;
  const stored = readFinalsStorage();
  if (stored) finalsCache = stored;
  return finalsCache;
}

export async function getFinals(
  options: { forceRefresh?: boolean } = {},
): Promise<TodayFinalsResponse> {
  if (!options.forceRefresh) {
    const cached = peekFinals();
    if (cached) return cached;
  }
  const data = await request<TodayFinalsResponse>('/sessions/today/final-prompts');
  finalsCache = data;
  writeFinalsStorage(data);
  return data;
}

export function clearFinalsCache(): void {
  finalsCache = null;
  try {
    sessionStorage.removeItem(FINALS_CACHE_KEY);
  } catch {
    // non-fatal
  }
}

// ---------- Briefings cache + poll-friendly helpers ----------

let briefingsCache: BriefingsResponse | null = null;

function readBriefingsStorage(): BriefingsResponse | null {
  try {
    const raw = sessionStorage.getItem(BRIEFINGS_CACHE_KEY);
    return raw ? (JSON.parse(raw) as BriefingsResponse) : null;
  } catch {
    return null;
  }
}

function writeBriefingsStorage(data: BriefingsResponse): void {
  try {
    sessionStorage.setItem(BRIEFINGS_CACHE_KEY, JSON.stringify(data));
  } catch {
    // non-fatal
  }
}

/** Synchronous read — used by Briefing.tsx to render immediately on mount. */
export function peekBriefings(): BriefingsResponse | null {
  if (briefingsCache) return briefingsCache;
  const stored = readBriefingsStorage();
  if (stored && stored.status === 'complete') {
    briefingsCache = stored;
  }
  return briefingsCache;
}

/** Fetch /sessions/today/briefings. Pass forceRefresh during polling so the
 * cache doesn't serve a stale `pending` response forever. */
export async function getBriefings(
  options: { forceRefresh?: boolean } = {},
): Promise<BriefingsResponse> {
  if (!options.forceRefresh) {
    const cached = peekBriefings();
    if (cached && cached.status === 'complete') return cached;
  }
  const data = await request<BriefingsResponse>('/sessions/today/briefings');
  if (data.status === 'complete') {
    briefingsCache = data;
    writeBriefingsStorage(data);
  }
  return data;
}

/** Kick off post-cold-record briefing generation. Returns immediately —
 * background generation runs server-side; caller polls getBriefings. */
export function kickOffBriefingGeneration(): Promise<BriefingGenerateResponse> {
  return request<BriefingGenerateResponse>('/sessions/today/briefings/generate', {
    method: 'POST',
  });
}

export function clearBriefingsCache(): void {
  briefingsCache = null;
  try {
    sessionStorage.removeItem(BRIEFINGS_CACHE_KEY);
  } catch {
    // non-fatal
  }
}

/** Mark today's session done + kick off tomorrow's content generation
 * (background on the server). Fire-and-forget from the Done screen. */
export function completeSession(): Promise<CompleteSessionResponse> {
  return request<CompleteSessionResponse>('/sessions/today/complete', {
    method: 'POST',
  });
}

// ---------- Scores cache + poll-friendly helpers ----------

let scoresCache: ScoresResponse | null = null;

function readScoresStorage(): ScoresResponse | null {
  try {
    const raw = sessionStorage.getItem(SCORES_CACHE_KEY);
    return raw ? (JSON.parse(raw) as ScoresResponse) : null;
  } catch {
    return null;
  }
}

function writeScoresStorage(data: ScoresResponse): void {
  try {
    sessionStorage.setItem(SCORES_CACHE_KEY, JSON.stringify(data));
  } catch {
    // non-fatal
  }
}

export function peekScores(): ScoresResponse | null {
  if (scoresCache) return scoresCache;
  const stored = readScoresStorage();
  if (stored && stored.status === 'complete') scoresCache = stored;
  return scoresCache;
}

export async function getScores(
  options: { forceRefresh?: boolean } = {},
): Promise<ScoresResponse> {
  if (!options.forceRefresh) {
    const cached = peekScores();
    if (cached && cached.status === 'complete') return cached;
  }
  const data = await request<ScoresResponse>('/sessions/today/scores');
  if (data.status === 'complete') {
    scoresCache = data;
    writeScoresStorage(data);
  }
  return data;
}

export function kickOffScoring(): Promise<ScoringGenerateResponse> {
  return request<ScoringGenerateResponse>('/sessions/today/scores/generate', {
    method: 'POST',
  });
}

export function clearScoresCache(): void {
  scoresCache = null;
  try {
    sessionStorage.removeItem(SCORES_CACHE_KEY);
  } catch {
    // non-fatal
  }
}

// ---------- Recording upload ----------

type PresignedResponse = {
  upload_url: string;
  s3_key: string;
  expires_in_seconds: number;
};

type RecordingResponse = {
  recording_id: string;
  transcription_status: 'pending' | 'completed';
};

/**
 * Upload a recorded audio blob end-to-end:
 *   1. POST /uploads/presigned → presigned PUT URL + s3_key
 *   2. PUT the blob directly to S3 (bytes never touch FastAPI)
 *   3. POST /recordings → backend registers the row + kicks off transcription
 *
 * Caller is expected to handle (or ignore) errors; this is typically called
 * fire-and-forget from a MediaRecorder onstop handler after the user has
 * already navigated to the next screen.
 */
export async function uploadRecording(
  promptId: string,
  kind: 'cold' | 'final',
  blob: Blob,
): Promise<RecordingResponse> {
  const presigned = await request<PresignedResponse>('/uploads/presigned', {
    method: 'POST',
    body: JSON.stringify({ prompt_id: promptId, kind }),
  });

  const putResponse = await fetch(presigned.upload_url, {
    method: 'PUT',
    body: blob,
    headers: blob.type ? { 'Content-Type': blob.type } : {},
  });
  if (!putResponse.ok) {
    const body = await putResponse.text().catch(() => '');
    throw new Error(
      `S3 PUT failed: ${putResponse.status} ${putResponse.statusText}` +
        (body ? ` — ${body.slice(0, 200)}` : ''),
    );
  }

  return request<RecordingResponse>('/recordings', {
    method: 'POST',
    body: JSON.stringify({
      prompt_id: promptId,
      kind,
      s3_key: presigned.s3_key,
    }),
  });
}
