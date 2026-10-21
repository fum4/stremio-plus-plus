// `npm run dev:mock`: a fake companion for UI work without a host. Chunks tick along so the
// animations have something to show; settings round-trip in memory.
import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

const GB = 1024 ** 3;
const t0 = Date.now() / 1000;

let settings = {
  subtitles: {
    translator: {
      provider: "claude-cli",
      model: "claude-haiku-5-5",
      max_calls_per_hour: 120,
      timeout_s: 180,
      context_cues: 15,
      style: "",
    },
    speech: {
      engine: "mlx-whisper",
      model: "mlx-community/whisper-large-v3-turbo",
      source_language: "en",
    },
  },
  downloads: { min_free_gb: 3, stale_after_days: 7 },
};
let version = 1;
const secrets: Record<string, boolean> = { anthropic_api_key: false };

const models = [
  { id: "claude-haiku-5-5", label: "Claude Haiku 5.5", note: "Fast and cheap; the default" },
  { id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", note: "More natural phrasing, slower" },
  { id: "claude-opus-5-5", label: "Claude Opus 5.5", note: "Best quality, priciest" },
];

// TV control: nothing chosen at first; pairing asks for Allow, typing "connects" the TV.
const tvState = {
  target: null as null | { host: string; os: string },
  pairedAt: 0,
  pairStart: 0,
  connectedAt: 0,
};
const FOUND = [
  { host: "192.168.1.134", name: "[TV] Samsung 7 Series (43)", model: "UE43TU7092UXXH", manufacturer: "Samsung Electronics", os: "samsung" },
  { host: "192.168.1.135", name: "Living Room", model: "Eureka Dongle", manufacturer: "Google", os: null },
];

function tvView() {
  const now = Date.now();
  const paired = tvState.pairedAt > 0 && now >= tvState.pairedAt;
  return {
    target: tvState.target,
    pinned_by_env: false,
    paired,
    pairing: {
      state: paired ? "paired" : tvState.pairStart ? "waiting" : "idle",
      error: null,
    },
    can_drive: false,
    client_last_seen: tvState.connectedAt && now >= tvState.connectedAt ? tvState.connectedAt / 1000 : null,
  };
}

// Setup flow: the server isn't set up for the TV and the model isn't downloaded, at first.
const setupState = { serverReady: false, completed: false, modelStart: 0 };
const MODEL_TOTAL = 1.62 * GB;

function modelView() {
  if (!setupState.modelStart) return { model: settings.subtitles.speech.model, state: "idle" };
  const downloaded = Math.min(MODEL_TOTAL, ((Date.now() - setupState.modelStart) / 9000) * MODEL_TOTAL);
  return {
    model: settings.subtitles.speech.model,
    state: downloaded >= MODEL_TOTAL ? "done" : "running",
    total: MODEL_TOTAL,
    downloaded,
    error: null,
  };
}

function setupView() {
  const s = setupState;
  const translatorReady =
    settings.subtitles.translator.provider === "claude-cli" || secrets.anthropic_api_key;
  const modelDone = modelView().state === "done";
  return {
    completed: s.completed,
    lan_ip: "192.168.1.132",
    checks: [
      { id: "mac", label: "Apple Silicon Mac", level: "ok", detail: "Darwin arm64", fix: null },
      { id: "tools", label: "Audio tools", level: "ok", detail: "ffmpeg and ffprobe found", fix: null },
      { id: "server", label: "Streaming server", level: "ok", detail: "http://127.0.0.1:11470", fix: null },
      { id: "disk", label: "Free disk space", level: "ok", detail: "212 GB free", fix: null },
      {
        id: "server_tv",
        label: "Server reachable by the TV",
        level: s.serverReady ? "ok" : "warn",
        detail: s.serverReady ? "HTTPS for 192.168.1.132" : "not set up for the TV yet",
        fix: s.serverReady ? null : "configure_server",
      },
      {
        id: "https",
        label: "Addon over HTTPS",
        level: s.serverReady ? "ok" : "warn",
        detail: s.serverReady
          ? "192-168-1-132.519b6502d940.stremio.rocks (stremio)"
          : "waiting for a certificate",
        fix: s.serverReady ? null : "configure_server",
      },
      {
        id: "translator",
        label: "Translator",
        level: translatorReady ? "ok" : "warn",
        detail: translatorReady ? "ready" : "add an API key",
        fix: translatorReady ? null : "subtitles",
      },
      {
        id: "tv_connected",
        label: "TV connected",
        level: tvView().client_last_seen ? "ok" : "warn",
        detail: tvView().client_last_seen ? "a Stremio app is using this server" : "waiting for the TV",
        fix: null,
      },
      {
        id: "model",
        label: "Speech model",
        level: modelDone ? "ok" : "warn",
        detail: modelDone ? settings.subtitles.speech.model : "not downloaded yet",
        fix: modelDone ? null : "download_model",
      },
    ],
    tv: {
      server_url: s.serverReady ? "https://192-168-1-132.519b6502d940.stremio.rocks:12470" : null,
      revert_url: "http://127.0.0.1:11470",
    },
    addon_url: s.serverReady
      ? "https://192-168-1-132.519b6502d940.stremio.rocks:8443/0f3c9b1e7d2a4c58b6e1f09a/manifest.json"
      : null,
    model: modelView(),
  };
}

const view = () => ({
  settings,
  version: String(version),
  path: "/Users/you/.config/stremio-plus-plus/config.toml",
  error: null,
  secrets,
});

function status() {
  const el = Date.now() / 1000 - t0;
  // Coverage grows ahead of the playhead, like the real scheduler.
  const ahead = Math.min(3270, 1150 + 60 * (el / 3 + 1));
  return {
    server: { ok: true, url: "http://127.0.0.1:11470" },
    torrents: [
      {
        info_hash: "ab".repeat(20),
        name: "MobLand.S01E03.1080p.WEB.H264-SuccessfulCrab.mkv",
        size: 3.3 * GB,
        downloaded: Math.min(3.3 * GB, 1.2 * GB + el * 9e6),
        speed: 9.1e6 + Math.sin(el) * 1.5e6,
        peers: 41,
        pinned: true,
      },
      {
        info_hash: "cd".repeat(20),
        name: "Dune.Part.Two.2024.2160p.WEB-DL.mkv",
        size: 18.4 * GB,
        downloaded: 18.4 * GB,
        speed: 0,
        peers: 3,
        pinned: false,
      },
    ],
    subtitles: [
      {
        info_hash: "ab".repeat(20),
        file_index: 2,
        file_name: "MobLand.S01E03.1080p.WEB.H264-SuccessfulCrab.mkv",
        duration_s: 3270,
        playhead_s: 1140 + el,
        covered: [
          [0, 240],
          [1150, ahead],
        ],
        failed: false,
        last_active: Date.now() / 1000 - 4,
      },
      {
        info_hash: "cd".repeat(20),
        file_index: 0,
        file_name: "Dune.Part.Two.2024.2160p.WEB-DL.mkv",
        duration_s: 9960,
        playhead_s: 9960,
        covered: [[0, 9960]],
        failed: false,
        last_active: Date.now() / 1000 - 7200,
      },
    ],
    translator: {
      provider: settings.subtitles.translator.provider,
      model: settings.subtitles.translator.model,
      calls_last_hour: 14 + Math.floor(el / 6),
      cap: settings.subtitles.translator.max_calls_per_hour,
      calls: 212,
      failures: 0,
      last_latency_s: 6.8,
      last_error: null,
    },
    disk: { free: 212 * GB, reserve: settings.downloads.min_free_gb * GB },
    addon: {
      manifest_url: setupState.serverReady
        ? "https://192-168-1-132.519b6502d940.stremio.rocks:8443/0f3c9b1e7d2a4c58b6e1f09a/manifest.json"
        : null,
      https: setupState.serverReady ? "stremio" : null,
    },
    settings_version: String(version),
  };
}

const SAMPLE = [
  ["Where the hell have you been?", "Unde naiba ai fost?"],
  ["I told you, I was at my sister's.", "Ți-am zis, am fost la sora mea."],
  ["Don't lie to me. Not tonight.", "Nu mă minți. Nu în seara asta."],
  ["We need to leave. Now.", "Trebuie să plecăm. Acum."],
];

async function body(req: IncomingMessage): Promise<unknown> {
  let raw = "";
  for await (const chunk of req) raw += String(chunk);
  return raw ? JSON.parse(raw) : {};
}

function merge(base: Record<string, unknown>, patch: Record<string, unknown>): void {
  for (const [k, v] of Object.entries(patch)) {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      merge(base[k] as Record<string, unknown>, v as Record<string, unknown>);
    } else base[k] = v;
  }
}

