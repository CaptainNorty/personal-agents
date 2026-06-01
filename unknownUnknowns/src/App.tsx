import { Routes, Route, useParams } from 'react-router-dom';
import { useAuth } from './lib/auth';
import Home from './screens/Home';
import Countdown from './screens/Countdown';
import PrepScreen from './screens/PrepScreen';
import RecordScreen from './screens/RecordScreen';
import ColdInterstitial from './screens/ColdInterstitial';
import Briefing from './screens/Briefing';
import PreparingBriefings from './screens/PreparingBriefings';
import PreparingScores from './screens/PreparingScores';
import Score from './screens/Score';
import Done from './screens/Done';
import SignIn from './screens/SignIn';

/* Force a fresh mount of Briefing/Score when the URL index changes, so
 * internal state (cached topic, animation counters) resets correctly per
 * topic. Without the key, React Router reuses the same component instance
 * across /briefing/1 → /briefing/2 and stale state leaks across. */
function BriefingByIndex() {
  const { index } = useParams<{ index: string }>();
  return <Briefing key={index ?? '0'} />;
}

function ScoreByIndex() {
  const { index } = useParams<{ index: string }>();
  return <Score key={index ?? '0'} />;
}

export default function App() {
  const { user, loading } = useAuth();

  // Initial Firebase load is ~50-200ms (reads IndexedDB). Hold the splash
  // briefly to avoid flashing the sign-in screen for already-signed-in users.
  if (loading) {
    return (
      <div className="min-h-screen w-full bg-paper text-ink flex items-center justify-center">
        <div className="tiny-label opacity-50">Loading…</div>
      </div>
    );
  }

  if (!user) return <SignIn />;

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/countdown" element={<Countdown />} />
      <Route path="/cold/prep/:index" element={<PrepScreen phase="cold" />} />
      <Route path="/cold/record/:index" element={<RecordScreen phase="cold" />} />
      <Route path="/cold/interstitial/:index" element={<ColdInterstitial />} />
      <Route path="/briefings/preparing" element={<PreparingBriefings />} />
      <Route path="/briefing/:index" element={<BriefingByIndex />} />
      <Route path="/final/prep/:index" element={<PrepScreen phase="final" />} />
      <Route path="/final/record/:index" element={<RecordScreen phase="final" />} />
      <Route path="/scores/preparing" element={<PreparingScores />} />
      <Route path="/scores/:index" element={<ScoreByIndex />} />
      <Route path="/done" element={<Done />} />
    </Routes>
  );
}
