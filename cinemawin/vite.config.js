import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// CinemaWin frontend.
//
// Two builds come out of this one config:
//
//   default  — served by the FastAPI backend (cinemawin/backend). Browser
//              routing, /api on the same origin, dev server proxies to the
//              backend port.
//
//   static   — CINEMAWIN_MODE=static. A self-contained site for any static
//              host (GitHub Pages). Hash routing, projects in localStorage,
//              sample AI output until the user points it at a backend.
//
// CINEMAWIN_BASE sets the sub-path the site is served from, e.g.
// "/ImaginariumOzone/cinemawin/" for GitHub Pages project sites.
export default defineConfig(({ mode }) => {
  // Read CINEMAWIN_* from .env files as well as the shell, so the backend's
  // port setting is honoured by the dev proxy instead of being hardcoded.
  const env = { ...loadEnv(mode, process.cwd(), "CINEMAWIN"), ...process.env };
  const backendPort = env.CINEMAWIN_PORT || "8002";
  const appMode = env.CINEMAWIN_MODE === "static" ? "static" : "server";

  return {
    base: env.CINEMAWIN_BASE || "/",
    define: {
      // Surfaced to the app as import.meta.env.VITE_CINEMAWIN_MODE.
      "import.meta.env.VITE_CINEMAWIN_MODE": JSON.stringify(appMode),
      "import.meta.env.VITE_CINEMAWIN_API": JSON.stringify(env.CINEMAWIN_API || ""),
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: Number(env.CINEMAWIN_FRONTEND_PORT || 5174),
      proxy: {
        "/api": {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
