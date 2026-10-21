// Mirrors src/stremio_plus_plus/config/settings.py and app/admin.py.

export type TranslatorProvider = "claude-cli" | "anthropic";

export interface TranslatorSettings {
  provider: TranslatorProvider;
  model: string;
  max_calls_per_hour: number;
  timeout_s: number;
  context_cues: number;
}

export interface SpeechSettings {
  engine: "mlx-whisper";
  model: string;
  source_language: string;
}

export interface Settings {
  subtitles: { translator: TranslatorSettings; speech: SpeechSettings };
  downloads: { min_free_gb: number; stale_after_days: number };
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
  addon: { manifest_url: string };
  settings_version: string;
}

export interface TranslatorTest {
  ok: boolean;
  error: string | null;
  seconds?: number;
  lines?: { source: string; target: string }[];
}
