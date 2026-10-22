// Mirrors src/stremio_plus_plus/config/settings.py and app/admin.py.

export type TranslatorProvider = "claude-cli" | "anthropic";

export interface TranslatorSettings {
  provider: TranslatorProvider;
  model: string;
  max_calls_per_hour: number;
  timeout_s: number;
  context_cues: number;
  style: string;
}

export interface SpeechSettings {
  engine: "mlx-whisper";
  model: string;
  source_language: string;
}

export interface Settings {
  subtitles: { translator: TranslatorSettings; speech: SpeechSettings; next_episodes: number };
  stremio: { keep_addon_first: boolean };
  downloads: {
    min_free_gb: number;
    stale_after_days: number;
    next_episodes: number | "season";
  };
}

export interface SettingsView {
  settings: Settings;
  version: string;
  path: string;
  error: string | null;
  secrets: Record<string, boolean>;
}

export interface ModelOption {
  id: string;
  label: string;
  note: string;
}

export interface Provider {
  id: TranslatorProvider;
  label: string;
  description: string;
  secret: string | null;
  models: ModelOption[];
  ready: boolean;
  why: string | null;
}

export interface Torrent {
  info_hash: string;
  name: string;
  size: number;
  downloaded: number;
  speed: number;
  peers: number;
  pinned: boolean;
}

export interface SubtitleJob {
  info_hash: string;
  file_index: number;
  file_name: string;
  duration_s: number | null;
  playhead_s: number;
  covered: [number, number][]; // subtitled (start_s, end_s) ranges, merged
  failed: boolean;
  last_active: number;
}

export interface Status {
  server: { ok: boolean; url: string };
  torrents: Torrent[];
  subtitles: SubtitleJob[];
  translator: {
    provider: TranslatorProvider;
    model: string;
    calls_last_hour: number;
    cap: number;
    calls: number;
    failures: number;
    last_latency_s: number | null;
    last_error: string | null;
  };
  disk: { free: number; reserve: number };
  addon: { manifest_url: string | null; https: "own-domain" | "stremio" | null };
  settings_version: string;
}

export interface TranslatorTest {
  ok: boolean;
  error: string | null;
  seconds?: number;
  lines?: { source: string; target: string }[];
}

export type CheckLevel = "ok" | "warn" | "bad";

export interface SetupCheck {
  id:
    | "mac"
    | "tools"
    | "server"
    | "server_tv"
    | "https"
    | "translator"
    | "model"
    | "tv_connected"
    | "account"
    | "addon_installed"
    | "disk";
  label: string;
  level: CheckLevel;
  detail: string;
  // A shell command or advice, or an action id the wizard knows (configure_server, …).
  fix: string | null;
}

export interface ModelDownload {
  model: string;
  state: "idle" | "running" | "done" | "failed";
  total?: number | null;
  downloaded?: number;
  error?: string | null;
}

export interface SetupState {
  completed: boolean;
  checks: SetupCheck[];
  lan_ip: string;
  tv: { server_url: string | null; revert_url: string };
  addon_url: string | null;
  model: ModelDownload;
}

export type TvOs = "samsung" | "webos" | "androidtv" | "firetv";

export interface FoundTv {
  host: string;
  name: string;
  model: string;
  manufacturer: string;
  os: TvOs | null;
}

export interface TvState {
  target: { host: string; os: TvOs } | null;
  pinned_by_env: boolean;
  paired: boolean;
  pairing: { state: "idle" | "waiting" | "code" | "paired" | "failed"; error: string | null };
  can_drive: boolean;
  client_last_seen: number | null;
}

export type ActivityCategory = "playback" | "subtitles" | "downloads" | "system" | "problem";

export interface ActivityItem {
  id: number;
  ts: number;
  updated: number;
  category: ActivityCategory;
  kind: string;
  title: string;
  detail: string | null;
  image: string | null;
  count: number;
}

export interface LogEntry {
  seq: number;
  ts: number | null;
  source: "server" | "companion";
  level: string;
  text: string;
  event: string | null;
  fields: Record<string, unknown>;
}

export interface AccountState {
  connected: boolean;
  email: string | null;
  error: string | null;
  position: number | null; // of Stremio++ in the collection; null = not installed
  url_current: boolean;
  addons: { id: string | null; name: string; ours: boolean }[];
  keep_first: boolean;
  manifest_url: string | null;
}
