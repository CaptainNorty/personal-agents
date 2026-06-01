/**
 * Firebase initialization for Unknown Unknowns.
 *
 * The config below is public — it identifies the Firebase project, not a
 * secret. Security is enforced server-side (the FastAPI auth dependency
 * verifies ID tokens with the Firebase Admin SDK against this project).
 *
 * Analytics is intentionally omitted — we don't want the extra bundle weight
 * for the v1 app, and product analytics can be layered in later.
 */
import { initializeApp } from 'firebase/app';
import {
  GoogleAuthProvider,
  browserLocalPersistence,
  getAuth,
  setPersistence,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: 'AIzaSyA8Wu41eiJFvWE2D_6fmEKP3Ih37VA8NmA',
  authDomain: 'unknownunknowns-38737.firebaseapp.com',
  projectId: 'unknownunknowns-38737',
  storageBucket: 'unknownunknowns-38737.firebasestorage.app',
  messagingSenderId: '334219812894',
  appId: '1:334219812894:web:5a57b585197a6a694ece0f',
  measurementId: 'G-B0T3SC682B',
};

export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const googleProvider = new GoogleAuthProvider();

// Persist auth across reloads + browser restarts. The refresh token is held
// in IndexedDB; the user stays signed in until they explicitly sign out.
// Fire-and-forget — if it fails we fall back to in-memory (still works for
// the current tab session).
void setPersistence(auth, browserLocalPersistence).catch((err) => {
  console.warn('[uu] auth persistence setup failed:', err);
});
