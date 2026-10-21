<script lang="ts">
  import type { Component } from "svelte";
  import { Check } from "@lucide/svelte";
  import { scale } from "svelte/transition";
  import { backOut } from "svelte/easing";

  interface Props {
    icon: Component;
    label: string;
    description: string;
    selected: boolean;
    status?: { ok: boolean; text: string } | null;
    onselect: () => void;
  }
  let { icon: Icon, label, description, selected, status = null, onselect }: Props = $props();
</script>

<button class="option" class:selected onclick={onselect} role="radio" aria-checked={selected}>
  <span class="icon"><Icon size={19} strokeWidth={1.9} /></span>
  <span class="text">
    <strong>{label}</strong>
    <span class="desc">{description}</span>
    {#if status}
      <span class="status" class:ok={status.ok}><span class="dot"></span>{status.text}</span>
    {/if}
  </span>
  {#if selected}
    <span class="check" in:scale={{ duration: 380, start: 0.3, easing: backOut }}>
      <Check size={13} strokeWidth={3} />
    </span>
  {/if}
</button>

<style>
  .option {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px;
    text-align: left;
    color: var(--text);
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
    transition:
      transform 0.25s var(--ease-out),
      border-color 0.25s,
      background 0.25s,
      box-shadow 0.3s;
  }

  .option:hover {
    transform: translateY(-2px);
    border-color: var(--border-strong);
    background: rgba(255, 255, 255, 0.03);
  }

  .option:active {
    transform: scale(0.985);
  }

  .selected {
    border-color: rgba(164, 139, 255, 0.55);
    background: rgba(164, 139, 255, 0.06);
  }

  .icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    flex: none;
    border-radius: 12px;
    color: var(--text-dim);
    background: var(--surface-strong);
    transition:
      color 0.3s,
      background 0.3s;
  }

  .selected .icon {
    color: var(--violet);
    background: var(--accent-soft);
  }

  .text {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
    padding-right: 18px;
  }

  .desc {
    color: var(--text-dim);
    font-size: 12.5px;
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 12px;
    color: var(--amber);
  }

  .status.ok {
    color: var(--green);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  .check {
    position: absolute;
    top: 12px;
    right: 12px;
    display: grid;
    place-items: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    color: #17121f;
    background: var(--violet);
  }
</style>
