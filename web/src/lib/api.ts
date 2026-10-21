import type {
  Provider,
  Settings,
  SettingsView,
  Status,
  TranslatorSettings,
  TranslatorTest,
  ModelDownload,
  SetupState,
  FoundTv,
  TvOs,
  TvState,
  ActivityItem,
  LogEntry,
} from "./types";

export class ApiError extends Error {}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    method,
    // Required by the companion on every call (blocks cross-site requests from LAN browsers).
    headers: { "X-Stremio-Plus-Plus": "1", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!resp.ok) {
    const detail = await resp.json().then((j: { detail?: unknown }) => j.detail).catch(() => null);
    throw new ApiError(typeof detail === "string" ? detail : `${resp.status} ${resp.statusText}`);
  }
  return (await resp.json()) as T;
}

export const api = {
  settings: () => call<SettingsView>("GET", "/settings"),
  saveSettings: (values: DeepPartial<Settings>) => call<SettingsView>("PUT", "/settings", values),
  setSecret: (name: string, value: string | null) =>
    call<SettingsView>("PUT", `/secrets/${name}`, { value }),
  providers: () => call<Provider[]>("GET", "/providers"),
  status: () => call<Status>("GET", "/status"),
  testTranslator: (settings: TranslatorSettings) =>
    call<TranslatorTest>("POST", "/translator/test", settings),
  regenerate: (infoHash: string, fileIndex: number) =>
    call<{ ok: boolean }>("POST", `/subtitles/${infoHash}/${fileIndex}/regenerate`),
  setup: () => call<SetupState>("GET", "/setup"),
  setupServer: () => call<SetupState>("POST", "/setup/server"),
  setupModel: () => call<ModelDownload>("POST", "/setup/model"),
  modelProgress: () => call<ModelDownload>("GET", "/setup/model"),
  completeSetup: () => call<SetupState>("POST", "/setup/complete"),
  logs: (after: number) => call<{ entries: LogEntry[]; cursor: number }>("GET", `/logs?after=${after}`),
  activity: (since: number) => call<{ items: ActivityItem[] }>("GET", `/activity?since=${since}`),
  activityBefore: (id: number) =>
    call<{ items: ActivityItem[] }>("GET", `/activity?before=${id}&limit=100`),
  tv: () => call<TvState>("GET", "/tv"),
  discoverTvs: () => call<FoundTv[]>("POST", "/tv/discover"),
  chooseTv: (host: string, os: TvOs) => call<TvState>("PUT", "/tv", { host, os }),
  pairTv: () => call<TvState>("POST", "/tv/pair"),
  tvCode: (code: string) => call<TvState>("POST", "/tv/pair/code", { code }),
  typeOnTv: (which: "server" | "revert") => call<{ ok: boolean }>("POST", "/tv/type", { which }),
  applyOnTv: (which: "server" | "revert") => call<{ ok: boolean }>("POST", "/tv/apply", { which }),
};
