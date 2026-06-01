import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, clearTodayCache, getMe, getToday, startToday } from '../lib/api';
import { timeUntilMidnight } from '../lib/time';
import type { MeResponse } from '../lib/types';

type PromptCount = 1 | 2 | 3;

const SETTINGS_KEY = 'uu.sessionSettings';

type StoredSettings = {
  promptCount: PromptCount;
  includeRepeat: boolean;
};

function loadSettings(): StoredSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { promptCount: 3, includeRepeat: false };
    const parsed = JSON.parse(raw) as Partial<StoredSettings>;
    return {
      promptCount: [1, 2, 3].includes(parsed.promptCount as number)
        ? (parsed.promptCount as PromptCount)
        : 3,
      includeRepeat: Boolean(parsed.includeRepeat),
    };
  } catch {
    return { promptCount: 3, includeRepeat: false };
  }
}

/**
 * Home routes by today's session state:
 *   today.exists === false                          → Fresh  (Begin → /countdown)
 *   today.exists === true && completed_at === null  → InProgress (Continue → /cold/prep/1)
 *   today.exists === true && completed_at !== null  → Done (terminal — no CTA)
 *
 * Continue always restarts at prompt 1 for now. Per-prompt resume needs
 * server-side recording state (Phase B, lands with the upload pipeline).
 */
