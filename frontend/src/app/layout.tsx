import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "MoodFlix — Watch What Matches Your Vibe",
  description: "AI-powered movie & anime recommendations based on how you feel right now.",
  openGraph: {
    title: "MoodFlix",
    description: "Watch what matches your vibe.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        {/* Global ambient glow — decorative background blobs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden>
          <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-accent-glow/10 blur-3xl" />
          <div className="absolute top-1/2 -right-40 w-80 h-80 rounded-full bg-accent-hot/8 blur-3xl" />
          <div className="absolute -bottom-20 left-1/3 w-64 h-64 rounded-full bg-accent/6 blur-3xl" />
        </div>

        <main className="relative z-10 min-h-dvh">
          {children}
        </main>

        {/* Toast notifications */}
        <Toaster
          position="bottom-center"
          toastOptions={{
            style: {
              background: "#18161C",
              color: "#F4F0FF",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
              fontFamily: "Satoshi, sans-serif",
              fontSize: "14px",
            },
            success: { iconTheme: { primary: "#C084FC", secondary: "#0A090C" } },
            error:   { iconTheme: { primary: "#F87171", secondary: "#0A090C" } },
          }}
        />
      </body>
    </html>
  );
}
