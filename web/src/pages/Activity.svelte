<script lang="ts">
  import { Activity as ActivityIcon, ScrollText } from "@lucide/svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import RawLogs from "./activity/RawLogs.svelte";
  import Timeline from "./activity/Timeline.svelte";

  const TABS = [
    { id: "timeline", label: "Activity", icon: ActivityIcon },
    { id: "raw", label: "Raw logs", icon: ScrollText },
  ] as const;
  let tab = $state<"timeline" | "raw">(location.hash.endsWith("/raw") ? "raw" : "timeline");
</script>

<PageHeader
  title="Activity"
  subtitle="What the TV and this Mac have been doing, in plain words, or line by line."
>
  <div class="tabs" role="tablist">
    {#each TABS as t (t.id)}
      {@const Icon = t.icon}
      <button role="tab" aria-selected={tab === t.id} class:on={tab === t.id} onclick={() => (tab = t.id)}>
        <Icon size={15} /> {t.label}
      </button>
    {/each}
  </div>
</PageHeader>

<section>
  {#if tab === "timeline"}<Timeline />{:else}<RawLogs />{/if}
</section>

<style>
  .tabs {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--border);
  }

  .tabs button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 550;
    color: var(--text-dim);
    background: transparent;
    border: none;
    border-radius: 999px;
    transition: color 0.2s, background 0.2s;
  }

  .tabs button.on {
    color: var(--text);
    background: var(--surface-strong);
  }
</style>
