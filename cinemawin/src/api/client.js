// CinemaWin API client.
//
// This replaces the Base44 SDK the app was built on. It keeps the same call
// surface the pages were written against and speaks to one of two drivers:
//
//   server — a FastAPI backend (cinemawin/backend). Real accounts, a real
//            database, and real model calls. Used when the app is served by
//            that backend, or when the user points at a backend URL.
//
//   local  — no server at all. Projects live in this browser's localStorage
//            and the four story functions return sample output. This is what
//            makes the static GitHub Pages build usable with nothing to
//            install, host, or pay for.
//
// The driver is chosen at runtime, so the same build works both ways.

import { DEMO_FUNCTIONS } from "@/lib/demoData";
import { localProjects, localPlan, localStorageWorks } from "@/lib/localStore";

const TOKEN_KEY = "cinemawin_token";
const BACKEND_KEY = "cinemawin_backend_url";

// Set at build time. The GitHub Pages build sets "static"; the default build
// (served by the backend) leaves it unset.
const BUILD_MODE = import.meta.env.VITE_CINEMAWIN_MODE || "server";
const BUILD_API = (import.meta.env.VITE_CINEMAWIN_API || "").replace(/\/$/, "");

const FRIENDLY = {
  // Auth
  invalid_credentials: "That email and password don't match.",
  email_not_verified: "Please verify your email before signing in.",
  email_already_registered: "An account with that email already exists.",
  invalid_or_expired_code: "That code is invalid or has expired.",
  invalid_or_expired_token: "That reset link is invalid or has expired.",
  invalid_email: "That doesn't look like a valid email address.",
  not_authenticated: "Your session has expired. Please sign in again.",
  invalid_token: "Your session has expired. Please sign in again.",
  // Projects
  project_not_found: "That project no longer exists. It may have been deleted.",
  title_required: "Please give the project a title.",
  // Functions
  logline_required: "Please describe your idea in a sentence first.",
  rate_limited: "You've hit the limit for now — please try again in a little while.",
  llm_not_configured:
    "The story engine has no AI provider configured on the server. Add a provider key to the backend, or turn on demo mode.",
  llm_error: "The story engine hit a problem. Please try again.",
  llm_refused: "The AI provider declined this request. Try rephrasing your idea.",
  // Generic
  invalid_json: "That request was malformed. Please try again.",
  body_must_be_object: "That request was malformed. Please try again.",
};

export class ApiError extends Error {
  constructor(status, detail, data) {
    super(FRIENDLY[detail] || (typeof detail === "string" ? detail : "Request failed"));
    this.name = "ApiError";
    this.status = status;
    this.code = detail;
    this.data = data;
  }
}

// ── Token + backend URL storage ─────────────────────────────────────────────

function readToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private window) — the session just won't persist */
  }
}

export function getBackendUrl() {
  try {
    const stored = window.localStorage.getItem(BACKEND_KEY);
    if (stored) return stored.replace(/\/$/, "");
  } catch {
    /* ignore */
  }
  return BUILD_API;
}

export function setBackendUrl(url) {
  const clean = (url || "").trim().replace(/\/$/, "");
  try {
    if (clean) window.localStorage.setItem(BACKEND_KEY, clean);
    else window.localStorage.removeItem(BACKEND_KEY);
  } catch {
    /* ignore */
  }
}

/** True when there is no server and everything runs in this browser. */
export function isLocalMode() {
  return BUILD_MODE === "static" && !getBackendUrl();
}

function apiBase() {
  const backend = getBackendUrl();
  return backend ? `${backend}/api` : "/api";
}

// ── HTTP ────────────────────────────────────────────────────────────────────

