"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuthStore } from "@/hooks/useAuth";
import { apiGetImportStatus } from "@/lib/api";
import MoodPicker from "@/components/mood/MoodPicker";
import ImportPanel from "@/components/media/ImportPanel";
import NavBar from "@/components/layout/NavBar";
import { Library, Sparkles } from "lucide-react";
import toast from "react-hot-toast";

type Tab = "mood" | "import";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, init } = useAuthStore();
  const [tab, setTab] = useState<Tab>("mood");
  const [importCounts, setImportCounts] = useState<Record<string, number>>({});

  // Initialize auth listener
  useEffect(() => {
    const unsub = init();
    return unsub;
  }, [init]);

  // Redirect to home if not authenticated
  useEffect(() => {
    if (!loading && !user) router.push("/");
  }, [user, loading, router]);

  // Load import stats
  useEffect(() => {
    if (!user) return;
    apiGetImportStatus()
      .then((r) => setImportCounts(r.totals))
      .catch(() => {}); // non-critical
  }, [user]);

  if (loading || !user) {
    return (
      <div className="min-h-dvh flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    );
  }

  const totalWatched = Object.values(importCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="min-h-dvh flex flex-col">
      <NavBar />

      <div className="flex-1 max-w-3xl mx-auto w-full px-4 py-8">

        {/* Greeting */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <p className="text-ink-secondary text-sm mb-1">
            {new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 18 ? "Good afternoon" : "Good evening"},{" "}
          </p>
          <h1 className="font-display font-bold text-3xl text-ink-primary">
            {user.displayName?.split(" ")[0] ?? "there"} 👋
          </h1>
          {totalWatched > 0 && (
            <p className="text-ink-secondary text-sm mt-1">
              {totalWatched.toLocaleString()} titles in your watch history
            </p>
          )}
        </motion.div>

        {/* Tab switcher */}
        <div className="flex gap-1 p-1 glass rounded-2xl mb-8 w-fit">
          {(["mood", "import"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                tab === t
                  ? "bg-accent/20 text-accent"
                  : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              {t === "mood" ? <Sparkles size={14} /> : <Library size={14} />}
              {t === "mood" ? "Pick Mood" : "Import History"}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {tab === "mood"   && <MoodPicker />}
          {tab === "import" && (
            <ImportPanel onImportSuccess={(platform, count) => {
              setImportCounts(prev => ({ ...prev, [platform]: (prev[platform] ?? 0) + count }));
              toast.success(`Imported ${count} titles from ${platform}!`);
            }} />
          )}
        </motion.div>
      </div>
    </div>
  );
}
