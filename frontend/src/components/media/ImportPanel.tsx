"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  apiImportNetflix,
  apiImportPrime,
  apiImportHotstar,
  apiImportMAL,
  type ImportResult,
} from "@/lib/api";
import { Upload, Check, AlertCircle, ExternalLink } from "lucide-react";
import toast from "react-hot-toast";

/* ── Platform config ──────────────────────────────────────────────────────── */

const PLATFORMS = [
  {
    id:       "netflix",
    label:    "Netflix",
    emoji:    "🎬",
    accept:   ".csv",
    helpUrl:  "https://www.netflix.com/viewingactivity",
    helpText: 'Go to netflix.com/viewingactivity → scroll down → "Download All"',
    fn:       apiImportNetflix,
  },
  {
    id:       "prime",
    label:    "Prime Video",
    emoji:    "📦",
    accept:   ".csv",
    helpUrl:  "https://github.com/twocaretcat/watch-history-exporter-for-amazon-prime-video",
    helpText: "Use the community browser script to export your watch history CSV.",
    fn:       apiImportPrime,
  },
  {
    id:       "hotstar",
    label:    "Hotstar",
    emoji:    "🌟",
    accept:   ".csv",
    helpUrl:  "https://github.com/twocaretcat/watch-history-exporter-for-amazon-prime-video",
    helpText: "Use the community browser script to export your watch history CSV.",
    fn:       apiImportHotstar,
  },
  {
    id:       "mal",
    label:    "MyAnimeList",
    emoji:    "🌸",
    accept:   ".xml",
    helpUrl:  "https://myanimelist.net/panel.php?go=export",
    helpText: "Log in → myanimelist.net/panel.php?go=export → Export Anime List.",
    fn:       apiImportMAL,
  },
] as const;

/* ── Single platform uploader ─────────────────────────────────────────────── */

function PlatformCard({
  platform,
  onSuccess,
}: {
  platform: (typeof PLATFORMS)[number];
  onSuccess: (platform: string, count: number) => void;
}) {
  const [status,  setStatus]  = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [result,  setResult]  = useState<ImportResult | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;

    setStatus("uploading");
    try {
      const res = await platform.fn(file);
      setResult(res);
      setStatus("done");
      onSuccess(platform.id, res.new_titles);
    } catch (e: any) {
      setStatus("error");
      toast.error(e.message ?? "Upload failed");
    }
  }, [platform]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { [platform.accept === ".csv" ? "text/csv" : "text/xml"]: [platform.accept] },
    maxFiles: 1,
    disabled: status === "uploading" || status === "done",
  });

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{platform.emoji}</span>
          <span className="font-display font-semibold text-ink-primary">{platform.label}</span>
        </div>
        <button
          onClick={() => setShowHelp(!showHelp)}
          className="text-xs text-ink-secondary hover:text-accent transition-colors flex items-center gap-1"
        >
          How to export
          <ExternalLink size={11} />
        </button>
      </div>

      {/* Help box */}
      <AnimatePresence>
        {showHelp && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 py-3 bg-accent/5 border-b border-white/5">
              <p className="text-ink-secondary text-xs leading-relaxed">{platform.helpText}</p>
              <a
                href={platform.helpUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent text-xs hover:underline mt-1 inline-block"
              >
                Open in new tab →
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drop zone */}
      <div className="p-4">
        {status === "done" && result ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-3 py-3 text-emerald-400"
          >
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <Check size={16} />
            </div>
            <div>
              <p className="font-medium text-sm">{result.new_titles} new titles imported</p>
              <p className="text-ink-muted text-xs">{result.skipped} already in library</p>
            </div>
          </motion.div>
        ) : (
          <div
            {...getRootProps()}
            className={`
              relative flex flex-col items-center justify-center gap-2 py-6 px-4
              border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200
              ${isDragActive
                ? "border-accent bg-accent/10"
                : status === "uploading"
                  ? "border-white/10 opacity-60 cursor-not-allowed"
                  : "border-white/10 hover:border-accent/50 hover:bg-accent/5"
              }
            `}
          >
            <input {...getInputProps()} />

            {status === "uploading" ? (
              <div className="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
            ) : (
              <Upload size={20} className={isDragActive ? "text-accent" : "text-ink-muted"} />
            )}

            <p className="text-sm text-ink-secondary text-center">
              {status === "uploading"
                ? "Uploading…"
                : isDragActive
                  ? "Drop it!"
                  : `Drop your ${platform.accept.toUpperCase()} here or click to browse`
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main ImportPanel ─────────────────────────────────────────────────────── */

export default function ImportPanel({
  onImportSuccess,
}: {
  onImportSuccess: (platform: string, count: number) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display font-bold text-2xl mb-1">Import Your History</h2>
        <p className="text-ink-secondary text-sm">
          Connect your watch history so we can personalize recommendations.
          Your data stays private and is only used to improve your suggestions.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {PLATFORMS.map((p) => (
          <PlatformCard
            key={p.id}
            platform={p}
            onSuccess={onImportSuccess}
          />
        ))}
      </div>

      <p className="text-ink-muted text-xs text-center">
        🔒 Your data is processed securely and never shared with third parties.
      </p>
    </div>
  );
}
