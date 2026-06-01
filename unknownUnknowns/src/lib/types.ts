/**
 * TypeScript mirrors of the backend Pydantic schemas in
 * `app/unknownUnknowns/schemas.py`. Keep snake_case to match wire format
 * directly — no remapping at the boundary.
 */

export type TodaySessionState = {
  exists: boolean;
  prompt_count: number | null;
  include_repeat: boolean | null;
  completed_at: string | null;
};

export type MeResponse = {
  user_id: string;
  email: string | null;
  streak_count: number;
  last_completed_date: string | null; // ISO date (YYYY-MM-DD)
  prefs: Record<string, unknown>;
  today: TodaySessionState;
};

export type SessionStartRequest = {
  prompt_count: 1 | 2 | 3;
  include_repeat: boolean;
};

export type SessionStartResponse = {
  session_id: string;
  session_date: string; // ISO date
  prompt_count: number;
  include_repeat: boolean;
};

export type PromptItem = {
  id: string;
  order_index: number;
  category: string;
  cold_prompt_text: string;
};

export type TodaySessionResponse = {
  session_id: string;
  prompts: PromptItem[];
};

export type FinalPromptItem = {
  id: string;
  order_index: number;
  category: string;
  final_prompt_text: string;
};

export type TodayFinalsResponse = {
  session_id: string;
  prompts: FinalPromptItem[];
};

export type BriefingItem = {
  prompt_id: string;
  order_index: number;
  briefing_md: string | null;
  generated_at: string | null;
};

export type BriefingsResponse = {
  session_id: string;
  briefings: BriefingItem[];
  pending_count: number;
  status: 'pending' | 'partial' | 'complete';
};

export type BriefingGenerateResponse = {
  status: 'started' | 'complete';
  pending_count: number;
};

export type CompleteSessionResponse = {
  completed_at: string;
  streak_count: number;
  next_content_status: 'scheduled' | 'already_present' | 'skipped';
};

export type MetricLabel =
  | 'Coverage'
  | 'Accuracy'
  | 'Structure'
  | 'Depth'
  | 'Clarity';

export type MetricScoreItem = {
  label: MetricLabel;
  cold: number;
  final: number;
  delta: number;
};

export type TopicScoreItem = {
  prompt_id: string;
  order_index: number;
  topic_title: string;
  metrics: MetricScoreItem[];
  net_delta: number | null;
  notes_md: string | null;
  is_ready: boolean;
};

export type ScoresResponse = {
  session_id: string;
  scores: TopicScoreItem[];
  pending_count: number;
  status: 'pending' | 'partial' | 'complete';
};

export type ScoringGenerateResponse = {
  status: 'started' | 'complete';
  pending_count: number;
};
