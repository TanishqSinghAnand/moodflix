"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/hooks/useAuth";
import {
  apiGetRecommendations,
  apiSubmitFeedback,
  type RecommendationResponse,
  type RecommendedTitle,
} from "@/lib/api";
import { getMoodConfig } from "@/lib/moods";
import NavBar from "@/components/layout/NavBar";
import MediaCard from "@/components/media/MediaCard";
import { Sparkles, RefreshCw, ChevronLeft } from "lucide-react";
import toast from "react-hot-toast";

function RecommendContent() {
  const router    = useRouter();
  const params    = useSearchParams();
  const { user, loading, init } = useAuthStore();
  const sessionId = params.get("session");

  const [data,     setData]     = useState<RecommendationResponse | null>(null);
  const [fetching, setFetching] = useState(true);
  const [feedback, setFeedback] = useState<Record<string, boolean>>({});

  useEffect(() => { const unsub = init(); return unsub; }, [init]);
  useEffect(() => { if (!loading && !user) router.push("/"); }, [user, loading, router]);

  useEffect(() => {
    if (!sessionId || !user) return;
    setFetching(true);
    apiGetRecommendations(sessionId)
      .then(setData)
      .catch((e) => { toast.error(e.message ?? "Failed to load"); router.push("/dashboard"); })
      .finally(() => setFetching(false));
  }, [sessionId, user]);

  const handleFeedback = async (title: RecommendedTitle, relevant: boolean) => {
    if (!sessionId) return;
    setFeedback(prev => ({ ...prev, [title.id]: relevant }));
    await apiSubmitFeedback({ title_id: title.id, session_id: sessionId, relevant }).catch(() => {});
    toast(relevant ? "👍 Thanks!" : "👎 Noted!", { icon: "🎯" });
  };

  if (loading || fetching) {
    return (
      <div className="min-h-dvh flex flex-col">
        <NavBar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            className="w-10 h-10 rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-ink-secondary text-sm animate-pulse">Finding your perfect watch...</p>
        </div>
      </div>
    );
  }

  if (!data) return null;
  const moodConfigs = data.moods.map(getMoodConfig);

  return (
    <div className="min-h-dvh flex flex-col">
      <NavBar />
      <div className="max-w-5xl mx-auto w-full px-4 py-8">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <button onClick={() => router.push("/dashboard")}
            className="flex items-center gap-1 text-ink-secondary text-sm mb-4 hover:text-ink-primary transition-colors">
            <ChevronLeft size={16} /> Back
          </button>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="font-display font-bold text-3xl mb-2">Your picks for tonight ✨</h1>
              <div className="flex flex-wrap gap-2">
                {moodConfigs.map((m) => (
                  <span key={m.tag} className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${m.color} ${m.textColor}`}>
                    {m.emoji} {m.label}
                  </span>
                ))}
              </div>
            </div>
            <button onClick={() => router.push("/dashboard")}
              className="flex items-center gap-2 px-4 py-2 glass rounded-xl text-sm text-ink-secondary hover:text-ink-primary transition-colors">
              <RefreshCw size={14} /> Change mood
            </button>
          </div>
        </motion.div>

        {data.serendipity_pick && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-accent" />
              <span className="text-accent text-sm font-medium">Wildcard Pick — Try Something New</span>
            </div>
            <MediaCard title={data.serendipity_pick} sessionId={data.session_id}
              feedback={feedback[data.serendipity_pick.id]}
              onFeedback={(r) => handleFeedback(data.serendipity_pick!, r)} featured />
          </motion.div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <AnimatePresence>
            {data.results.map((title, i) => (
              <motion.div key={title.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}>
                <MediaCard title={title} sessionId={data.session_id}
                  feedback={feedback[title.id]} onFeedback={(r) => handleFeedback(title, r)} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {data.results.length === 0 && (
          <div className="text-center py-20 text-ink-secondary">
            <p className="text-4xl mb-4">🎬</p>
            <p>No results found. Try importing your watch history first!</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RecommendPage() {
  return (
    <Suspense fallback={
      <div className="min-h-dvh flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    }>
      <RecommendContent />
    </Suspense>
  );
}
