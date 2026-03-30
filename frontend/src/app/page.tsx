"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuthStore } from "@/hooks/useAuth";
import { Sparkles, Play, Upload, Zap } from "lucide-react";

/* ── Animation helpers ──────────────────────────────────────────────────── */

const fadeUp = {
  hidden:  { opacity: 0, y: 24 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1], delay },
  }),
};

/* ── Feature pill ────────────────────────────────────────────────────────── */

function FeaturePill({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-full glass text-ink-secondary text-sm">
      <span className="text-accent">{icon}</span>
      {text}
    </div>
  );
}

/* ── Floating mood demo badges ─────────────────────────────────────────── */

const DEMO_MOODS = [
  { emoji: "⚡", label: "Thrilling", top: "10%",  left: "5%",  delay: 0.2 },
  { emoji: "☀️", label: "Feel-Good", top: "20%",  right: "8%", delay: 0.4 },
  { emoji: "🌀", label: "Mind-Bending", top: "65%", left: "3%", delay: 0.6 },
  { emoji: "💗", label: "Romance",   bottom: "20%", right: "5%", delay: 0.8 },
  { emoji: "🌿", label: "Chill",     bottom: "35%", left: "8%", delay: 1.0 },
];

export default function HomePage() {
  const router  = useRouter();
  const { user, loading, init, signInGoogle } = useAuthStore();

  // Initialize Firebase auth listener
  useEffect(() => {
    const unsub = init();
    return unsub;
  }, [init]);

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (!loading && user) router.push("/dashboard");
  }, [user, loading, router]);

  return (
    <div className="relative min-h-dvh flex flex-col items-center justify-center px-6 overflow-hidden">

      {/* ── Floating mood badges ──────────────────────────────────────── */}
      {DEMO_MOODS.map((mood) => (
        <motion.div
          key={mood.label}
          className="absolute hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full glass text-sm text-ink-secondary pointer-events-none"
          style={{
            top:    mood.top,
            left:   mood.left,
            right:  mood.right,
            bottom: mood.bottom,
          }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{
            opacity: [0, 1, 1, 0.7],
            scale:   [0.8, 1, 1, 1],
            y:       [0, -8, 0, -4],
          }}
          transition={{
            delay:    mood.delay,
            duration: 4,
            repeat:   Infinity,
            repeatType: "reverse",
          }}
        >
          <span>{mood.emoji}</span>
          {mood.label}
        </motion.div>
      ))}

      {/* ── Hero content ─────────────────────────────────────────────── */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-2xl">

        {/* Badge */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0}
          className="flex items-center gap-2 px-4 py-1.5 rounded-full glass mb-8 text-sm text-accent"
        >
          <Sparkles size={14} />
          <span>AI-Powered Mood Matching</span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.1}
          className="font-display font-bold text-5xl sm:text-6xl md:text-7xl leading-none tracking-tight balance mb-6"
        >
          Watch what{" "}
          <span className="gradient-text">matches<br />your vibe</span>
        </motion.h1>

        {/* Sub */}
        <motion.p
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.2}
          className="text-ink-secondary text-lg sm:text-xl leading-relaxed mb-10 max-w-md"
        >
          Stop scrolling forever. Tell us how you feel — we'll find the perfect movie, series, or anime for tonight.
        </motion.p>

        {/* CTA */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.3}
          className="flex flex-col sm:flex-row gap-3"
        >
          <button
            onClick={signInGoogle}
            disabled={loading}
            className="btn-glow px-8 py-3.5 rounded-2xl font-display font-semibold text-white text-base flex items-center gap-2 disabled:opacity-60"
          >
            <Play size={16} fill="white" />
            Get Started Free
          </button>

          <button
            onClick={signInGoogle}
            className="px-8 py-3.5 rounded-2xl glass font-body font-medium text-ink-primary text-base hover:bg-white/5 transition-colors"
          >
            Sign in with Google
          </button>
        </motion.div>

        {/* Feature pills */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.5}
          className="flex flex-wrap justify-center gap-2 mt-12"
        >
          <FeaturePill icon={<Zap size={13} />}     text="Mood-aware AI" />
          <FeaturePill icon={<Upload size={13} />}  text="Netflix · Prime · MAL" />
          <FeaturePill icon={<Sparkles size={13} />} text="Movies + Anime" />
        </motion.div>
      </div>

      {/* ── Bottom fade ──────────────────────────────────────────────── */}
      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-bg-base to-transparent pointer-events-none" />
    </div>
  );
}