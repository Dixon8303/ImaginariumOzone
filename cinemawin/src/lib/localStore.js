// Browser-only storage for the static build.
//
// When CinemaWin is served from GitHub Pages there is no server and no
// database, so projects live in this browser's localStorage. That means:
// they are private to this browser, they are not backed up, and clearing
// site data deletes them. The UI says so; see ServerlessNotice.
//
// The shape returned here is identical to the API's Project shape, so the
// pages cannot tell which driver they are talking to.

const KEY = "cinemawin_projects";
const PLAN_KEY = "cinemawin_local_plan";

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(projects) {
  try {
    localStorage.setItem(KEY, JSON.stringify(projects));
    return true;
  } catch {
    // Quota exceeded or storage blocked (private window). The caller still
    // gets its object back so the current screen works; it just will not
    // survive a reload.
    return false;
  }
}

function newId() {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return "prj_" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function localPlan() {
  try {
    return localStorage.getItem(PLAN_KEY) || "entry";
  } catch {
    return "entry";
  }
}

export function setLocalPlan(plan) {
  try {
    localStorage.setItem(PLAN_KEY, plan);
  } catch {
    /* ignore */
  }
}

const TEXT_FIELDS = [
  "title", "logline", "track", "genre", "premise", "protagonist", "core_need",
  "emotional_wound", "central_question", "theme", "story_verdict_label",
  "story_headline", "first_step", "production_notes", "paywall_email",
];
const JSON_FIELDS = ["score_breakdown", "structure", "finance", "top_fixes"];
const OTHER_FIELDS = [
  "maturity_level", "current_module", "story_score", "story_verdict",
  "budget_ceiling", "paywall_email_captured",
];
const WRITABLE = new Set([...TEXT_FIELDS, ...JSON_FIELDS, ...OTHER_FIELDS]);

function withDerived(project) {
  const plan = localPlan();
  return {
    ...project,
    // Mirrors the server's derive_plan_flags so the paywall behaves the same.
    score_locked: plan === "entry",
    pitch_deck_unlocked: plan === "premium",
  };
}

function blank(id, now) {
  return {
    id,
    owner_id: "local",
    created_date: now,
    updated_date: now,
    title: "",
    logline: "",
    track: "Writer",
    genre: "",
    premise: "",
    protagonist: "",
    core_need: "",
    emotional_wound: "",
    central_question: "",
    theme: "",
    first_step: "",
    production_notes: "",
    paywall_email: "",
    maturity_level: 0,
    current_module: "develop",
    story_score: null,
    story_verdict: null,
    story_verdict_label: null,
    story_headline: null,
    score_breakdown: null,
    structure: null,
    finance: null,
    top_fixes: null,
    budget_ceiling: null,
    paywall_email_captured: false,
  };
}

function sanitize(data) {
  const out = {};
  for (const [key, value] of Object.entries(data || {})) {
    if (WRITABLE.has(key)) out[key] = value;
  }
  return out;
}

export const localProjects = {
  list(sort = "-updated_date", limit = 50) {
    const projects = read().map(withDerived);
    const desc = sort.startsWith("-");
    const field = desc ? sort.slice(1) : sort;
    projects.sort((a, b) => {
      const av = a[field] ?? "";
      const bv = b[field] ?? "";
      if (av === bv) return 0;
      return (av < bv ? -1 : 1) * (desc ? -1 : 1);
    });
    return projects.slice(0, limit);
  },

  get(id) {
    const found = read().find((p) => p.id === id);
    if (!found) {
      const error = new Error("project_not_found");
      error.status = 404;
      error.code = "project_not_found";
      throw error;
    }
    return withDerived(found);
  },

  create(data) {
    const now = new Date().toISOString();
    const project = { ...blank(newId(), now), ...sanitize(data) };
    if (!project.title) {
      const error = new Error("title_required");
      error.status = 422;
      error.code = "title_required";
      throw error;
    }
    const projects = read();
    projects.push(project);
    write(projects);
    return withDerived(project);
  },

  update(id, data) {
    const projects = read();
    const index = projects.findIndex((p) => p.id === id);
    if (index === -1) {
      const error = new Error("project_not_found");
      error.status = 404;
      error.code = "project_not_found";
      throw error;
    }
    projects[index] = {
      ...projects[index],
      ...sanitize(data),
      updated_date: new Date().toISOString(),
    };
    write(projects);
    return withDerived(projects[index]);
  },

  delete(id) {
    write(read().filter((p) => p.id !== id));
    return { ok: true };
  },
};

export function localStorageWorks() {
  try {
    const probe = "__cinemawin_probe__";
    localStorage.setItem(probe, "1");
    localStorage.removeItem(probe);
    return true;
  } catch {
    return false;
  }
}
