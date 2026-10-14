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

export async function getFirebaseIdToken(): Promise<string> {
  if (!firebaseAuth?.currentUser) {
    throw new Error('Debes iniciar sesión para usar la generación de IA.');
  }

  const token = await firebaseAuth.currentUser.getIdToken();
  if (!token) {
    throw new Error('No se pudo obtener el token de Firebase.');
  }

  return token;
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
