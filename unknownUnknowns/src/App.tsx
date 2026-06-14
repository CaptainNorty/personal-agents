import { Routes, Route } from 'react-router-dom';
import { useAuth } from './lib/auth';
import Home from './screens/Home';
import Countdown from './screens/Countdown';
import PrepScreen from './screens/PrepScreen';
import RecordScreen from './screens/RecordScreen';
import ColdInterstitial from './screens/ColdInterstitial';
import BriefingFlow from './screens/BriefingFlow';
import PreparingBriefings from './screens/PreparingBriefings';
import PreparingScores from './screens/PreparingScores';
import ScoreFlow from './screens/ScoreFlow';
import Done from './screens/Done';
import SignIn from './screens/SignIn';

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
      <Route path="/briefing/:index" element={<BriefingFlow />} />
      <Route path="/final/prep/:index" element={<PrepScreen phase="final" />} />
      <Route path="/final/record/:index" element={<RecordScreen phase="final" />} />
      <Route path="/scores/preparing" element={<PreparingScores />} />
      <Route path="/scores/:index" element={<ScoreFlow />} />
      <Route path="/done" element={<Done />} />
    </Routes>
  );
}
