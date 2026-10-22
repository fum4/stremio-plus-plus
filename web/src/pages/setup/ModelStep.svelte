<script lang="ts">
  import { Download, LoaderCircle } from "@lucide/svelte";
  import { onDestroy } from "svelte";
  import { api } from "../../lib/api";
  import Progress from "../../lib/components/Progress.svelte";
  import { bytes } from "../../lib/format";
  import { app } from "../../lib/state.svelte";
  import type { ModelDownload } from "../../lib/types";

  interface Props {
    done: boolean;
  }
  let { done }: Props = $props();
  let dl = $state<ModelDownload | null>(null);
  let timer: ReturnType<typeof setInterval> | undefined;
  const running = $derived(dl?.state === "running");
  const fraction = $derived(dl?.total ? Math.min(1, (dl.downloaded ?? 0) / dl.total) : 0);

  async function poll() {
    dl = await api.modelProgress();
    if (dl.state !== "running") {
      clearInterval(timer);
      timer = undefined;
      await app.loadSetup();
    }
  }

  async function start() {
    dl = await api.setupModel();
    timer ??= setInterval(() => void poll(), 1000);
  }

  $effect(() => {
    if (app.setup?.model.state === "running" && !timer) {
      dl = app.setup.model;
      timer = setInterval(() => void poll(), 1000);
    }
  });
  onDestroy(() => clearInterval(timer));
</script>

<p class="explain">
  Whisper turns the film's audio into timed lines, on this Mac's GPU. The model is
  <code>{app.draft?.subtitles.speech.model}</code>, about 1.6 GB, downloaded once.
</p>
{#if !done}
  {#if running || dl?.state === "failed"}
    <div class="progress">
      <Progress value={dl?.total ? fraction : 0.08} active={running} />
      <div class="meta num">
        {#if dl?.state === "failed"}
          <span class="error">Download failed: {dl.error}</span>
        {:else if dl?.total}
          <span>{bytes(dl.downloaded ?? 0)} of {bytes(dl.total)}</span>
          <span>{Math.round(fraction * 100)}%</span>
        {:else}
          <span>Starting…</span>
        {/if}
      </div>
    </div>
  {/if}
  {#if !running}
    <button class="btn primary" onclick={start}>
      <Download size={15} />
      {dl?.state === "failed" ? "Try again" : "Download the model"}
    </button>
  {:else}
    <p class="hint"><LoaderCircle size={14} class="spin" /> You can keep going; it finishes in the background.</p>
  {/if}
{/if}

<style>
  .explain {
    margin: 0 0 16px;
    color: var(--text-dim);
  }

  .progress {
    margin-bottom: 16px;
  }

  .meta {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .error {
    color: var(--red);
  }

  .hint {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    color: var(--text-faint);
    font-size: 13px;
  }
</style>
