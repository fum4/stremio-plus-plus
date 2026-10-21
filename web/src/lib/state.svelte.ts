import { api, ApiError } from "./api";
import type { Provider, Settings, SettingsView, Status } from "./types";

const STATUS_POLL_MS = 2000;

export type ToastKind = "success" | "info" | "error";
export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  body?: string;
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** Only the leaves that differ: a save then never reverts a hand edit to another key. */
function changes(base: object, next: object): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(next)) {
    const was = (base as Record<string, unknown>)[key];
    if (value && typeof value === "object" && was && typeof was === "object") {
      const inner = changes(was, value as object);
      if (Object.keys(inner).length) out[key] = inner;
    } else if (!same(was, value)) {
      out[key] = value;
    }
  }
  return out;
}

class AppState {
  view = $state<SettingsView | null>(null);
  draft = $state<Settings | null>(null);
  status = $state<Status | null>(null);
  providers = $state<Provider[]>([]);
  toasts = $state<Toast[]>([]);
  saving = $state(false);
  online = $state(true);
  dirty = $derived(
    this.view !== null && this.draft !== null && !same(this.view.settings, this.draft),
  );
  #nextToast = 1;

  async start(): Promise<void> {
    await Promise.all([this.loadSettings(), this.loadProviders(), this.poll()]);
    setInterval(() => void this.poll(), STATUS_POLL_MS);
  }

  async loadSettings(): Promise<void> {
    this.adopt(await api.settings());
  }

  async loadProviders(): Promise<void> {
    this.providers = await api.providers();
  }

  async poll(): Promise<void> {
    try {
      this.status = await api.status();
      this.online = true;
    } catch {
      this.online = false;
      return;
    }
    if (this.view && this.status.settings_version !== this.view.version) {
      await this.onDiskChange();
    }
  }

  async save(): Promise<void> {
    if (!this.draft || !this.view) return;
    this.saving = true;
    try {
      const diff = changes($state.snapshot(this.view.settings), $state.snapshot(this.draft));
      this.adopt(await api.saveSettings(diff));
      this.toast("success", "Saved", "Written to config.toml and live");
    } catch (e) {
      this.toast("error", "Not saved", e instanceof ApiError ? e.message : String(e));
    } finally {
      this.saving = false;
    }
  }

  reset(): void {
    if (this.view) this.draft = structuredClone($state.snapshot(this.view.settings));
  }

  async setSecret(name: string, value: string | null): Promise<void> {
    try {
      this.adopt(await api.setSecret(name, value), false);
      await this.loadProviders();
      this.toast("success", value ? "Key saved" : "Key removed", "Stored in secrets.toml (0600)");
    } catch (e) {
      this.toast("error", "Key not saved", e instanceof ApiError ? e.message : String(e));
    }
  }

  toast(kind: ToastKind, title: string, body?: string): void {
    const id = this.#nextToast++;
    this.toasts.push({ id, kind, title, body });
    setTimeout(() => (this.toasts = this.toasts.filter((t) => t.id !== id)), 4200);
  }

  dismiss(id: number): void {
    this.toasts = this.toasts.filter((t) => t.id !== id);
  }

  private adopt(view: SettingsView, replaceDraft = true): void {
    this.view = view;
    if (replaceDraft || !this.draft) this.draft = structuredClone(view.settings);
  }

  private async onDiskChange(): Promise<void> {
    const wasDirty = this.dirty;
    const fresh = await api.settings();
    this.adopt(fresh, !wasDirty);
    await this.loadProviders();
    if (fresh.error) {
      this.toast("error", "config.toml has an error", "The last good settings keep running");
    } else if (wasDirty) {
      this.toast("info", "config.toml changed on disk", "Your unsaved edits are kept; saving overwrites");
    } else {
      this.toast("info", "Reloaded", "config.toml was edited outside the UI");
    }
  }
}

export const app = new AppState();