async function request(method, path, body, { auth = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = auth ? readToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${apiBase()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the CinemaWin server.", null);
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    let detail = data && typeof data === "object" ? data.detail : data;
    if (Array.isArray(detail)) {
      // FastAPI validation errors — surface the first message.
      detail = detail[0]?.msg || "Please check the form and try again.";
    }
    // An expired or invalid session must not leave a dead token behind,
    // or every later action fails with the same opaque error.
    if (res.status === 401 && auth) writeToken(null);
    throw new ApiError(res.status, detail || `Request failed (${res.status})`, data);
  }
  return data;
}

function currentPath() {
  if (BUILD_MODE === "static") {
    const hash = window.location.hash.replace(/^#/, "");
    return hash || "/";
  }
  return window.location.pathname + window.location.search;
}

/**
 * A full page navigation that works under both routers. The static build uses
 * hash routing, where "/workspace" must be written as "#/workspace".
 */
export function navigateHard(path) {
  window.location.href = BUILD_MODE === "static" ? `#${path}` : path;
  if (BUILD_MODE === "static") window.location.reload();
}

// ── Local-mode helpers ──────────────────────────────────────────────────────

const LOCAL_USER = {
  id: "usr_local",
  email: "you@this-browser",
  plan: "entry",
  role: "user",
  email_verified: true,
  created_date: new Date(0).toISOString(),
  local: true,
};

function localUser() {
  return { ...LOCAL_USER, plan: localPlan() };
}

function wrapLocal(fn) {
  // localProjects throws plain Errors with .status/.code; normalise them so
  // callers only ever have to understand ApiError.
  try {
    return Promise.resolve(fn());
  } catch (e) {
    return Promise.reject(new ApiError(e.status || 500, e.code || e.message, null));
  }
}

// ── Public surface ──────────────────────────────────────────────────────────

export const cw = {
  getToken: readToken,
  isLocalMode,
  getBackendUrl,
  setBackendUrl,
  localStorageWorks,

  auth: {
    setToken(token) {
      writeToken(token);
    },
    async me() {
      if (isLocalMode()) return localUser();
      return request("GET", "/auth/me");
    },
    async isAuthenticated() {
      if (isLocalMode()) return true;
      if (!readToken()) return false;
      try {
        await request("GET", "/auth/me");
        return true;
      } catch {
        return false;
      }
    },
    async loginViaEmailPassword(email, password) {
      const res = await request("POST", "/auth/login", { email, password }, { auth: false });
      writeToken(res.access_token);
      return res;
    },
    async register({ email, password }) {
      const res = await request("POST", "/auth/register", { email, password }, { auth: false });
      if (res.access_token) writeToken(res.access_token);
      return res;
    },
    async verifyOtp({ email, otpCode }) {
      const res = await request("POST", "/auth/verify-otp", { email, code: otpCode }, { auth: false });
      if (res.access_token) writeToken(res.access_token);
      return res;
    },
    async resendOtp(email) {
      return request("POST", "/auth/resend-otp", { email }, { auth: false });
    },
    async resetPasswordRequest(email) {
      return request("POST", "/auth/forgot-password", { email }, { auth: false });
    },
    async resetPassword({ resetToken, newPassword }) {
      return request(
        "POST",
        "/auth/reset-password",
        { token: resetToken, new_password: newPassword },
        { auth: false },
      );
    },
    async logout(redirectUrl) {
      if (!isLocalMode()) {
        try {
          await request("POST", "/auth/logout");
        } catch {
          /* stateless logout — dropping the token is what matters */
        }
      }
      writeToken(null);
      if (redirectUrl) window.location.href = redirectUrl;
    },
    redirectToLogin(returnTo = currentPath()) {
      navigateHard(`/login?returnTo=${encodeURIComponent(returnTo)}`);
    },
    loginWithProvider() {
      throw new ApiError(501, "Social sign-in isn't enabled on this server.", null);
    },
  },

  entities: {
    Project: {
      list(sort = "-updated_date", limit = 50) {
        if (isLocalMode()) return wrapLocal(() => localProjects.list(sort, limit));
        const q = new URLSearchParams({ sort, limit: String(limit) });
        return request("GET", `/projects?${q}`);
      },
      get(id) {
        if (isLocalMode()) return wrapLocal(() => localProjects.get(id));
        return request("GET", `/projects/${encodeURIComponent(id)}`);
      },
      create(data) {
        if (isLocalMode()) return wrapLocal(() => localProjects.create(data));
        return request("POST", "/projects", data);
      },
      update(id, data) {
        if (isLocalMode()) return wrapLocal(() => localProjects.update(id, data));
        return request("PATCH", `/projects/${encodeURIComponent(id)}`, data);
      },
      delete(id) {
        if (isLocalMode()) return wrapLocal(() => localProjects.delete(id));
        return request("DELETE", `/projects/${encodeURIComponent(id)}`);
      },
    },
  },

  functions: {
    // Mirrors base44.functions.invoke → resolves to { data }.
    async invoke(name, payload) {
      if (isLocalMode()) {
        const fn = DEMO_FUNCTIONS[name];
        if (!fn) throw new ApiError(404, `Unknown function "${name}"`, null);
        const options = name === "buildFinance" ? { deckUnlocked: localPlan() === "premium" } : undefined;
        // A beat of latency so the loading states are visible rather than
        // flashing — the screens are written around a real request.
        await new Promise((resolve) => setTimeout(resolve, 450));
        return { data: fn(payload ?? {}, options) };
      }
      const data = await request("POST", `/functions/${encodeURIComponent(name)}`, payload ?? {});
      return { data };
    },
  },

  app: {
    async getPublicSettings() {
      if (isLocalMode()) {
        return {
          app_name: "CinemaWin",
          google_oauth_enabled: false,
          email_verification_required: false,
          demo_mode: true,
          local_mode: true,
          plans: { entry: { price: 0 }, starter: { price: 12 }, premium: { price: 29 } },
          llm: { provider: "", label: "Sample output (no server)", configured: false },
        };
      }
      const settings = await request("GET", "/app/public-settings", undefined, { auth: false });
      return { ...settings, local_mode: false };
    },
    health() {
      return request("GET", "/health", undefined, { auth: false });
    },
  },
};

export default cw;
