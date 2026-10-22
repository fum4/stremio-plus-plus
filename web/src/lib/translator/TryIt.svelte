<script lang="ts">
  // Translate four sample lines with the current (possibly unsaved) translator settings.
  import { Play, Timer } from "@lucide/svelte";
  import { fly, slide } from "svelte/transition";
  import { api, ApiError } from "../api";
  import Badge from "../components/Badge.svelte";
  import { app } from "../state.svelte";
  import type { TranslatorTest } from "../types";

  interface Props {
    onresult?: (result: TranslatorTest) => void;
  }
  let { onresult }: Props = $props();
  const tr = $derived(app.draft!.subtitles.translator);
  let testing = $state(false);
  let result = $state<TranslatorTest | null>(null);

  async function run() {
    testing = true;
    result = null;
    try {
      result = await api.testTranslator($state.snapshot(tr));
    } catch (e) {
      result = { ok: false, error: e instanceof ApiError ? e.message : String(e) };
    } finally {
      testing = false;
    }
    onresult?.(result);
  }
</script>

<div class="head">
  <div>
    <strong>Try it</strong>
    <span>Four sample lines through the settings above, saved or not.</span>
  </div>
  <button class="btn" onclick={run} disabled={testing}>
    <Play size={14} />
    {testing ? "Translating…" : "Run a test"}
  </button>
</div>
{#if testing}
  <div class="lines" transition:slide={{ duration: 250 }}>
    {#each { length: 4 }, i (i)}
      <div class="skeleton" style:animation-delay="{i * 120}ms"></div>
    {/each}
  </div>
{:else if result}
  <div class="lines" transition:slide={{ duration: 300 }}>
    {#each result.lines ?? [] as line, i (i)}
      <div class="line" in:fly={{ x: -12, duration: 420, delay: i * 110 }}>
        <span class="src">{line.source}</span>
        <span class="arrow">→</span>
        <span class="dst">{line.target}</span>
      </div>
    {/each}
    <div class="verdict">
      {#if result.ok}<Badge tone="good">Works</Badge>{:else}<Badge tone="bad">{result.error}</Badge>{/if}
      {#if result.seconds}<Badge><Timer size={11} /> {result.seconds}s</Badge>{/if}
    </div>
  </div>
{/if}

<style>
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .head div {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .head span {
    color: var(--text-faint);
    font-size: 12.5px;
  }

  .lines {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
  }

  .line {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 14px;
    align-items: center;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid var(--border);
  }

  .src {
    color: var(--text-dim);
  }

  .arrow {
    color: var(--text-faint);
  }

  .dst {
    font-weight: 560;
  }

  .verdict {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .skeleton {
    height: 40px;
    border-radius: var(--radius-sm);
    background:
      linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent) 0 0 / 200% 100%,
      rgba(0, 0, 0, 0.2);
    animation: sweep 1.3s ease-in-out infinite;
  }

  @keyframes sweep {
    from {
      background-position: 150% 0;
    }
    to {
      background-position: -50% 0;
    }
  }
</style>
