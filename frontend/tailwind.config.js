import typography from "@tailwindcss/typography";
import plugin from "tailwindcss/plugin";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      animationDelay: {
        0: "0ms",
        75: "75ms",
        150: "150ms",
      },
    },
  },
  plugins: [
    typography,
    plugin(({ matchUtilities, theme }) => {
      matchUtilities(
        {
          delay: (value) => ({ animationDelay: value }),
        },
        { values: theme("animationDelay") }
      );
    }),
  ],
};
