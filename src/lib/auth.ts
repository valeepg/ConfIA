import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type User,
} from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';

import { firebaseAuth, firebaseDb } from './firebase';

export type AppRole = 'admin' | 'sales' | 'medical' | 'support';

const googleProvider = new GoogleAuthProvider();

export function subscribeToAuth(callback: (user: User | null) => void) {
  if (!firebaseAuth) {
    callback(null);
    return () => undefined;
  }

  return onAuthStateChanged(firebaseAuth, callback);
}

export async function signInWithGoogle() {
  if (!firebaseAuth) {
    throw new Error('Firebase Authentication no está habilitado.');
  }

  return signInWithPopup(firebaseAuth, googleProvider);
}

export async function signOutUser() {
  if (!firebaseAuth) {
    return;
  }

  await signOut(firebaseAuth);
}

/**
 * Devuelve el token de Firebase si hay sesión; si no, null.
 * Por ahora la IA funciona sin login (demo). El backend decide si exige el token.
 */
export async function getFirebaseIdToken(): Promise<string | null> {
  if (!firebaseAuth?.currentUser) {
    return null;
  }

  return firebaseAuth.currentUser.getIdToken();
}

export async function getUserRole(uid: string): Promise<AppRole | null> {
  if (!firebaseDb) {
    return null;
  }

  const snapshot = await getDoc(doc(firebaseDb, 'users', uid));
  const role = snapshot.data()?.role;

  return role === 'admin' || role === 'sales' || role === 'medical' || role === 'support'
    ? role
    : null;
}
