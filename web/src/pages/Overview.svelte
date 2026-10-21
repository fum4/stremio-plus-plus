<script lang="ts">
  import {
    ArrowDown,
    Captions,
    HardDrive,
    Languages,
    ListChecks,
    Pin,
    RotateCcw,
    Server,
    Sparkles,
    Users,
  } from "@lucide/svelte";
  import { flip } from "svelte/animate";
  import { fly } from "svelte/transition";
  import Badge from "../lib/components/Badge.svelte";
  import Card from "../lib/components/Card.svelte";
  import Coverage from "../lib/components/Coverage.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import Progress from "../lib/components/Progress.svelte";
  import StatCard from "../lib/components/StatCard.svelte";
  import { ago, bytes, clock, prettyName, speed } from "../lib/format";
  import { app } from "../lib/state.svelte";
  import { api } from "../lib/api";

  const s = $derived(app.status);
  const coveredS = (spans: [number, number][]) => spans.reduce((n, [a, b]) => n + b - a, 0);
  const isDone = (j: { duration_s: number | null; covered: [number, number][] }) =>
    j.duration_s !== null && coveredS(j.covered) >= j.duration_s - 1;
  const generating = $derived(s?.subtitles.filter((j) => !j.failed && !isDone(j)) ?? []);
  async function regenerate(infoHash: string, fileIndex: number, name: string) {
    if (!confirm(`Generate the subtitles for “${prettyName(name)}” again with the current settings?`)) return;
    await api.regenerate(infoHash, fileIndex);
    app.toast("success", "Regenerating", "New subtitles arrive as the film plays, playhead first");
    await app.poll();
  }

  const greeting = (() => {
    const h = new Date().getHours();
    return h < 5 ? "Late show" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  })();
</script>

<PageHeader title={greeting} subtitle="What your stremio++ host is doing right now." />

