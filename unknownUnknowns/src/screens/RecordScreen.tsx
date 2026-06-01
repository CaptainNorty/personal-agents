import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  getFinals,
  getToday,
  peekFinals,
  peekToday,
  uploadRecording,
} from '../lib/api';
import { FAKE_TOPICS } from '../data/fakeTopics';

const MAX_RECORDING_MS = 90_000;
const HOLD_TO_END_MS = 800;
const SPIKE_COUNT = 12;
const MIN_SPIKE_LEN = 8;
const MAX_SPIKE_LEN = 30;

type Phase = 'cold' | 'final';

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

type Status = 'preparing' | 'recording' | 'stopping' | 'denied';

type Props = {
  phase: Phase;
};

export default function RecordScreen({ phase }: Props) {
  const { index } = useParams<{ index: string }>();
  const promptIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  const fakeTopic = FAKE_TOPICS[(promptIndex - 1) % FAKE_TOPICS.length]!;
  const initialReal =
    phase === 'cold'
      ? (peekToday()?.prompts.find((p) => p.order_index === promptIndex - 1)
          ?.cold_prompt_text ?? null)
      : (peekFinals()?.prompts.find((p) => p.order_index === promptIndex - 1)
          ?.final_prompt_text ?? null);
  const [realText, setRealText] = useState<string | null>(initialReal);
  const promptText =
    realText ?? (phase === 'cold' ? fakeTopic.coldPrompt : fakeTopic.finalPrompt);
  const headerLabel =
    phase === 'cold'
      ? `Prompt ${promptIndex} / ${promptCount} · Recording`
      : `Final · ${promptIndex} of ${promptCount} · Recording`;

  const [status, setStatus] = useState<Status>('preparing');
  const [secondsElapsed, setSecondsElapsed] = useState(0);
  const [holding, setHolding] = useState(false);

  // Refresh the prompt text from the API cache if it wasn't warm at mount.
  useEffect(() => {
    if (realText != null) return;
    let cancelled = false;
    const fetcher = phase === 'cold' ? getToday() : getFinals();
    fetcher
      .then((r) => {
        if (cancelled) return;
        const p = r.prompts.find((pp) => pp.order_index === promptIndex - 1);
        if (p) {
          setRealText(
            'cold_prompt_text' in p ? p.cold_prompt_text : p.final_prompt_text,
          );
        }
      })
      .catch(() => {
        // Silent fallback to fixture text.
      });
    return () => {
      cancelled = true;
    };
  }, [phase, promptIndex, realText]);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const spikeRefs = useRef<(SVGLineElement | null)[]>([]);
  const rafRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);
  const holdTimerRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const stoppedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function startCapture() {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        if (!cancelled) {
          console.warn('Mic permission denied or unavailable:', err);
          setStatus('denied');
        }
        return;
      }

      if (cancelled) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      streamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        console.log(
          `[uu] ${phase} recording ${promptIndex} stopped — ${blob.size}B, ${recorder.mimeType}`,
        );

        // Prompt UUIDs are shared between cold and final — same Prompt row
        // carries both texts. Look up from whichever cache matches the phase.
        const cached =
          phase === 'cold' ? peekToday() : peekFinals();
        const promptForUpload = cached?.prompts.find(
          (p) => p.order_index === promptIndex - 1,
        );
        if (!promptForUpload) {
          console.warn(
            `[uu] no ${phase} prompt id for promptIndex=${promptIndex}; skipping upload`,
          );
          return;
        }

        // Fire-and-forget. The user has already navigated away by now; the
        // promise survives unmount and any failure logs but doesn't bubble.
        uploadRecording(promptForUpload.id, phase, blob)
          .then((res) => {
            console.log(
              `[uu] ${phase} upload registered as ${res.recording_id} (${res.transcription_status})`,
            );
          })
          .catch((err: Error) => {
            console.error(`[uu] ${phase} upload failed:`, err.message);
          });
      };
      recorderRef.current = recorder;
      recorder.start();

      const audioCtx = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 32;
      analyser.smoothingTimeConstant = 0.7;
      source.connect(analyser);

      audioCtxRef.current = audioCtx;
      analyserRef.current = analyser;
      dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);

      startedAtRef.current = Date.now();
      setStatus('recording');

      const tick = () => {
        if (stoppedRef.current) return;

        const a = analyserRef.current;
        const data = dataArrayRef.current;
        if (a && data) {
          a.getByteFrequencyData(data);
          for (let i = 0; i < SPIKE_COUNT; i++) {
            const v = (data[i + 1] ?? 0) / 255;
            const len = MIN_SPIKE_LEN + v * (MAX_SPIKE_LEN - MIN_SPIKE_LEN);
            const line = spikeRefs.current[i];
            if (line) {
              line.setAttribute('y2', String(-70 + len));
              line.setAttribute('opacity', String(0.4 + v * 0.6));
            }
          }
        }

        const elapsed = Date.now() - startedAtRef.current;
        setSecondsElapsed(Math.floor(elapsed / 1000));

        if (elapsed >= MAX_RECORDING_MS) {
          stopAndExit();
          return;
        }

        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    }

    startCapture();

    return () => {
      cancelled = true;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function cleanup() {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      try {
        recorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {});
    }
    if (holdTimerRef.current !== null) {
      window.clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
  }

  function computeNextRoute(): string {
    if (phase === 'cold') {
      return promptIndex < promptCount
        ? `/cold/interstitial/${promptIndex + 1}`
        : '/briefings/preparing';
    }
    return promptIndex < promptCount
      ? `/final/prep/${promptIndex + 1}`
      : '/scores/preparing';
  }

  function stopAndExit() {
    if (stoppedRef.current) return;
    stoppedRef.current = true;
    setStatus('stopping');
    cleanup();
    const nextRoute = computeNextRoute();
    window.setTimeout(() => {
      navigate(nextRoute, {
        replace: true,
        state: { promptCount, includeRepeat },
      });
    }, 300);
  }

  function onHoldStart() {
    if (status !== 'recording') return;
    setHolding(true);
    holdTimerRef.current = window.setTimeout(stopAndExit, HOLD_TO_END_MS);
  }

  function onHoldCancel() {
    if (holdTimerRef.current !== null) {
      window.clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHolding(false);
  }

  if (status === 'denied') {
    return (
      <div className="min-h-screen w-full bg-ink text-paper flex items-center justify-center px-6">
        <div className="max-w-[280px] text-center">
          <div className="tiny-label">Microphone required</div>
          <p className="mt-4 text-[14px] leading-[1.45] opacity-70">
            Unknown Unknowns needs microphone access to record your answer. Allow it in your
            browser, then come back and start over.
          </p>
          <button
            onClick={() => navigate('/', { replace: true })}
            className="mt-7 text-[11px] tracking-[0.14em] uppercase opacity-70 underline underline-offset-4"
          >
            Back home
          </button>
        </div>
      </div>
    );
  }

  if (status === 'preparing') {
    return (
      <div className="min-h-screen w-full bg-ink text-paper flex items-center justify-center">
        <div className="tiny-label opacity-50">Preparing microphone…</div>
      </div>
    );
  }

  const mm = String(Math.floor(secondsElapsed / 60)).padStart(2, '0');
  const ss = String(secondsElapsed % 60).padStart(2, '0');

  return (
    <div className="min-h-screen w-full bg-ink text-paper flex flex-col">
      <div className="mx-auto w-full max-w-[420px] px-6 pt-10 pb-8 flex flex-col flex-1">
        <header className="text-center">
          <div className="tiny-label opacity-50">{headerLabel}</div>
          <div className="mt-2 text-[13px] font-semibold opacity-70">{promptText}</div>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center">
          <div className="relative w-[200px] h-[200px] flex items-center justify-center">
            <div className="absolute inset-0 m-auto w-[184px] h-[184px] rounded-full border border-paper opacity-35" />
            <div className="absolute inset-0 m-auto w-[164px] h-[164px] rounded-full border border-paper opacity-55" />
            <div className="absolute inset-0 m-auto w-[144px] h-[144px] rounded-full border border-paper opacity-80" />

            <svg
              viewBox="-80 -80 160 160"
              width="200"
              height="200"
              className="absolute pointer-events-none"
              aria-hidden
            >
              <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                {Array.from({ length: SPIKE_COUNT }).map((_, i) => (
                  <line
                    key={i}
                    ref={(el) => {
                      spikeRefs.current[i] = el;
                    }}
                    x1="0"
                    y1="-70"
                    x2="0"
                    y2={-70 + MIN_SPIKE_LEN}
                    opacity="0.4"
                    transform={`rotate(${i * (360 / SPIKE_COUNT)})`}
                  />
                ))}
              </g>
            </svg>

            <div className="absolute inset-0 m-auto w-[120px] h-[120px] rounded-full bg-paper flex items-center justify-center animate-record-pulse">
              <div className="w-[14px] h-[14px] rounded-full bg-ink" />
            </div>
          </div>

          <div className="mt-9 text-[32px] font-semibold tabular-nums tracking-[-0.04em]">
            {mm}:{ss}
          </div>
          <div className="mt-1 tiny-label opacity-50">target 60–90s</div>
        </main>

        <footer className="flex justify-center pb-2">
          <button
            onPointerDown={onHoldStart}
            onPointerUp={onHoldCancel}
            onPointerLeave={onHoldCancel}
            onPointerCancel={onHoldCancel}
            className={[
              'text-[11px] tracking-[0.14em] uppercase border-t border-paper pt-2 px-3 transition-opacity duration-150 select-none touch-none',
              holding ? 'opacity-100' : 'opacity-50',
            ].join(' ')}
            aria-label="Hold to end recording"
          >
            hold to end
          </button>
        </footer>
      </div>
    </div>
  );
}
