import { useState } from 'react';
import { useAuth } from '../lib/auth';

export default function SignIn() {
  const { signInWithGoogle } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await signInWithGoogle();
      // Successful sign-in triggers onAuthStateChanged, which re-renders
      // the app router and replaces this screen. No navigate() needed.
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Sign-in failed.';
      setError(message);
      setPending(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-paper text-ink flex flex-col">
      <div className="mx-auto w-full max-w-[420px] px-6 pt-14 pb-10 flex flex-col flex-1">
        <header className="flex flex-col items-center">
          <div
            className="text-[34px] font-extrabold leading-none tracking-[-0.04em] select-none"
            aria-label="Unknown Unknowns"
          >
            UU
          </div>
          <div className="mt-1.5 tiny-label">Unknown Unknowns</div>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center gap-6">
          <div className="text-[22px] font-semibold tracking-[-0.02em] leading-[1.1] text-center max-w-[260px]">
            Sign in to begin today's session.
          </div>
          <button
            onClick={handleClick}
            disabled={pending}
            className="w-full max-w-[260px] py-3 bg-ink text-paper rounded-full font-medium text-[14px] tracking-tight transition-opacity active:opacity-80 disabled:opacity-60"
          >
            {pending ? 'Signing in…' : 'Continue with Google'}
          </button>
          {error && (
            <div className="text-[11px] opacity-70 max-w-[260px] text-center">
              {error}
            </div>
          )}
        </main>

        <footer className="tiny-label opacity-50 text-center">
          A daily learning game
        </footer>
      </div>
    </div>
  );
}
