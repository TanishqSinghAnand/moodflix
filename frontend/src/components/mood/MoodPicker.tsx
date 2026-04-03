"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { MOODS, type MoodConfig } from "@/lib/moods";
import { apiCreateMoodSession, type MoodIntensity } from "@/lib/api";
import type { MoodTag } from "@/lib/api";
import { ArrowRight, Check, X } from "lucide-react";
import toast from "react-hot-toast";

const MAX_MOODS = 3;

/* ── Per-mood intensity slider ───────────────────────────────────────────────── */

function MoodIntensitySlider({
  mood,
  value,
  onChange,
  onRemove,
}: {
  mood:     MoodConfig;
  value:    number;
  onChange: (v: number) => void;
  onRemove: () => void;
}) {
  const label = value <= 3 ? "Low" : value <= 6 ? "Medium" : value <= 8 ? "High" : "Intense";

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className={`rounded-2xl p-4 ${mood.color} border border-current/20`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{mood.emoji}</span>
          <span className={`font-display font-semibold text-sm ${mood.textColor}`}>
            {mood.label}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-medium ${mood.textColor} opacity-80`}>
            {label}
          </span>
          <button
            onClick={onRemove}
            className="w-5 h-5 rounded-full bg-black/20 flex items-center justify-center hover:bg-black/40 transition-colors"
          >
            <X size={10} className={mood.textColor} />
          </button>
        </div>
      </div>

      {/* Intensity slider styled to match mood color */}
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 appearance-none rounded-full cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-4
          [&::-webkit-slider-thumb]:h-4
          [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:shadow-md"
        style={{
          background: `linear-gradient(to right, ${mood.hex} ${(value - 1) * 11.1}%, rgba(0,0,0,0.2) ${(value - 1) * 11.1}%)`,
        }}
      />

      <div className="flex justify-between text-xs mt-1 opacity-50">
        <span className={mood.textColor}>Mild</span>
        <span className={mood.textColor}>Intense</span>
      </div>
    </motion.div>
  );
}

/* ── Single mood pill ─────────────────────────────────────────────────────────── */

function MoodPill({
  mood,
  selected,
  disabled,
  onClick,
}: {
  mood:     MoodConfig;
  selected: boolean;
  disabled: boolean;
  onClick:  () => void;
}) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled && !selected}
      whileHover={!disabled || selected ? { scale: 1.04 } : {}}
      whileTap={!disabled || selected ? { scale: 0.97 } : {}}
      className={`
        relative flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-200
        ${selected
          ? `${mood.color} border-current/30 ${mood.textColor}`
          : disabled
            ? "glass border-transparent text-ink-muted opacity-40 cursor-not-allowed"
            : "glass border-transparent hover:border-white/10 text-ink-secondary hover:text-ink-primary"
        }
      `}
    >
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className={`absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center ${mood.color} ${mood.textColor}`}
          >
            <Check size={11} strokeWidth={3} />
          </motion.div>
        )}
      </AnimatePresence>
      <span className="text-3xl">{mood.emoji}</span>
      <span className="font-display font-semibold text-sm">{mood.label}</span>
      <span className="text-xs text-center leading-tight opacity-70">{mood.description}</span>
    </motion.button>
  );
}

/* ── Main MoodPicker ──────────────────────────────────────────────────────────── */

export default function MoodPicker() {
  const router = useRouter();

  // Each selected mood has its own intensity value
  const [selectedMoods, setSelectedMoods] = useState<MoodIntensity[]>([]);
  const [loading, setLoading] = useState(false);

  const selectedTags = selectedMoods.map((m) => m.mood);

  const toggleMood = (tag: MoodTag) => {
    setSelectedMoods((prev) => {
      const exists = prev.find((m) => m.mood === tag);
      if (exists) {
        // Deselect
        return prev.filter((m) => m.mood !== tag);
      }
      if (prev.length >= MAX_MOODS) {
        toast(`Pick up to ${MAX_MOODS} moods`, { icon: "💡" });
        return prev;
      }
      // Select with default intensity 5
      return [...prev, { mood: tag, intensity: 5 }];
    });
  };

  const updateIntensity = (tag: MoodTag, intensity: number) => {
    setSelectedMoods((prev) =>
      prev.map((m) => (m.mood === tag ? { ...m, intensity } : m))
    );
  };

  const removeMood = (tag: MoodTag) => {
    setSelectedMoods((prev) => prev.filter((m) => m.mood !== tag));
  };

  const handleSubmit = async () => {
    if (selectedMoods.length === 0) {
      toast.error("Pick at least one mood first!");
      return;
    }
    setLoading(true);
    try {
      const session = await apiCreateMoodSession(selectedMoods);
      router.push(`/recommend?session=${session.session_id}`);
    } catch (e: any) {
      toast.error(e.message ?? "Something went wrong");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Prompt */}
      <div>
        <h2 className="font-display font-bold text-2xl text-ink-primary mb-1">
          How are you feeling?
        </h2>
        <p className="text-ink-secondary text-sm">
          Pick up to {MAX_MOODS} moods — then set how strongly you feel each one.
        </p>
      </div>

      {/* Mood grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {MOODS.map((mood) => (
          <MoodPill
            key={mood.tag}
            mood={mood}
            selected={selectedTags.includes(mood.tag)}
            disabled={selectedMoods.length >= MAX_MOODS && !selectedTags.includes(mood.tag)}
            onClick={() => toggleMood(mood.tag)}
          />
        ))}
      </div>

      {/* Per-mood intensity sliders + CTA */}
      <AnimatePresence>
        {selectedMoods.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="space-y-4"
          >
            {/* Counter badge */}
            <div className="flex items-center justify-between">
              <p className="text-ink-secondary text-sm">
                Adjust the intensity for each mood
              </p>
              <span className="text-xs px-2 py-1 glass rounded-full text-ink-muted">
                {selectedMoods.length}/{MAX_MOODS}
              </span>
            </div>

            {/* Per-mood sliders — one per selected mood */}
            <div className="space-y-3">
              <AnimatePresence>
                {selectedMoods.map((mi) => {
                  const moodConfig = MOODS.find((m) => m.tag === mi.mood)!;
                  return (
                    <MoodIntensitySlider
                      key={mi.mood}
                      mood={moodConfig}
                      value={mi.intensity}
                      onChange={(v) => updateIntensity(mi.mood, v)}
                      onRemove={() => removeMood(mi.mood)}
                    />
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-glow w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-display font-bold text-white text-base disabled:opacity-60 mt-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  Finding your picks…
                </>
              ) : (
                <>
                  Find My Picks
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
