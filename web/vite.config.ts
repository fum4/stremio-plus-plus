import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";
import { mockApi } from "./mock/api.ts";

// `npm run dev` proxies /api to a running companion (COMPANION_URL, default the LAN host);
// `npm run dev:mock` serves canned data instead, for UI work without a host.
export default defineConfig(({ mode }) => ({
  plugins: [svelte(), ...(mode === "mock" ? [mockApi()] : [])],
  server: {
    proxy:
      mode === "mock"
        ? undefined
        : { "/api": { target: process.env.COMPANION_URL ?? "http://localhost:11471" } },
  },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 300 },
}));
