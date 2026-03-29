/**
 * Client-side mood definitions — emoji, label, color, description.
 * Synced with backend MoodTag enum.
 */

import type { MoodTag } from "@/lib/api";

export interface MoodConfig {
  tag:         MoodTag;
  emoji:       string;
  label:       string;
  description: string;
  color:       string;  // Tailwind bg class
  textColor:   string;  // Tailwind text class
  hex:         string;  // Raw hex for inline styles
}

export const MOODS: MoodConfig[] = [
  {
    tag:         "uplifting",
    emoji:       "☀️",
    label:       "Feel-Good",
    description: "Warm, happy, wholesome vibes",
    color:       "bg-yellow-300/15",
    textColor:   "text-yellow-300",
    hex:         "#FCD34D",
  },
  {
    tag:         "funny",
    emoji:       "😂",
    label:       "Comedy",
    description: "Make me laugh, please",
    color:       "bg-amber-300/15",
    textColor:   "text-amber-300",
    hex:         "#FDE68A",
  },
  {
    tag:         "thrilling",
    emoji:       "⚡",
    label:       "Thrilling",
    description: "Edge-of-seat suspense",
    color:       "bg-red-400/15",
    textColor:   "text-red-400",
    hex:         "#F87171",
  },
  {
    tag:         "adventurous",
    emoji:       "🌍",
    label:       "Adventure",
    description: "Action, journeys & epic worlds",
    color:       "bg-orange-400/15",
    textColor:   "text-orange-400",
    hex:         "#FB923C",
  },
  {
    tag:         "relaxing",
    emoji:       "🌿",
    label:       "Chill",
    description: "Low-stakes, easy watching",
    color:       "bg-emerald-400/15",
    textColor:   "text-emerald-400",
    hex:         "#6EE7B7",
  },
  {
    tag:         "nostalgic",
    emoji:       "🌅",
    label:       "Nostalgic",
    description: "Throwback & coming-of-age feels",
    color:       "bg-blue-300/15",
    textColor:   "text-blue-300",
    hex:         "#93C5FD",
  },
  {
    tag:         "romantic",
    emoji:       "💗",
    label:       "Romance",
    description: "Love, longing, butterflies",
    color:       "bg-pink-400/15",
    textColor:   "text-pink-400",
    hex:         "#F9A8D4",
  },
  {
    tag:         "emotional",
    emoji:       "🥺",
    label:       "Emotional",
    description: "Complex feelings, deep stories",
    color:       "bg-purple-400/15",
    textColor:   "text-purple-400",
    hex:         "#A78BFA",
  },
  {
    tag:         "dark",
    emoji:       "🌑",
    label:       "Dark",
    description: "Gritty, intense, unsettling",
    color:       "bg-indigo-400/15",
    textColor:   "text-indigo-400",
    hex:         "#818CF8",
  },
  {
    tag:         "mind_bending",
    emoji:       "🌀",
    label:       "Mind-Bending",
    description: "Sci-fi, twists, reality breaks",
    color:       "bg-cyan-400/15",
    textColor:   "text-cyan-400",
    hex:         "#67E8F9",
  },
];

export const getMoodConfig = (tag: MoodTag): MoodConfig =>
  MOODS.find((m) => m.tag === tag) ?? MOODS[0];
