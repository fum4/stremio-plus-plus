<script lang="ts">
  // The activity feed: what the TV and this Mac did, newest first, grouped by day.
  import {
    CircleAlert,
    Captions,
    Download,
    Play,
    Search,
    Settings2,
  } from "@lucide/svelte";
  import type { Component } from "svelte";
  import { onDestroy, onMount } from "svelte";
  import { flip } from "svelte/animate";
  import { fly } from "svelte/transition";
  import { api } from "../../lib/api";
  import type { ActivityCategory, ActivityItem } from "../../lib/types";

  const POLL_MS = 2000;
  const CATS: { id: ActivityCategory | "all"; label: string }[] = [
    { id: "all", label: "Everything" },
    { id: "playback", label: "Playback" },
    { id: "subtitles", label: "Subtitles" },
    { id: "downloads", label: "Downloads" },
    { id: "system", label: "System" },
    { id: "problem", label: "Problems" },
  ];
  const ICON: Record<ActivityCategory, Component> = {
    playback: Play,
    subtitles: Captions,
    downloads: Download,
    system: Settings2,
    problem: CircleAlert,
  };

  let items = $state<ActivityItem[]>([]);
  let cat = $state<ActivityCategory | "all">("all");
  let query = $state("");
  let since = 0;
  let loadingMore = $state(false);
  let exhausted = $state(false);
  let timer: ReturnType<typeof setInterval> | undefined;

  async function poll() {
    const { items: changed } = await api.activity(since);
    if (!changed.length) return;
    since = Math.max(since, ...changed.map((i) => i.updated));
    const byId = new Map(items.map((i) => [i.id, i]));
    for (const c of changed) byId.set(c.id, c);
    items = [...byId.values()].sort((a, b) => b.updated - a.updated);
  }

  async function more() {
    const oldest = Math.min(...items.map((i) => i.id));
    loadingMore = true;
    const { items: older } = await api.activityBefore(oldest);
    loadingMore = false;
    if (older.length < 100) exhausted = true;
    const ids = new Set(items.map((i) => i.id));
    items = [...items, ...older.filter((o) => !ids.has(o.id))];
  }

  onMount(() => {
    void poll();
    timer = setInterval(() => void poll(), POLL_MS);
  });
  onDestroy(() => clearInterval(timer));

  const problems = $derived(items.filter((i) => i.category === "problem").length);
  const shown = $derived(
    items.filter(
      (i) =>
        (cat === "all" || i.category === cat) &&
        (!query || `${i.title} ${i.detail ?? ""}`.toLowerCase().includes(query.toLowerCase())),
    ),
  );

  function day(ts: number): string {
    const d = new Date(ts * 1000);
    const today = new Date();
    const yesterday = new Date(Date.now() - 86400_000);
    if (d.toDateString() === today.toDateString()) return "Today";
    if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
    return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
  }
  const time = (ts: number) =>
    new Date(ts * 1000).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
  const groups = $derived.by(() => {
    const out: { day: string; items: ActivityItem[] }[] = [];
    for (const item of shown) {
      const d = day(item.updated);
      if (out.at(-1)?.day !== d) out.push({ day: d, items: [] });
      out.at(-1)!.items.push(item);
    }
    return out;
  });
</script>

<div class="toolbar">
  <div class="chips" role="tablist">
    {#each CATS as c (c.id)}
      <button class="chip {c.id}" class:on={cat === c.id} onclick={() => (cat = c.id)}>
        {c.label}
        {#if c.id === "problem" && problems}<span class="count">{problems}</span>{/if}
      </button>
    {/each}
  </div>
  <label class="search">
    <Search size={14} />
    <input type="text" bind:value={query} placeholder="Search activity" />
  </label>
</div>

{#if !groups.length}
  <div class="empty">
    {items.length ? "Nothing matches these filters." : "Nothing yet. Play something on the TV and watch it appear here."}
  </div>
{/if}

{#each groups as g (g.day)}
  <h3 class="day">{g.day}</h3>
  <ol class="timeline">
    {#each g.items as item (item.id)}
      {@const Icon = ICON[item.category]}
      <li class={item.category} animate:flip={{ duration: 300 }} in:fly={{ y: -10, duration: 350 }}>
        <time datetime={new Date(item.updated * 1000).toISOString()}>{time(item.updated)}</time>
        <span class="node"><Icon size={13} strokeWidth={2.2} /></span>
        <div class="card">
          <div class="text">
            <strong>{item.title}</strong>
            {#if item.detail}<span>{item.detail}</span>{/if}
          </div>
          {#if item.count > 1}<span class="times num">×{item.count}</span>{/if}
          {#if item.image}<img src={item.image} alt="" loading="lazy" />{/if}
        </div>
      </li>
    {/each}
  </ol>
{/each}

{#if items.length >= 100 && !exhausted}
  <button class="btn ghost more" onclick={more} disabled={loadingMore}>
    {loadingMore ? "Loading…" : "Show older"}
  </button>
{/if}

<style>
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    font-size: 12.5px;
    font-weight: 540;
    color: var(--text-dim);
    border-radius: 999px;
    background: transparent;
    border: 1px solid var(--border);
    transition: color 0.2s, background 0.2s, border-color 0.2s;
  }

  .chip:hover {
    color: var(--text);
  }

  .chip.on {
    color: var(--text);
    background: var(--surface-strong);
    border-color: var(--border-strong);
  }

  .count {
    padding: 0 6px;
    border-radius: 999px;
    font-size: 11px;
    color: #2a0d12;
    background: var(--red);
  }

  .search {
    position: relative;
    display: flex;
    align-items: center;
    width: 240px;
  }

  .search :global(svg) {
    position: absolute;
    left: 11px;
    color: var(--text-faint);
  }

  .search input {
    padding-left: 32px;
  }

  .day {
    margin: 22px 0 10px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .timeline {
    list-style: none;
    margin: 0;
    padding: 0;
    position: relative;
  }

  .timeline::before {
    content: "";
    position: absolute;
    left: 63px;
    top: 6px;
    bottom: 6px;
    width: 1px;
    background: var(--border-strong);
  }

  li {
    position: relative;
    display: grid;
    grid-template-columns: 48px 32px 1fr;
    align-items: start;
    gap: 0;
    padding: 4px 0;
  }

  time {
    padding-top: 12px;
    font-size: 12px;
    color: var(--text-faint);
    font-variant-numeric: tabular-nums;
  }

  .node {
    z-index: 1;
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    margin-top: 9px;
    margin-left: 4px;
    border-radius: 50%;
    color: var(--c);
    background: var(--bg);
    border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  }

  .playback {
    --c: var(--violet);
  }
  .subtitles {
    --c: var(--green);
  }
  .downloads {
    --c: #7cc4ff;
  }
  .system {
    --c: var(--text-dim);
  }
  .problem {
    --c: var(--red);
  }

  .card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
    transition: border-color 0.2s;
  }

  li:hover .card {
    border-color: var(--border-strong);
  }

  .problem .card {
    border-color: rgba(255, 125, 142, 0.22);
    background: rgba(255, 125, 142, 0.04);
  }

  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .text strong {
    font-weight: 570;
  }

  .text span {
    font-size: 12.5px;
    color: var(--text-dim);
    overflow-wrap: anywhere;
  }

  .times {
    font-size: 12px;
    color: var(--text-faint);
    padding: 1px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
  }

  img {
    height: 46px;
    max-width: 82px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid var(--border);
  }

  .empty {
    padding: 40px 0;
    text-align: center;
    color: var(--text-faint);
  }

  .more {
    margin: 16px auto 0;
    display: flex;
  }
</style>
