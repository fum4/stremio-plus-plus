<script lang="ts">
  import { LoaderCircle } from "@lucide/svelte";
  import { fly } from "svelte/transition";
  import { backOut } from "svelte/easing";
  import { app } from "../state.svelte";
</script>

<svelte:window
  onkeydown={(e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s" && app.dirty) {
      e.preventDefault();
      void app.save();
    }
  }}
/>

{#if app.dirty}
  <div class="bar" transition:fly={{ y: 80, duration: 480, easing: backOut }}>
    <span class="pulse" aria-hidden="true"></span>
    <span class="msg">Unsaved changes</span>
    <kbd>⌘S</kbd>
    <button class="btn ghost small" onclick={() => app.reset()} disabled={app.saving}>Discard</button>
    <button class="btn primary small" onclick={() => app.save()} disabled={app.saving}>
      {#if app.saving}<LoaderCircle size={14} class="spin" />{/if}
      Save to config.toml
    </button>
  </div>
{/if}

<style>
  .bar {
    position: fixed;
    left: 50%;
    bottom: 24px;
    z-index: 40;
    translate: -50% 0;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 8px 8px 18px;
    border-radius: 999px;
    background: rgba(24, 21, 34, 0.9);
    border: 1px solid var(--border-strong);
    backdrop-filter: blur(20px);
    box-shadow:
      0 20px 50px -18px rgba(0, 0, 0, 0.9),
      0 0 0 1px rgba(164, 139, 255, 0.12);
  }

  .pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--amber);
    animation: breathe 1.6s ease-in-out infinite;
  }

  .msg {
    font-weight: 560;
    font-size: 13px;
  }

  kbd {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-faint);
    padding: 2px 6px;
    border-radius: 6px;
    border: 1px solid var(--border-strong);
    margin-right: 4px;
  }

  .bar :global(.spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes breathe {
    50% {
      transform: scale(0.6);
      opacity: 0.5;
    }
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
