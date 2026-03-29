/**
 * Global auth state via Zustand.
 * Keeps Firebase user in sync and exposes sign-in/out helpers.
 */

import { create } from "zustand";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  User,
} from "firebase/auth";
import { auth, googleProvider } from "@/lib/firebase";

interface AuthState {
  user:        User | null;
  loading:     boolean;
  signInGoogle: () => Promise<void>;
  signOut:     () => Promise<void>;
  init:        () => () => void; // returns unsubscribe
}

export const useAuthStore = create<AuthState>((set) => ({
  user:    null,
  loading: true,

  /** Subscribe to Firebase auth state changes (call once in root layout). */
  init: () => {
    const unsub = onAuthStateChanged(auth, (user) => {
      set({ user, loading: false });
    });
    return unsub;
  },

  signInGoogle: async () => {
    await signInWithPopup(auth, googleProvider);
  },

  signOut: async () => {
    await firebaseSignOut(auth);
    set({ user: null });
  },
}));
