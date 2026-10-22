<script lang="ts">
  // The streaming server's and the companion's own log lines, live, with filters. Secrets are
  // redacted by the companion before they get here.
  import { ArrowDownToLine, Download, Pause, Play, Search } from "@lucide/svelte";
  import { onDestroy, onMount, tick } from "svelte";
  import { api } from "../../lib/api";
  import type { LogEntry } from "../../lib/types";

  const POLL_MS = 1500;
  const KEEP = 20_000;
  const SHOW = 1500;
  // Lines that are true but rarely interesting: piece checks, the server's SSDP errors, polls,
  // and stremio++'s own reads (tagged src=companion). What's left is mostly the TV.
  const NOISE = [
    /invalid piece/,
    /^SSDP error|^\s+(at |type:|error:|syscall|errno|code:|address:|port:|\}|\{)/,
    /stats\.json/,
    /src=companion/,
  ];
  // A request line without our tag came from a Stremio app: the TV.
  const fromTv = (e: LogEntry) =>
    e.source === "server" && e.text.startsWith("-> ") && !e.text.includes("src=companion");
  const LEVELS = ["debug", "info", "warning", "error"] as const;

  let entries = $state<LogEntry[]>([]);
  let cursor = 0;
  let sources = $state({ server: true, companion: true });
  let minLevel = $state<(typeof LEVELS)[number]>("info");
  let hideNoise = $state(true);
  let query = $state("");
  let follow = $state(true);
  let paused = $state(false);
  let open = $state<number | null>(null);
  let panel: HTMLDivElement | undefined = $state();
  let timer: ReturnType<typeof setInterval> | undefined;

  async function poll() {
    if (paused) return;
    const { entries: fresh, cursor: next } = await api.logs(cursor);
    cursor = next;
    if (!fresh.length) return;
    entries = [...entries, ...fresh].slice(-KEEP);
    if (follow) {
      await tick();
      panel?.scrollTo({ top: panel.scrollHeight });
    }
  }

  onMount(() => {
    void poll();
    timer = setInterval(() => void poll(), POLL_MS);
  });
  onDestroy(() => clearInterval(timer));

  const levelRank = (l: string) => Math.max(0, LEVELS.indexOf(l === "critical" ? "error" : (l as never)));
  const noisy = (e: LogEntry) => e.source === "server" && NOISE.some((r) => r.test(e.text));
  const needle = $derived(query.trim().toLowerCase());
  const filtered = $derived(
    entries.filter(
      (e) =>
        sources[e.source] &&
        levelRank(e.level) >= levelRank(minLevel) &&
        !(hideNoise && noisy(e)) &&
        (!needle || `${e.text} ${JSON.stringify(e.fields)}`.toLowerCase().includes(needle)),
    ),
  );
  const visible = $derived(filtered.slice(-SHOW));
  const counts = $derived({
    server: entries.filter((e) => e.source === "server").length,
    companion: entries.filter((e) => e.source === "companion").length,
  });

  function clockOf(ts: number | null): string {
    if (ts === null) return "--:--:--";
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString(undefined, { hour12: false }) + "." + String(d.getMilliseconds()).padStart(3, "0");
  }

  function fieldsInline(e: LogEntry): [string, string][] {
    return Object.entries(e.fields)
      .filter(([k]) => k !== "exception" && k !== "logger")
      .slice(0, 8)
      .map(([k, v]) => [k, typeof v === "string" ? v : JSON.stringify(v)]);
  }

  // Server request lines: method + path stand out, hashes and ranges dim.
  function serverParts(text: string): { cls: string; text: string }[] {
    const m = text.match(/^(-> )([A-Z]+) (\S+)(.*)$/);
    if (!m) return [{ cls: "", text }];
    return [
      { cls: "dim", text: m[1]! },
      { cls: "method", text: m[2]! + " " },
      { cls: "path", text: m[3]! },
      { cls: "dim", text: m[4]! },
    ];
  }

  function split(text: string): { hit: boolean; text: string }[] {
    if (!needle) return [{ hit: false, text }];
    const out: { hit: boolean; text: string }[] = [];
    const lower = text.toLowerCase();
    let i = 0;
    for (let j = lower.indexOf(needle); j !== -1; j = lower.indexOf(needle, i)) {
      if (j > i) out.push({ hit: false, text: text.slice(i, j) });
      out.push({ hit: true, text: text.slice(j, j + needle.length) });
      i = j + needle.length;
    }
    if (i < text.length) out.push({ hit: false, text: text.slice(i) });
    return out;
  }

  function download() {
    const lines = filtered.map((e) =>
      `${e.ts ? new Date(e.ts * 1000).toISOString() : "-"} ${e.source} ${e.level} ${e.text} ${Object.keys(e.fields).length ? JSON.stringify(e.fields) : ""}`,
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain" }));
    a.download = `stremio-plus-plus-${new Date().toISOString().slice(0, 19)}.log`;
    a.click();
  }

  function onScroll() {
    if (!panel) return;
    follow = panel.scrollHeight - panel.scrollTop - panel.clientHeight < 40;
  }
</script>

<div class="toolbar">
  <div class="group">
    <button class="toggle server" class:on={sources.server} onclick={() => (sources.server = !sources.server)}>
      Streaming server <span class="num">{counts.server}</span>
    </button>
    <button class="toggle companion" class:on={sources.companion} onclick={() => (sources.companion = !sources.companion)}>
      stremio++ <span class="num">{counts.companion}</span>
    </button>
  </div>
  <div class="group">
    <select bind:value={minLevel} aria-label="Minimum level">
      <option value="debug">All levels</option>
      <option value="info">Info and up</option>
      <option value="warning">Warnings and errors</option>
      <option value="error">Errors only</option>
    </select>
    <label class="check"><input type="checkbox" bind:checked={hideNoise} /> Hide noise</label>
    <label class="search">
      <Search size={14} />
      <input type="text" bind:value={query} placeholder="Search logs" />
    </label>
  </div>
</div>

<div class="frame">
  <div class="bar">
    <span class="live" class:paused>{paused ? "Paused" : "Live"}</span>
    <span class="num shown">{filtered.length.toLocaleString()} lines{filtered.length > SHOW ? ` · showing the last ${SHOW}` : ""}</span>
    <div class="actions">
      <button class="icon-btn" onclick={() => (paused = !paused)} title={paused ? "Resume" : "Pause"}>
        {#if paused}<Play size={14} />{:else}<Pause size={14} />{/if}
      </button>
      <button class="icon-btn" class:on={follow} onclick={() => { follow = true; panel?.scrollTo({ top: panel.scrollHeight }); }} title="Follow new lines">
        <ArrowDownToLine size={14} />
      </button>
      <button class="icon-btn" onclick={download} title="Download what's filtered">
        <Download size={14} />
      </button>
    </div>
  </div>
  <div class="panel" bind:this={panel} onscroll={onScroll}>
    {#each visible as e (e.seq)}
      <button class="line {e.source} lvl-{e.level}" class:open={open === e.seq} onclick={() => (open = open === e.seq ? null : e.seq)}>
        <span class="t">{clockOf(e.ts)}</span>
        <span class="src" class:tv={fromTv(e)}>{fromTv(e) ? "TV" : e.source === "server" ? "SRV" : "S++"}</span>
        <span class="msg">
          {#if e.source === "server"}
            {#each serverParts(e.text) as part, i (i)}<span class={part.cls}>{#each split(part.text) as s, j (j)}{#if s.hit}<mark>{s.text}</mark>{:else}{s.text}{/if}{/each}</span>{/each}
          {:else}
            <span class="event">{#each split(e.text) as s, j (j)}{#if s.hit}<mark>{s.text}</mark>{:else}{s.text}{/if}{/each}</span>
            {#each fieldsInline(e) as [k, v] (k)}<span class="kv"><span class="k">{k}=</span>{#each split(v) as s, j (j)}{#if s.hit}<mark>{s.text}</mark>{:else}{s.text}{/if}{/each}</span>{/each}
          {/if}
        </span>
      </button>
      {#if open === e.seq && (Object.keys(e.fields).length || e.text.length > 160)}
        <pre class="detail">{e.source === "server" ? e.text : JSON.stringify({ event: e.event, level: e.level, ...e.fields }, null, 2)}</pre>
      {/if}
    {:else}
      <div class="empty">No lines match.</div>
    {/each}
  </div>
</div>

<style>
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 12.5px;
    font-weight: 550;
    color: var(--text-faint);
    border-radius: 999px;
    background: transparent;
    border: 1px solid var(--border);
    transition: color 0.2s, border-color 0.2s, background 0.2s;
  }

  .toggle span {
    font-size: 11px;
    opacity: 0.7;
  }

  .toggle.on.server {
    color: #7cc4ff;
    border-color: rgba(124, 196, 255, 0.35);
    background: rgba(124, 196, 255, 0.07);
  }

  .toggle.on.companion {
    color: var(--violet);
    border-color: rgba(164, 139, 255, 0.4);
    background: var(--accent-soft);
  }

  select {
    width: auto;
    padding: 6px 10px;
    font-size: 12.5px;
  }

  .check {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    color: var(--text-dim);
    cursor: pointer;
  }

  .check input {
    accent-color: var(--violet);
  }

  .search {
    position: relative;
    display: flex;
    align-items: center;
    width: 220px;
  }

  .search :global(svg) {
    position: absolute;
    left: 11px;
    color: var(--text-faint);
  }

  .search input {
    padding: 6px 10px 6px 32px;
    font-size: 12.5px;
  }

  .frame {
    border-radius: var(--radius-lg);
    border: 1px solid var(--border);
    background: #08070c;
    overflow: hidden;
  }

  .bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-faint);
  }

  .live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: var(--green);
  }

  .live::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
    animation: blink 1.6s ease-in-out infinite;
  }

  .live.paused {
    color: var(--amber);
  }

  .live.paused::before {
    animation: none;
  }

  .actions {
    margin-left: auto;
    display: flex;
    gap: 4px;
  }

  .icon-btn {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    color: var(--text-dim);
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
  }

  .icon-btn:hover,
  .icon-btn.on {
    color: var(--text);
    border-color: var(--border-strong);
  }

  .panel {
    height: min(68vh, 760px);
    overflow-y: auto;
    padding: 6px 0;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.55;
  }

  .line {
    display: grid;
    grid-template-columns: 96px 36px 1fr;
    gap: 10px;
    width: 100%;
    padding: 1px 14px;
    text-align: left;
    font: inherit;
    color: var(--text-dim);
    background: none;
    border: none;
    border-left: 2px solid transparent;
    cursor: pointer;
  }

  .line:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .line.open {
    background: rgba(164, 139, 255, 0.06);
  }

  .t {
    color: var(--text-faint);
  }

  .src {
    font-weight: 600;
    font-size: 10.5px;
    padding-top: 1px;
  }

  .server .src {
    color: #7cc4ff;
  }

  .companion .src {
    color: var(--violet);
  }

  .src.tv {
    color: var(--peach);
  }

  .msg {
    min-width: 0;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .event {
    color: var(--text);
    font-weight: 600;
  }

  .kv {
    margin-left: 10px;
    color: var(--text-dim);
  }

  .k {
    color: var(--text-faint);
  }

  .method {
    color: #7cc4ff;
  }

  .path {
    color: var(--text);
  }

  .dim {
    color: var(--text-faint);
  }

  .lvl-warning {
    border-left-color: var(--amber);
  }

  .lvl-warning .event {
    color: var(--amber);
  }

  .lvl-error,
  .lvl-critical {
    border-left-color: var(--red);
    background: rgba(255, 125, 142, 0.05);
  }

  .lvl-error .event,
  .lvl-error .msg {
    color: var(--red);
  }

  mark {
    color: #17121f;
    background: var(--amber);
    border-radius: 2px;
  }

  .detail {
    margin: 2px 14px 8px 156px;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 11.5px;
    color: var(--text-dim);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .empty {
    padding: 40px;
    text-align: center;
    color: var(--text-faint);
    font-family: var(--font);
  }

  @keyframes blink {
    50% {
      opacity: 0.3;
    }
  }
</style>
