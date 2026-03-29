"use client";

import { useAuthStore } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion } from "framer-motion";
import { LogOut, Sparkles } from "lucide-react";

export default function NavBar() {
  const { user, signOut } = useAuthStore();
  const router = useRouter();

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-50 border-b border-white/5 glass"
    >
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <button
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-2 font-display font-bold text-xl"
        >
          <Sparkles size={18} className="text-accent" />
          <span className="gradient-text">MoodFlix</span>
        </button>

        {/* User menu */}
        {user && (
          <div className="flex items-center gap-3">
            {user.photoURL && (
              <Image
                src={user.photoURL}
                alt={user.displayName ?? "User"}
                width={30}
                height={30}
                className="rounded-full"
              />
            )}
            <span className="text-ink-secondary text-sm hidden sm:block">
              {user.displayName?.split(" ")[0]}
            </span>
            <button
              onClick={signOut}
              className="p-2 rounded-xl glass hover:bg-white/5 text-ink-muted hover:text-ink-primary transition-colors"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </motion.header>
  );
}
