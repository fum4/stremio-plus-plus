<script lang="ts">
  import { ChevronDown } from "@lucide/svelte";
  import type { Snippet } from "svelte";
  import { slide } from "svelte/transition";

  interface Props {
    label: string;
    children: Snippet;
  }
  let { label, children }: Props = $props();
  let open = $state(false);
</script>

<div class="collapse">
  <button class="toggle" class:open onclick={() => (open = !open)} aria-expanded={open}>
    <ChevronDown size={15} />
    {label}
  </button>
  {#if open}
    <div class="body" transition:slide={{ duration: 320 }}>{@render children()}</div>
  {/if}
</div>

<style>
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
    color: var(--text-dim);
    background: none;
    border: none;
    font-weight: 540;
    font-size: 13px;
    transition: color 0.2s;
  }

  .toggle:hover {
    color: var(--text);
  }

  .toggle :global(svg) {
    transition: transform 0.3s var(--ease-spring);
  }

  .open :global(svg) {
    transform: rotate(180deg);
  }

  .body {
    padding-top: 14px;
  }
</style>
