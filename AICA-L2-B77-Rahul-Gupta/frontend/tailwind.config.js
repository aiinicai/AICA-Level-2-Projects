/** CompanyVal AI design tokens — derived from the finalized UI mockups. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#F4F7FB",
        surface: "#FFFFFF",
        line: "#E5EAF2",
        navy: "#0F1F3D",
        slate2: "#5B6B84",
        slate3: "#8A97AB",
        primary: {
          DEFAULT: "#2563EB",
          50: "#EFF4FF",
          100: "#DBE7FF",
          600: "#2563EB",
          700: "#1D4ED8",
        },
        mint: { DEFAULT: "#10B981", bg: "#E7F8F1", text: "#0B8F6B" },
        teal2: "#14B8A6",
        warn: { DEFAULT: "#F59E0B", bg: "#FEF4E0", text: "#B45309" },
        risk: { DEFAULT: "#EF4444", bg: "#FDE8E8", text: "#C0392B" },
        violet2: { DEFAULT: "#8B5CF6", bg: "#F1EBFE" },
      },
      borderRadius: {
        xl2: "14px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,31,61,0.04), 0 4px 14px rgba(15,31,61,0.05)",
        pop: "0 8px 30px rgba(15,31,61,0.12)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
