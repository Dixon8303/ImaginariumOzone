// CinemaWin API client.
//
// This replaces the Base44 SDK the app was originally built on. It exposes the
// same surface the pages were written against (auth · entities.Project ·
// functions.invoke · app.getPublicSettings) but talks to the FastAPI backend in
// ../backend over plain fetch. Same origin in both dev (Vite proxies /api) and
// production (the backend serves ./dist), so no base URL configuration needed.

const TOKEN_KEY = "cinemawin_token";
const API_BASE = "/api";

const FRIENDLY = {
  invalid_credentials: "That email and password don't match.",
  email_not_verified: "Please verify your email before signing in.",
  email_already_registered: "An account with that email already exists.",
  invalid_or_expired_code: "That code is invalid or has expired.",
  invalid_or_expired_token: "That reset link is invalid or has expired.",
  rate_limited: "You've hit the limit for now — please try again in a little while.",
  llm_not_configured: "The story engine isn't configured on this server yet (missing ANTHROPIC_API_KEY).",
  llm_error: "The story engine hit a problem. Please try again.",
  llm_refused: "The story engine declined this request. Try rephrasing your idea.",
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
    /* storage unavailable (private mode) — session simply won't persist */
  }
}

async function request(method, path, body, { auth = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = auth ? readToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
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
    throw new ApiError(res.status, detail || `Request failed (${res.status})`, data);
  }
  return data;
}

function currentPath() {
  return window.location.pathname + window.location.search;
}

export const cw = {
  getToken: readToken,

  auth: {
    setToken(token) {
      writeToken(token);
    },
    async me() {
      return request("GET", "/auth/me");
    },
    async isAuthenticated() {
      if (!readToken()) return false;
      try {
        await request("GET", "/auth/me");
        return true;
      } catch (e) {
        if (e.status === 401) writeToken(null);
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
      return request("POST", "/auth/reset-password", { token: resetToken, new_password: newPassword }, { auth: false });
    },
    async logout(redirectUrl) {
      try {
        await request("POST", "/auth/logout");
      } catch {
        /* stateless logout — dropping the token is what matters */
      }
      writeToken(null);
      if (redirectUrl) window.location.href = redirectUrl;
    },
    redirectToLogin(returnTo = currentPath()) {
      window.location.href = `/login?returnTo=${encodeURIComponent(returnTo)}`;
    },
    loginWithProvider() {
      throw new ApiError(501, "Social sign-in isn't enabled on this server.", null);
    },
  },

  entities: {
    Project: {
      list(sort = "-updated_date", limit = 50) {
        const q = new URLSearchParams({ sort, limit: String(limit) });
        return request("GET", `/projects?${q}`);
      },
      get(id) {
        return request("GET", `/projects/${encodeURIComponent(id)}`);
      },
      create(data) {
        return request("POST", "/projects", data);
      },
      update(id, data) {
        return request("PATCH", `/projects/${encodeURIComponent(id)}`, data);
      },
      delete(id) {
        return request("DELETE", `/projects/${encodeURIComponent(id)}`);
      },
    },
  },

  functions: {
    // Mirrors base44.functions.invoke → resolves to { data }.
    async invoke(name, payload) {
      const data = await request("POST", `/functions/${encodeURIComponent(name)}`, payload ?? {});
      return { data };
    },
  },

  app: {
    getPublicSettings() {
      return request("GET", "/app/public-settings", undefined, { auth: false });
    },
    health() {
      return request("GET", "/health", undefined, { auth: false });
    },
  },
};

export default cw;
