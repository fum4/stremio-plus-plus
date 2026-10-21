<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    label: string;
    hint?: string;
    tomlKey?: string; // shown so a hand/agent edit can find the same knob in config.toml
    children: Snippet;
  }
  let { label, hint, tomlKey, children }: Props = $props();
</script>

<div class="field">
  <div class="head">
    <span class="label">{label}</span>
    {#if tomlKey}<code class="key" title="Key in config.toml">{tomlKey}</code>{/if}
  </div>
  {@render children()}
  {#if hint}<p class="hint">{hint}</p>{/if}
</div>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }

  .label {
    font-weight: 560;
    font-size: 13px;
  }

  .key {
    color: var(--text-faint);
    font-size: 11px;
    opacity: 0;
    transform: translateX(-4px);
    transition:
      opacity 0.2s,
      transform 0.2s var(--ease-out);
  }

  .field:hover .key,
  .field:focus-within .key {
    opacity: 1;
    transform: none;
  }

  .hint {
    margin: 0;
    font-size: 12.5px;
    color: var(--text-faint);
  }
</style>
