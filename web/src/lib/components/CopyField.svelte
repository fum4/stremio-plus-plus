<script lang="ts">
  import { Check, Copy } from "@lucide/svelte";
  import { scale } from "svelte/transition";

  interface Props {
    value: string;
    secret?: boolean; // blur until hovered/focused
  }
  let { value, secret = false }: Props = $props();
  let copied = $state(false);

  async function copy() {
    await navigator.clipboard.writeText(value);
    copied = true;
    setTimeout(() => (copied = false), 1600);
  }
</script>

<div class="copy" class:secret>
  <code title={value}>{value}</code>
  <button class="btn small" onclick={copy} aria-label="Copy">
    {#key copied}
      <span class="ico" in:scale={{ duration: 260, start: 0.4 }}>
        {#if copied}<Check size={14} />{:else}<Copy size={14} />{/if}
      </span>
    {/key}
    {copied ? "Copied" : "Copy"}
  </button>
</div>

<style>
  .copy {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 6px 6px 14px;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border-strong);
  }

  code {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-dim);
    transition: filter 0.3s;
  }

  .secret code {
    filter: blur(5px);
  }

  .secret:hover code,
  .secret:focus-within code {
    filter: none;
  }

  .ico {
    display: grid;
  }
</style>