function send(res: ServerResponse, data: unknown, code = 200): void {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

export function mockApi(): Plugin {
  return {
    name: "stremio-plus-plus-mock-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url ?? "";
        if (!url.startsWith("/api/")) return next();
        const path = url.slice(4).split("?")[0];
        if (req.method === "GET" && path === "/settings") return send(res, view());
        if (req.method === "GET" && path === "/status") return send(res, status());
        if (req.method === "GET" && path === "/setup") return send(res, setupView());
        if (req.method === "POST" && path === "/setup/server") {
          await new Promise((r) => setTimeout(r, 1200));
          setupState.serverReady = true;
          return send(res, setupView());
        }
        if (req.method === "POST" && path === "/setup/model") {
          setupState.modelStart ||= Date.now();
          return send(res, modelView());
        }
        if (req.method === "GET" && path === "/setup/model") return send(res, modelView());
        if (req.method === "POST" && path === "/setup/complete") {
          setupState.completed = true;
          return send(res, setupView());
        }
        if (req.method === "POST" && path?.endsWith("/regenerate")) return send(res, { ok: true });
        if (req.method === "GET" && path === "/tv") return send(res, tvView());
        if (req.method === "POST" && path === "/tv/discover") {
          await new Promise((r) => setTimeout(r, 2500));
          return send(res, FOUND);
        }
        if (req.method === "PUT" && path === "/tv") {
          const { host, os } = (await body(req)) as { host: string; os: string };
          tvState.target = { host, os };
          return send(res, tvView());
        }
        if (req.method === "POST" && path === "/tv/pair") {
          tvState.pairStart = Date.now();
          tvState.pairedAt = Date.now() + 4000;
          return send(res, tvView());
        }
        if (req.method === "POST" && path === "/tv/type") {
          const { which } = (await body(req)) as { which: string };
          if (which === "server") tvState.connectedAt = Date.now() + 3000;
          return send(res, { ok: true });
        }
        if (req.method === "POST" && path === "/tv/apply") {
          return send(res, { detail: "no recorded key sequence for this TV yet: use Type it for me" }, 502);
        }
        if (req.method === "GET" && path === "/providers") {
          return send(res, [
            {
              id: "claude-cli",
              label: "Claude subscription",
              description:
                "Uses the claude CLI logged in on this machine. Personal use of your own plan.",
              secret: null,
              models,
              ready: true,
              why: null,
            },
            {
              id: "anthropic",
              label: "Anthropic API",
              description: "Pay-as-you-go with your own API key from console.anthropic.com.",
              secret: "anthropic_api_key",
              models,
              ready: secrets.anthropic_api_key,
              why: secrets.anthropic_api_key ? null : "add an API key",
            },
          ]);
        }
        if (req.method === "PUT" && path === "/settings") {
          merge(settings as unknown as Record<string, unknown>, (await body(req)) as never);
          settings = structuredClone(settings);
          version++;
          return send(res, view());
        }
        if (req.method === "PUT" && path?.startsWith("/secrets/")) {
          const { value } = (await body(req)) as { value: string | null };
          secrets[path.slice(9)] = Boolean(value);
          version++;
          return send(res, view());
        }
        if (req.method === "POST" && path === "/translator/test") {
          const s = (await body(req)) as { provider: string };
          await new Promise((r) => setTimeout(r, 1400));
          if (s.provider === "anthropic" && !secrets.anthropic_api_key) {
            return send(res, { ok: false, error: "no Anthropic API key set" });
          }
          return send(res, {
            ok: true,
            error: null,
            seconds: 4.2,
            lines: SAMPLE.map(([source, target]) => ({ source, target })),
          });
        }
        send(res, { detail: "not found" }, 404);
      });
    },
  };
}
