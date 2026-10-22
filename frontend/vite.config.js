import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Split vendor code into long-lived chunks.
 *
 * Vite 8 bundles with Rolldown, which requires `manualChunks` to be a function
 * (the object form that worked with Rollup throws "manualChunks is not a
 * function"). The function form works for both bundlers.
 */
const manualChunks = (id) => {
  if (!id.includes("node_modules")) return undefined;
  if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "vendor";
  if (/node_modules\/(react-markdown|remark-[^/]+|rehype-[^/]+|highlight\.js|lowlight|unified|micromark|mdast-[^/]+|hast-[^/]+|property-information|space-separated-tokens|comma-separated-tokens|character-entities[^/]*|decode-named-character-reference|trim-lines|devlop|vfile[^/]*|unist-[^/]+|bail|trough|is-plain-obj|html-url-attributes|longest-streak|markdown-table|zwitch|ccount|escape-string-regexp|extend|style-to-[^/]+)\//.test(
    id,
  )) {
    return "markdown";
  }
  return undefined;
};

export default defineConfig({
  plugins: [react()],
  server: {
    // Lets `npm run dev` talk to the backend without any env configuration.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: { manualChunks },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.{js,jsx}"],
  },
});