export default function Home() {
  const navigate = useNavigate();

  const [{ promptCount, includeRepeat }, setSettings] = useState<StoredSettings>(loadSettings);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [beginning, setBeginning] = useState(false);
  const [beginError, setBeginError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(timeUntilMidnight);

  // Fetch /me on mount.
  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((data) => {
        if (!cancelled) setMe(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Refresh the "new unknowns in" countdown every minute (only displayed in Done state).
  useEffect(() => {
    const t = window.setInterval(() => setCountdown(timeUntilMidnight()), 60_000);
    return () => window.clearInterval(t);
  }, []);

  // Persist settings to localStorage.
  useEffect(() => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({ promptCount, includeRepeat }),
    );
  }, [promptCount, includeRepeat]);

  // Repeat toggle locks until the user has completed at least one prior day.
  const repeatLocked = me?.last_completed_date == null;

  useEffect(() => {
    if (repeatLocked && includeRepeat) {
      setSettings((s) => ({ ...s, includeRepeat: false }));
    }
  }, [repeatLocked, includeRepeat]);

  const todayDate = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const handleBegin = async () => {
    if (beginning) return;
    setBeginning(true);
    setBeginError(null);
    try {
      const session = await startToday(promptCount, includeRepeat);
      clearTodayCache();
      await getToday({ forceRefresh: true });
      navigate('/countdown', {
        state: {
          promptCount: session.prompt_count as PromptCount,
          includeRepeat: session.include_repeat,
        },
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Something went wrong.';
      setBeginError(message);
      setBeginning(false);
    }
  };

  const handleContinue = () => {
    if (!me || !me.today.exists) return;
    navigate('/cold/prep/1', {
      state: {
        promptCount: (me.today.prompt_count ?? 3) as PromptCount,
        includeRepeat: me.today.include_repeat ?? false,
      },
    });
  };

  // ----- derive view state -----
  const loading = me === null && loadError === null;
  const view: 'loading' | 'fresh' | 'in_progress' | 'done' = loading
    ? 'loading'
    : me?.today.exists && me.today.completed_at !== null
      ? 'done'
      : me?.today.exists
        ? 'in_progress'
        : 'fresh';

  const streak = me?.streak_count ?? 0;
  const streakLine =
    streak === 0 ? 'No streak yet' : `${streak}-day streak`;

  return (
    <div className="min-h-screen w-full bg-paper text-ink flex flex-col">
      <div className="mx-auto w-full max-w-[420px] px-6 pt-14 pb-10 flex flex-col flex-1">
        {/* Header — mark + wordmark (always shown) */}
        <header className="flex flex-col items-center">
          <div
            className="text-[34px] font-extrabold leading-none tracking-[-0.04em] select-none"
            aria-label="Unknown Unknowns"
          >
            UU
          </div>
          <div className="mt-1.5 tiny-label">Unknown Unknowns</div>
        </header>

        {view === 'loading' && (
          <main className="flex-1 flex items-center justify-center">
            <div className="tiny-label opacity-60">Loading today's session…</div>
          </main>
        )}

        {view === 'fresh' && (
          <>
            <main className="flex-1 flex flex-col gap-9 mt-14">
              <div>
                <div className="tiny-label">Today's session</div>
                <h1 className="mt-1.5 text-[28px] font-semibold leading-[1.05] tracking-[-0.02em]">
                  Today's unknowns
                </h1>
              </div>

              <section>
                <div className="tiny-label">Prompts</div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  {([1, 2, 3] as const).map((n) => {
                    const selected = promptCount === n;
                    return (
                      <button
                        key={n}
                        onClick={() => setSettings((s) => ({ ...s, promptCount: n }))}
                        className={[
                          'py-3.5 border-[1.5px] border-ink text-center font-semibold text-lg transition-colors',
                          selected ? 'bg-ink text-paper' : 'bg-paper text-ink',
                        ].join(' ')}
                        aria-pressed={selected}
                      >
                        {n}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section>
                <div className="tiny-label">Repeat a prior topic</div>
                <div
                  className={[
                    'mt-2 flex justify-between items-center py-3 border-t border-b border-ink',
                    repeatLocked ? 'opacity-40' : '',
                  ].join(' ')}
                >
                  <span className="text-[13px] font-medium tracking-[-0.01em]">
                    {repeatLocked ? 'Unlocks after your first day' : 'Include one'}
                  </span>
                  <button
                    onClick={() =>
                      !repeatLocked &&
                      setSettings((s) => ({ ...s, includeRepeat: !s.includeRepeat }))
                    }
                    disabled={repeatLocked}
                    aria-label="Include a repeat topic"
                    aria-pressed={includeRepeat}
                    className={[
                      'relative w-9 h-5 border-[1.5px] border-ink rounded-full transition-opacity',
                      repeatLocked ? 'cursor-not-allowed' : '',
                    ].join(' ')}
                  >
                    <span
                      className={[
                        'absolute top-[1px] w-[14px] h-[14px] bg-ink rounded-full transition-all duration-150',
                        includeRepeat ? 'left-[18px]' : 'left-[1px]',
                      ].join(' ')}
                    />
                  </button>
                </div>
              </section>

              {loadError && (
                <div className="text-[12px] leading-[1.45] opacity-70">
                  Couldn't reach the server: {loadError}. You can still try to start.
                </div>
              )}
            </main>

            <footer className="flex flex-col items-center gap-5 mt-10">
              <button
                onClick={handleBegin}
                disabled={beginning}
                className="w-full max-w-[220px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80 disabled:opacity-60"
              >
                {beginning ? 'Starting…' : 'Begin →'}
              </button>
              {beginError && (
                <div className="text-[11px] opacity-70 max-w-[260px] text-center">
                  {beginError}
                </div>
              )}
              <div className="flex flex-col items-center gap-1">
                <div className="text-[11px] font-medium tracking-[0.04em]">{streakLine}</div>
                <div className="tiny-label">{todayDate}</div>
              </div>
            </footer>
          </>
        )}

        {view === 'in_progress' && me?.today.exists && (
          <>
            <main className="flex-1 flex flex-col gap-7 mt-14">
              <div>
                <div className="tiny-label">Today's session</div>
                <h1 className="mt-1.5 text-[28px] font-semibold leading-[1.05] tracking-[-0.02em]">
                  In progress
                </h1>
              </div>

              <div className="text-[15px] leading-[1.5] text-ink/80">
                {me.today.prompt_count}
                {me.today.prompt_count === 1 ? ' prompt' : ' prompts'}
                {me.today.include_repeat ? ' · with a repeat' : ''}
              </div>
            </main>

            <footer className="flex flex-col items-center gap-5 mt-10">
              <button
                onClick={handleContinue}
                className="w-full max-w-[220px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80"
              >
                Continue →
              </button>
              <div className="flex flex-col items-center gap-1">
                <div className="text-[11px] font-medium tracking-[0.04em]">{streakLine}</div>
                <div className="tiny-label">{todayDate}</div>
              </div>
            </footer>
          </>
        )}

        {view === 'done' && (
          <>
            <main className="flex-1 flex flex-col items-center justify-center text-center gap-2">
              <div className="text-[24px] font-semibold tracking-[-0.025em] leading-[1.1]">
                Done for today.
              </div>
              <div className="mt-1 tiny-label opacity-50">
                New unknowns in {countdown}
              </div>
            </main>

            <footer className="flex flex-col items-center gap-1">
              <div className="text-[11px] font-medium tracking-[0.04em]">{streakLine}</div>
              <div className="tiny-label">{todayDate}</div>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
