/**
 * Firebase client-side SDK initialization.
 * Uses environment variables prefixed with NEXT_PUBLIC_ (safe to expose).
 * The same firebase project is used by both web and the future React Native app.
 */

import { initializeApp, getApps, FirebaseApp } from "firebase/app";
import { getAuth, Auth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore, Firestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey:            process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain:        process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId:         process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  storageBucket:     process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET!,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
  appId:             process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
};

// Singleton pattern — safe with Next.js hot reload
let app: FirebaseApp;
let auth: Auth;
let db: Firestore;

if (!getApps().length) {
  app  = initializeApp(firebaseConfig);
} else {
  app  = getApps()[0];
}

auth = getAuth(app);
db   = getFirestore(app);

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: "select_account" });

export { app, auth, db, googleProvider };