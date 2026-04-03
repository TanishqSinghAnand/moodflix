/**
 * Typed API client — auto-attaches Firebase token to every request.
 * Works identically from Next.js and React Native (swap getToken import only).
 */

import { auth } from "./firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────────

export type MoodTag =
  | "uplifting" | "relaxing"  | "thrilling"   | "nostalgic"
  | "dark"      | "romantic"  | "adventurous" | "funny"
  | "emotional" | "mind_bending";

/** Per-mood intensity: each selected mood can have its own slider value */
export interface MoodIntensity {
  mood:      MoodTag;
  intensity: number;  // 1–10
}

export interface MoodSession {
  session_id:    string;
  moods:         MoodTag[];
  intensities:   Record<string, number>;
  genre_weights: Record<string, number>;
}

export interface RecommendedTitle {
  id:           string;
  title:        string;
  media_type:   "movie" | "series" | "anime";
  genres:       string[];
  mood_tags:    MoodTag[];
  poster_url:   string | null;
  backdrop_url: string | null;
  overview:     string | null;
  release_year: number | null;
  rating:       number | null;
  mood_score:   number;
  cf_score:     number;
  final_score:  number;
  reason:       string;
}

export interface RecommendationResponse {
  session_id:       string;
  moods:            MoodTag[];
  results:          RecommendedTitle[];
  serendipity_pick: RecommendedTitle | null;
}

export interface ImportResult {
  platform:     string;
  parsed_count: number;
  new_titles:   number;
  skipped:      number;
  errors:       string[];
}

export interface OnboardingGenreChoice {
  genre:    string;
  strength: 1 | 2 | 3;
}

export interface OnboardingSubmit {
  genres:           OnboardingGenreChoice[];
  favorite_titles:  string[];
  media_preference: "movies" | "series" | "both" | "anime";
}

export interface OnboardingStatus {
  onboarding_complete: boolean;
  media_preference:    string;
  favorite_genres:     string[];
}

// ── Core fetch ─────────────────────────────────────────────────────────────────

async function getToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  };
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Auth ───────────────────────────────────────────────────────────────────────
export const apiVerifyToken = () =>
  apiFetch<{ uid: string }>("/api/v1/auth/me");

// ── Mood ───────────────────────────────────────────────────────────────────────

/**
 * Create a mood session with per-mood intensity values.
 * Each mood in the array has its own intensity slider (1–10).
 */
export const apiCreateMoodSession = (moods: MoodIntensity[]) =>
  apiFetch<MoodSession>("/api/v1/mood/session", {
    method: "POST",
    body: JSON.stringify({ moods }),
  });

export const apiGetMoodHistory = () =>
  apiFetch<MoodSession[]>("/api/v1/mood/history");

// ── Recommendations ────────────────────────────────────────────────────────────
export const apiGetRecommendations = (
  mood_session_id: string,
  limit = 12,
  exclude_watched = true
) =>
  apiFetch<RecommendationResponse>("/api/v1/recommendations/", {
    method: "POST",
    body: JSON.stringify({ mood_session_id, limit, exclude_watched }),
  });

export const apiSubmitFeedback = (payload: {
  title_id:     string;
  session_id:   string;
  relevant:     boolean;
  mood_matched?: boolean;
  rating?:      number;
}) =>
  apiFetch<{ status: string }>("/api/v1/recommendations/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// ── Import ─────────────────────────────────────────────────────────────────────
async function importFile(path: string, file: File, extra?: Record<string, string>) {
  const form = new FormData();
  form.append("file", file);
  const url = extra ? `${path}?${new URLSearchParams(extra)}` : path;
  return apiFetch<ImportResult>(url, { method: "POST", body: form });
}

export const apiImportNetflix  = (file: File) => importFile("/api/v1/import/netflix", file);
export const apiImportPrime    = (file: File) => importFile("/api/v1/import/prime", file);
export const apiImportHotstar  = (file: File) => importFile("/api/v1/import/prime", file, { platform: "hotstar" });
export const apiImportMAL      = (file: File) => importFile("/api/v1/import/mal", file);
export const apiGetImportStatus = () =>
  apiFetch<{ totals: Record<string, number>; grand_total: number }>("/api/v1/import/status");

// ── Onboarding ─────────────────────────────────────────────────────────────────
export const apiGetOnboardingStatus = () =>
  apiFetch<OnboardingStatus>("/api/v1/onboarding/status");

export const apiCompleteOnboarding = (payload: OnboardingSubmit) =>
  apiFetch<{ success: boolean; message: string }>("/api/v1/onboarding/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// ── Users ──────────────────────────────────────────────────────────────────────
export const apiGetProfile = () =>
  apiFetch<{ uid: string; display_name: string | null; onboarding_complete: boolean }>(
    "/api/v1/users/profile"
  );
