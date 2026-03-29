"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import type { RecommendedTitle } from "@/lib/api";
import { getMoodConfig } from "@/lib/moods";
import { Star, ThumbsUp, ThumbsDown, Info } from "lucide-react";

interface Props {
  title:      RecommendedTitle;
  sessionId:  string;
  feedback?:  boolean;          // undefined = not given, true = liked, false = disliked
  onFeedback: (relevant: boolean) => void;
  featured?:  boolean;
}

export default function MediaCard({ title, sessionId, feedback, onFeedback, featured }: Props) {
  const [showInfo, setShowInfo] = useState(false);

  const primaryMood = title.mood_tags[0] ? getMoodConfig(title.mood_tags[0]) : null;

  /* ── Featured (wide) layout ──────────────────────────────────────────── */
  if (featured) {
    return (
      <motion.div
        className="relative overflow-hidden rounded-3xl glass gradient-border group cursor-pointer"
        whileHover={{ scale: 1.01 }}
        transition={{ duration: 0.2 }}
      >
        {/* Backdrop image */}
        {title.backdrop_url && (
          <div className="absolute inset-0">
            <Image
              src={title.backdrop_url}
              alt={title.title}
              fill
              className="object-cover opacity-30 group-hover:opacity-40 transition-opacity duration-300"
              sizes="(max-width: 768px) 100vw, 900px"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-bg-card via-bg-card/80 to-transparent" />
          </div>
        )}

        <div className="relative p-6 flex gap-5 items-start">
          {/* Poster */}
          {title.poster_url && (
            <div className="flex-shrink-0 w-24 h-36 rounded-xl overflow-hidden shadow-lg shadow-black/40">
              <Image
                src={title.poster_url}
                alt={title.title}
                width={96}
                height={144}
                className="object-cover w-full h-full"
              />
            </div>
          )}

          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              {primaryMood && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${primaryMood.color} ${primaryMood.textColor}`}>
                  {primaryMood.emoji} {primaryMood.label}
                </span>
              )}
              <span className="text-xs px-2 py-0.5 rounded-full glass text-ink-muted capitalize">
                {title.media_type}
              </span>
            </div>

            <h3 className="font-display font-bold text-xl text-ink-primary leading-tight">
              {title.title}
            </h3>

            {title.overview && (
              <p className="text-ink-secondary text-sm leading-relaxed line-clamp-2">
                {title.overview}
              </p>
            )}

            <p className="text-accent text-sm font-medium">{title.reason}</p>

            <div className="flex items-center gap-4 pt-1">
              {title.rating && (
                <span className="flex items-center gap-1 text-yellow-400 text-sm">
                  <Star size={12} fill="currentColor" />
                  {title.rating.toFixed(1)}
                </span>
              )}
              {title.release_year && (
                <span className="text-ink-muted text-sm">{title.release_year}</span>
              )}
              <FeedbackButtons feedback={feedback} onFeedback={onFeedback} />
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  /* ── Standard (card) layout ──────────────────────────────────────────── */
  return (
    <motion.div
      className="group relative rounded-2xl overflow-hidden glass cursor-pointer"
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
      onClick={() => setShowInfo(!showInfo)}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] bg-bg-elevated overflow-hidden">
        {title.poster_url ? (
          <Image
            src={title.poster_url}
            alt={title.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl text-ink-muted">
            🎬
          </div>
        )}

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Mood badge */}
        {primaryMood && (
          <div className={`absolute top-2 left-2 text-xs px-2 py-0.5 rounded-full font-medium ${primaryMood.color} ${primaryMood.textColor}`}>
            {primaryMood.emoji}
          </div>
        )}

        {/* Rating */}
        {title.rating && (
          <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/60 text-yellow-400 text-xs">
            <Star size={10} fill="currentColor" />
            {title.rating.toFixed(1)}
          </div>
        )}

        {/* Info overlay on hover */}
        <AnimatePresence>
          {showInfo && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/85 p-3 flex flex-col justify-end"
              onClick={(e) => e.stopPropagation()}
            >
              <p className="text-white text-xs leading-relaxed line-clamp-4 mb-2">
                {title.overview ?? "No description available."}
              </p>
              <p className="text-accent text-xs">{title.reason}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="p-3 space-y-1">
        <h3 className="font-display font-semibold text-sm text-ink-primary leading-tight line-clamp-1">
          {title.title}
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-ink-muted text-xs capitalize">{title.media_type} {title.release_year ? `· ${title.release_year}` : ""}</span>
          <FeedbackButtons feedback={feedback} onFeedback={onFeedback} compact />
        </div>
      </div>
    </motion.div>
  );
}

/* ── Feedback buttons sub-component ──────────────────────────────────────── */

function FeedbackButtons({
  feedback,
  onFeedback,
  compact = false,
}: {
  feedback?:  boolean;
  onFeedback: (r: boolean) => void;
  compact?:   boolean;
}) {
  const size = compact ? 12 : 14;

  if (feedback !== undefined) {
    return (
      <span className="text-xs text-ink-muted">
        {feedback ? "👍" : "👎"} Noted
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => onFeedback(true)}
        className="p-1 rounded-lg hover:bg-emerald-500/20 hover:text-emerald-400 text-ink-muted transition-colors"
        title="Good pick"
      >
        <ThumbsUp size={size} />
      </button>
      <button
        onClick={() => onFeedback(false)}
        className="p-1 rounded-lg hover:bg-red-500/20 hover:text-red-400 text-ink-muted transition-colors"
        title="Not for me"
      >
        <ThumbsDown size={size} />
      </button>
    </div>
  );
}
