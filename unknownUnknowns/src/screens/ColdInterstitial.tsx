import { useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

const DURATION_MS = 1200;

type LocationState = {
  promptCount?: 1 | 2 | 3;
  includeRepeat?: boolean;
};

export default function ColdInterstitial() {
  const { index } = useParams<{ index: string }>();
  const promptIndex = Math.max(1, parseInt(index ?? '1', 10));

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const promptCount = state.promptCount ?? 3;
  const includeRepeat = state.includeRepeat ?? false;

  useEffect(() => {
    const t = window.setTimeout(() => {
      navigate(`/cold/prep/${promptIndex}`, {
        replace: true,
        state: { promptCount, includeRepeat },
      });
    }, DURATION_MS);
    return () => window.clearTimeout(t);
  }, [navigate, promptIndex, promptCount, includeRepeat]);

  return (
    <div
      className="min-h-screen w-full flex flex-col text-ink"
      style={{ backgroundColor: '#fafafa' }}
    >
      <div className="mx-auto w-full max-w-[420px] px-6 flex flex-col flex-1 items-center justify-center">
        <div className="tiny-label mb-5">Transitioning</div>
        <div className="text-[22px] font-semibold tracking-[-0.02em] leading-[1.1] text-center">
          {promptIndex} of {promptCount}
        </div>
        <div className="mt-2.5 text-[13px] opacity-60">Next prompt incoming</div>
        <div className="mt-9 w-[140px] h-[2px] bg-ink/30 relative overflow-hidden">
          <div className="absolute inset-0 bg-ink animate-interstitial-fill" />
        </div>
      </div>
    </div>
  );
}
