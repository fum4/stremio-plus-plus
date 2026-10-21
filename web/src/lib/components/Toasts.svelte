<script lang="ts">
  import { CircleAlert, CircleCheck, Info, X } from "@lucide/svelte";
  import { flip } from "svelte/animate";
  import { fly } from "svelte/transition";
  import { app } from "../state.svelte";

  const icons = { success: CircleCheck, info: Info, error: CircleAlert };
</script>

<div class="toasts" aria-live="polite">
  {#each app.toasts as toast (toast.id)}
    {@const Icon = icons[toast.kind]}
    <div
      class="toast {toast.kind}"
      animate:flip={{ duration: 300 }}
      in:fly={{ x: 40, duration: 420, opacity: 0 }}
      out:fly={{ x: 40, duration: 260 }}
    >
      <span class="icon"><Icon size={17} /></span>
      <div class="text">
        <strong>{toast.title}</strong>
        {#if toast.body}<span>{toast.body}</span>{/if}
      </div>
      <button class="close" onclick={() => app.dismiss(toast.id)} aria-label="Dismiss">
        <X size={14} />
      </button>
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    top: 18px;
    right: 18px;
    z-index: 50;
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: min(360px, calc(100vw - 36px));
  }

  .toast {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 13px 14px;
    border-radius: var(--radius);
    background: rgba(24, 21, 34, 0.86);
    border: 1px solid var(--border-strong);
    backdrop-filter: blur(20px);
    box-shadow: 0 18px 40px -16px rgba(0, 0, 0, 0.8);
  }

  .icon {
    display: grid;
    margin-top: 1px;
  }
  .success .icon {
    color: var(--green);
  }
  .info .icon {
    color: var(--violet);
  }
  .error .icon {
    color: var(--red);
  }

  .text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 13px;
  }

  .text span {
    color: var(--text-dim);
  }

  .close {
    display: grid;
    padding: 2px;
    color: var(--text-faint);
    background: none;
    border: none;
    border-radius: 6px;
  }

  .close:hover {
    color: var(--text);
  }
</style>