{#if app.setup && !app.setup.completed}
  <a class="setup-nudge" href="#setup" in:fly={{ y: -8, duration: 300 }}>
    <ListChecks size={16} />
    <span>Setup isn't finished yet: the TV may not be able to use this Mac.</span>
    <strong>Continue setup →</strong>
  </a>
{/if}

{#if s}
  <div class="stats">
    <StatCard
      label="Streaming server"
      icon={Server}
      value={s.torrents.length}
      format={(n) => `${Math.round(n)} active`}
      hint={s.server.ok ? s.server.url : "Not responding"}
      tone={s.server.ok ? "good" : "bad"}
    />
    <StatCard
      label="Translator calls / hour"
      icon={Languages}
      value={s.translator.calls_last_hour}
      format={(n) => `${Math.round(n)} / ${s.translator.cap}`}
      meter={s.translator.calls_last_hour / s.translator.cap}
      hint={s.translator.model}
      tone={s.translator.last_error ? "warn" : "good"}
      delay={60}
    />
    <StatCard
      label="Free disk"
      icon={HardDrive}
      value={s.disk.free}
      format={(n) => bytes(n)}
      meter={Math.min(1, s.disk.reserve / Math.max(1, s.disk.free))}
      hint="keeps {bytes(s.disk.reserve, 0)} in reserve"
      tone={s.disk.free < s.disk.reserve * 1.5 ? "warn" : "good"}
      delay={120}
    />
    <StatCard
      label="Subtitles generating"
      icon={Captions}
      value={generating.length}
      hint={s.translator.last_latency_s ? `last batch ${s.translator.last_latency_s}s` : "idle"}
      tone={generating.length ? "good" : "neutral"}
      delay={180}
    />
  </div>

  {#if s.translator.last_error}
    <div class="alert" in:fly={{ y: -8, duration: 300 }}>
      <Sparkles size={15} />
      <span>Translator: {s.translator.last_error}</span>
      <a href="#subtitles">Fix in Subtitles →</a>
    </div>
  {/if}

  <Card
    title="AI subtitles"
    subtitle="Generated just ahead of the playhead, then the rest of the film. Filled = subtitled; the caret is where the TV is."
    icon={Captions}
    delay={120}
  >
    {#if s.subtitles.length === 0}
      <div class="empty">
        <span class="bubble"><Captions size={22} /></span>
        <p>Nothing yet. Pick <strong>Romanian (AI)</strong> in the TV's subtitle menu and it starts here.</p>
      </div>
    {:else}
      <ul class="jobs">
        {#each s.subtitles as job (`${job.info_hash}:${job.file_index}`)}
          <li animate:flip={{ duration: 400 }} in:fly={{ y: 10, duration: 400 }}>
            <div class="row">
              <span class="name" title={job.file_name}>{prettyName(job.file_name)}</span>
              <button
                class="regen"
                title="Forget these subtitles and generate them again with the current settings"
                onclick={() => regenerate(job.info_hash, job.file_index, job.file_name)}
              >
                <RotateCcw size={13} /> Regenerate
              </button>
              {#if job.failed}
                <Badge tone="bad">Failed: retries when you reselect the track</Badge>
              {:else if isDone(job)}
                <Badge tone="good">Complete</Badge>
              {:else if job.duration_s === null}
                <Badge tone="accent">Preparing audio…</Badge>
              {:else}
                <Badge tone="accent"><span class="live"></span>Generating</Badge>
              {/if}
            </div>
            {#if job.duration_s}
              <Coverage
                duration={job.duration_s}
                covered={job.covered}
                playhead={job.playhead_s}
                failed={job.failed}
              />
            {/if}
            <div class="meta num">
              {#if job.duration_s}
                <span>{Math.floor((coveredS(job.covered) / job.duration_s) * 100)}% subtitled</span>
                <span>at {clock(job.playhead_s)} of {clock(job.duration_s)}</span>
              {/if}
              <span>{ago(job.last_active)}</span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </Card>

  <Card
    title="Torrents"
    subtitle="Kept downloading while the TV is paused, and the next episode is prefetched."
    icon={ArrowDown}
    delay={180}
  >
    {#if s.torrents.length === 0}
      <div class="empty">
        <span class="bubble"><ArrowDown size={22} /></span>
        <p>No active torrents. Start something on the TV.</p>
      </div>
    {:else}
      <ul class="torrents">
        {#each s.torrents as t (t.info_hash)}
          <li animate:flip={{ duration: 400 }} in:fly={{ y: 10, duration: 400 }}>
            <div class="row">
              <span class="name" title={t.name}>{prettyName(t.name)}</span>
              {#if t.pinned}<Badge tone="accent"><Pin size={11} /> Pinned</Badge>{/if}
            </div>
            <Progress value={t.size ? t.downloaded / t.size : 0} active={t.speed > 0} />
            <div class="meta num">
              <span>{bytes(t.downloaded)} of {bytes(t.size)}</span>
              <span><ArrowDown size={12} /> {speed(t.speed)}</span>
              <span><Users size={12} /> {t.peers} peers</span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </Card>
{/if}

<style>
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
  }

  .alert {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-radius: var(--radius);
    background: rgba(251, 191, 119, 0.07);
    border: 1px solid rgba(251, 191, 119, 0.22);
    color: var(--amber);
    font-size: 13px;
  }

  .alert span {
    flex: 1;
    color: var(--text);
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  li {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 16px;
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
    transition:
      border-color 0.25s,
      background 0.25s;
  }

  li:hover {
    border-color: var(--border-strong);
    background: rgba(0, 0, 0, 0.26);
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .row .name {
    flex: 1;
  }

  .regen {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    font-size: 12px;
    color: var(--text-faint);
    background: none;
    border: 1px solid transparent;
    border-radius: 999px;
    opacity: 0;
    transition:
      opacity 0.2s,
      color 0.2s,
      border-color 0.2s;
  }

  li:hover .regen,
  .regen:focus-visible {
    opacity: 1;
  }

  .regen:hover {
    color: var(--text);
    border-color: var(--border-strong);
  }

  .setup-nudge {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-radius: var(--radius);
    color: var(--amber);
    background: rgba(251, 191, 119, 0.07);
    border: 1px solid rgba(251, 191, 119, 0.22);
    font-size: 13px;
  }

  .setup-nudge span {
    flex: 1;
    color: var(--text);
  }

  .name {
    font-weight: 580;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .meta span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .live {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: blink 1.2s ease-in-out infinite;
  }

  .empty {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px;
    border-radius: var(--radius);
    border: 1px dashed var(--border-strong);
    color: var(--text-dim);
  }

  .empty p {
    margin: 0;
  }

  .bubble {
    display: grid;
    place-items: center;
    width: 46px;
    height: 46px;
    flex: none;
    border-radius: 14px;
    color: var(--violet);
    background: var(--accent-soft);
    animation: float 3.6s ease-in-out infinite;
  }

  @keyframes blink {
    50% {
      opacity: 0.25;
    }
  }

  @keyframes float {
    50% {
      transform: translateY(-4px) rotate(-3deg);
    }
  }
</style>
