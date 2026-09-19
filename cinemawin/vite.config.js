import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// CinemaWin frontend. In development the FastAPI backend (cinemawin/backend,
// port 8002) is reached through the /api proxy below, so the browser only ever
// talks to one origin. In production the backend serves ./dist itself.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/api": {
        target: "http://localhost:8002",
        changeOrigin: true,
      },
    },
  },
});
