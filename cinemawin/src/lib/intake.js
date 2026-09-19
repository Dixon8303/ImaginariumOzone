import { cw } from "@/api/client";

// The Get Started flow runs before sign-up. If the visitor develops a story and
// then has to create an account, the developed material is parked here and
// turned into a real project the moment they are authenticated.
const KEY = "cinemawin_intake";

export function stashIntake(intake) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(intake));
  } catch {
    /* sessionStorage unavailable — the visitor can re-enter the idea */
  }
}

export function hasPendingIntake() {
  try {
    return !!sessionStorage.getItem(KEY);
  } catch {
    return false;
  }
}

// Creates the parked project (if any) and returns it, or null.
export async function consumePendingIntake() {
  let intake = null;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    intake = JSON.parse(raw);
  } catch {
    return null;
  }
  try {
    const project = await cw.entities.Project.create({
      title: intake.title,
      logline: intake.logline,
      track: intake.track,
      genre: intake.genre,
      premise: intake.premise,
      protagonist: intake.protagonist,
      core_need: intake.core_need,
      emotional_wound: intake.emotional_wound,
      central_question: intake.central_question,
      theme: intake.theme,
      first_step: intake.first_step,
      maturity_level: intake.maturity_level ?? 1,
      current_module: "develop",
    });
    sessionStorage.removeItem(KEY);
    return project;
  } catch {
    // Leave the intake parked so the next successful sign-in can retry.
    return null;
  }
}

// Where to send a freshly authenticated user: their new project if an intake
// was waiting, otherwise the requested returnTo.
export async function postAuthDestination(returnTo) {
  const project = await consumePendingIntake();
  if (project) return `/project/${project.id}/develop`;
  return returnTo;
}
