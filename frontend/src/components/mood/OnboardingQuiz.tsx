"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { apiCompleteOnboarding } from "@/lib/api";
import type { OnboardingGenreChoice } from "@/lib/api";
import { Check, ArrowRight, Film, Tv, Sparkles } from "lucide-react";
import toast from "react-hot-toast";

/* ── Genre data ──────────────────────────────────────────────────────────────── */

const GENRE_GROUPS = [
  {
    label: "Action & Thrills",
    genres: ["Action", "Thriller", "Crime", "Mystery", "Horror"],
  },
  {
    label: "Feel Good",
    genres: ["Comedy", "Romance", "Family", "Music", "Animation"],
  },
  {
    label: "Deep & Immersive",
    genres: ["Drama", "Science Fiction", "Fantasy", "Adventure", "History"],
  },
  {
    label: "Real World",
    genres: ["Documentary", "War", "Western"],
  },
];

// Color per genre group
const GROUP_COLORS = [
  { bg: "bg-red-500/10",    text: "text-red-400",    border: "border-red-500/20"    },
  { bg: "bg-yellow-500/10", text: "text-yellow-400", border: "border-yellow-500/20" },
  { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  { bg: "bg-blue-500/10",   text: "text-blue-400",   border: "border-blue-500/20"   },
];

const STRENGTH_LABELS: Record<number, string> = {
  1: "It's okay",
  2: "I like it",
  3: "I love it ❤️",
};

const MEDIA_OPTIONS = [
  { value: "both",    label: "Everything",  emoji: "🎬", desc: "Movies + Series" },
  { value: "movies",  label: "Movies",      emoji: "🎥", desc: "Feature films"   },
  { value: "series",  label: "Series",      emoji: "📺", desc: "TV & web shows"  },
  { value: "anime",   label: "Anime",       emoji: "🌸", desc: "Japanese animation" },
] as const;

/* ── Step 1: Genre picker ─────────────────────────────────────────────────────── */

function GenrePicker({
  selected,
  onChange,
}: {
  selected: Map<string, number>;
  onChange: (genre: string, strength: number) => void;
}) {
  const cycleStrength = (genre: string) => {
    const current = selected.get(genre) ?? 0;
    if (current === 0)      onChange(genre, 1); // unselected → mild
    else if (current === 1) onChange(genre, 2); // mild → like
    else if (current === 2) onChange(genre, 3); // like → love
    else                    onChange(genre, 0); // love → unselect
  };

  return (
    <div className="space-y-6">
      {GENRE_GROUPS.map((group, gi) => {
        const color = GROUP_COLORS[gi];
        return (
          <div key={group.label}>
            <p className={`text-xs font-medium uppercase tracking-wider mb-3 ${color.text}`}>
              {group.label}
            </p>
            <div className="flex flex-wrap gap-2">
              {group.genres.map((genre) => {
                const strength = selected.get(genre) ?? 0;
                const isSelected = strength > 0;

                return (
                  <motion.button
                    key={genre}
                    onClick={() => cycleStrength(genre)}
                    whileTap={{ scale: 0.95 }}
                    className={`
                      px-4 py-2 rounded-full text-sm font-medium border transition-all duration-200
                      ${isSelected
                        ? `${color.bg} ${color.text} ${color.border}`
                        : "glass border-transparent text-ink-secondary hover:border-white/10"
                      }
                    `}
                  >
                    {isSelected && (
                      <span className="mr-1.5">
                        {strength === 1 ? "👍" : strength === 2 ? "✨" : "❤️"}
                      </span>
                    )}
                    {genre}
                  </motion.button>
                );
              })}
            </div>
          </div>
        );
      })}

      <p className="text-ink-muted text-xs">
        Tap once = okay · twice = like · three times = love · four times = remove
      </p>
    </div>
  );
}

/* ── Step 2: Media preference ─────────────────────────────────────────────────── */

function MediaPreferencePicker({
  value,
  onChange,
}: {
  value:    string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {MEDIA_OPTIONS.map((opt) => (
        <motion.button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          whileTap={{ scale: 0.97 }}
          className={`
            flex flex-col items-center gap-2 p-5 rounded-2xl border transition-all duration-200
            ${value === opt.value
              ? "bg-accent/15 border-accent/40 text-accent"
              : "glass border-transparent text-ink-secondary hover:border-white/10"
            }
          `}
        >
          <span className="text-3xl">{opt.emoji}</span>
          <span className="font-display font-semibold text-sm">{opt.label}</span>
          <span className="text-xs opacity-70">{opt.desc}</span>
          {value === opt.value && (
            <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center">
              <Check size={11} className="text-accent" strokeWidth={3} />
            </div>
          )}
        </motion.button>
      ))}
    </div>
  );
}

/* ── Main OnboardingQuiz ──────────────────────────────────────────────────────── */

export default function OnboardingQuiz({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<1 | 2>(1);
  const [genreMap, setGenreMap] = useState<Map<string, number>>(new Map());
  const [mediaPreference, setMediaPreference] = useState("both");
  const [loading, setLoading] = useState(false);

  const selectedCount = [...genreMap.values()].filter(v => v > 0).length;

  const handleGenreChange = (genre: string, strength: number) => {
    setGenreMap((prev) => {
      const next = new Map(prev);
      if (strength === 0) next.delete(genre);
      else next.set(genre, strength);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (selectedCount < 3) {
      toast.error("Pick at least 3 genres so we can personalize your recs!");
      return;
    }

    setLoading(true);
    try {
      const genres: OnboardingGenreChoice[] = [...genreMap.entries()]
        .filter(([, s]) => s > 0)
        .map(([genre, strength]) => ({ genre, strength: strength as 1 | 2 | 3 }));

      await apiCompleteOnboarding({
        genres,
        favorite_titles: [],
        media_preference: mediaPreference as any,
      });

      toast.success("All set! Your personalized picks are ready 🎬");
      onComplete();
    } catch (e: any) {
      toast.error(e.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Sparkles size={18} className="text-accent" />
          <span className="text-accent text-sm font-medium">Quick Setup</span>
        </div>
        <h2 className="font-display font-bold text-2xl text-ink-primary mb-1">
          {step === 1 ? "What do you love watching?" : "What type of content?"}
        </h2>
        <p className="text-ink-secondary text-sm">
          {step === 1
            ? `Select genres you enjoy — ${selectedCount < 3 ? `${3 - selectedCount} more needed` : "great! keep going"}`
            : "We'll mix your results to match your preference."
          }
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2">
        {[1, 2].map((s) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              s <= step ? "bg-accent" : "bg-bg-elevated"
            }`}
          />
        ))}
      </div>

      {/* Step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: step === 1 ? -20 : 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: step === 1 ? 20 : -20 }}
          transition={{ duration: 0.25 }}
        >
          {step === 1 ? (
            <GenrePicker selected={genreMap} onChange={handleGenreChange} />
          ) : (
            <MediaPreferencePicker value={mediaPreference} onChange={setMediaPreference} />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex gap-3">
        {step === 2 && (
          <button
            onClick={() => setStep(1)}
            className="px-6 py-3 glass rounded-2xl text-ink-secondary font-medium hover:text-ink-primary transition-colors"
          >
            Back
          </button>
        )}

        {step === 1 ? (
          <button
            onClick={() => {
              if (selectedCount < 3) {
                toast.error("Pick at least 3 genres first!");
                return;
              }
              setStep(2);
            }}
            className="btn-glow flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl font-display font-bold text-white"
          >
            Next <ArrowRight size={16} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="btn-glow flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl font-display font-bold text-white disabled:opacity-60"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Setting up…
              </>
            ) : (
              <>
                Let's Go! <Sparkles size={16} />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
