"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { MOODS, type MoodConfig } from "@/lib/moods";
import { apiCreateMoodSession } from "@/lib/api";
import type { MoodTag } from "@/lib/api";
import { ArrowRight, Check } from "lucide-react";
import toast from "react-hot-toast";

/* ── Single mood pill ─────────────────────────────────────────────────────── */

function MoodPill({
  mood,
  selected,
  onClick,
}: {
  mood:     MoodConfig;
  selected: boolean;
  onClick:  () => void;
}) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.97 }}
      className={`
        relative flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-200
        ${selected
          ? `${mood.color} border-current ${mood.textColor}`
          : "glass border-transparent hover:border-white/10 text-ink-secondary hover:text-ink-primary"
        }
      `}
    >
      {/* Checkmark badge */}
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

/* ── Intensity slider ─────────────────────────────────────────────────────── */

function IntensitySlider({
  value,
  onChange,
}: {
  value:    number;
  onChange: (v: number) => void;
}) {
  const labels = ["Casual", "Moderate", "Intense"];
  const label  = value <= 3 ? labels[0] : value <= 7 ? labels[1] : labels[2];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-ink-secondary">Intensity</span>
        <span className="text-accent font-medium">{label}</span>
      </div>
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 appearance-none rounded-full bg-bg-elevated cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-5
          [&::-webkit-slider-thumb]:h-5
          [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-accent
          [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:shadow-lg
          [&::-webkit-slider-thumb]:shadow-accent/30"
        style={{
          background: `linear-gradient(to right, #A855F7 ${(value - 1) * 11.1}%, #201D26 ${(value - 1) * 11.1}%)`,
        }}
      />
    </div>
  );
}

/* ── Main MoodPicker ──────────────────────────────────────────────────────── */

export default function MoodPicker() {
  const router    = useRouter();
  const [selected, setSelected] = useState<MoodTag[]>([]);
  const [intensity, setIntensity] = useState(5);
  const [loading,  setLoading]  = useState(false);

  const MAX_MOODS = 3;

  const toggle = (tag: MoodTag) => {
    setSelected(prev => {
      if (prev.includes(tag)) return prev.filter(t => t !== tag);
      if (prev.length >= MAX_MOODS) {
        toast(`Pick up to ${MAX_MOODS} moods`, { icon: "💡" });
        return prev;
      }
      return [...prev, tag];
    });
  };

  const handleSubmit = async () => {
    if (selected.length === 0) {
      toast.error("Pick at least one mood first!");
      return;
    }
    setLoading(true);
    try {
      const session = await apiCreateMoodSession(selected, intensity);
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
          Pick up to {MAX_MOODS} moods — we'll match your vibe.
        </p>
      </div>

      {/* Mood grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {MOODS.map((mood) => (
          <MoodPill
            key={mood.tag}
            mood={mood}
            selected={selected.includes(mood.tag)}
            onClick={() => toggle(mood.tag)}
          />
        ))}
      </div>

      {/* Intensity + CTA — shown when at least 1 mood selected */}
      <AnimatePresence>
        {selected.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="space-y-6 p-6 glass rounded-2xl"
          >
            {/* Selected badges */}
            <div className="flex flex-wrap gap-2">
              {selected.map(tag => {
                const m = MOODS.find(x => x.tag === tag)!;
                return (
                  <span
                    key={tag}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${m.color} ${m.textColor}`}
                  >
                    {m.emoji} {m.label}
                  </span>
                );
              })}
            </div>

            <IntensitySlider value={intensity} onChange={setIntensity} />

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-glow w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-display font-bold text-white text-base disabled:opacity-60"
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
