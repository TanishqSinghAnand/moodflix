/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // ── Brand Colors ──────────────────────────────────────────────────────────
      colors: {
        // Background palette — deep almost-black with subtle warm undertone
        bg: {
          base:    "#0A090C",
          surface: "#111014",
          card:    "#18161C",
          elevated:"#201D26",
        },
        // Accent — electric violet-to-pink for Gen Z energy
        accent: {
          DEFAULT: "#C084FC",   // violet-400
          hot:     "#F472B6",   // pink-400
          glow:    "#A855F7",   // violet-500
        },
        // Neutral text
        ink: {
          primary:   "#F4F0FF",
          secondary: "#9B96A8",
          muted:     "#524F5C",
        },
        // Mood pill colors
        mood: {
          uplifting:    "#FCD34D",
          relaxing:     "#6EE7B7",
          thrilling:    "#F87171",
          nostalgic:    "#93C5FD",
          dark:         "#818CF8",
          romantic:     "#F9A8D4",
          adventurous:  "#FB923C",
          funny:        "#FDE68A",
          emotional:    "#A78BFA",
          mind_bending: "#67E8F9",
        },
      },

      // ── Typography ─────────────────────────────────────────────────────────────
      fontFamily: {
        // Display: bold, chunky editorial font
        display: ["'Clash Display'", "'DM Sans'", "sans-serif"],
        // Body: clean variable font
        body:    ["'Satoshi'", "'DM Sans'", "sans-serif"],
        // Mono for tags/labels
        mono:    ["'JetBrains Mono'", "monospace"],
      },

      // ── Spacing ────────────────────────────────────────────────────────────────
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
      },

      // ── Animations ─────────────────────────────────────────────────────────────
      keyframes: {
        "float-up": {
          "0%":   { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(168, 85, 247, 0.3)" },
          "50%":      { boxShadow: "0 0 40px rgba(168, 85, 247, 0.6)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "card-in": {
          "0%":   { opacity: "0", transform: "scale(0.95) translateY(12px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
      },
      animation: {
        "float-up":   "float-up 0.5s ease-out forwards",
        "glow-pulse":  "glow-pulse 2s ease-in-out infinite",
        "shimmer":    "shimmer 2s linear infinite",
        "card-in":    "card-in 0.4s ease-out forwards",
      },

      // ── Border Radius ──────────────────────────────────────────────────────────
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },

      // ── Backdrop Blur ─────────────────────────────────────────────────────────
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
