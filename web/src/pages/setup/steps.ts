import type { SetupCheck, SetupState } from "../../lib/types";

export type StepId = "machine" | "server" | "translator" | "model" | "tv" | "addon";

export interface Step {
  id: StepId;
  title: string;
  blurb: string;
  checks: SetupCheck["id"][];
  // Steps only a person can do (on the TV, in Stremio) are confirmed with a tick instead.
  confirm?: string;
}

export const STEPS: Step[] = [
  { id: "machine", title: "This Mac", blurb: "Hardware, tools and disk", checks: ["mac", "tools", "server", "disk"] },
  { id: "server", title: "Streaming server", blurb: "Reachable by your TV", checks: ["server_tv", "https"] },
  { id: "translator", title: "Translator", blurb: "The AI that writes the subtitles", checks: ["translator"] },
  { id: "model", title: "Speech model", blurb: "Whisper, downloaded once", checks: ["model"] },
  {
    id: "tv",
    title: "Your TV",
    blurb: "Point Stremio at this Mac",
    checks: ["tv_connected"],
    // Fallback when the TV's requests can't be seen yet (e.g. it connected before this update).
    confirm: "The TV shows the server as online",
  },
  { id: "addon", title: "The addon", blurb: "Add Stremio++ to your account", checks: [], confirm: "Stremio++ is installed in my account" },
];

const CONFIRM_KEY = "stremio-plus-plus.setup.confirmed";

export function confirmed(): Set<StepId> {
  try {
    return new Set(JSON.parse(localStorage.getItem(CONFIRM_KEY) ?? "[]") as StepId[]);
  } catch {
    return new Set();
  }
}

export function saveConfirmed(ids: Set<StepId>): void {
  localStorage.setItem(CONFIRM_KEY, JSON.stringify([...ids]));
}

export function stepChecks(state: SetupState, step: Step): SetupCheck[] {
  return step.checks.flatMap((id) => state.checks.filter((c) => c.id === id));
}

/** Done = nothing red; warnings count as done only for the machine step (e.g. low-ish disk). */
export function stepDone(state: SetupState, step: Step, ticked: Set<StepId>): boolean {
  const checks = stepChecks(state, step);
  if (step.confirm) return ticked.has(step.id) || (checks.length > 0 && checks.every((c) => c.level === "ok"));
  return step.id === "machine"
    ? checks.every((c) => c.level !== "bad")
    : checks.every((c) => c.level === "ok");
}
