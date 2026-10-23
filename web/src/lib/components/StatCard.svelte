<script lang="ts">
  import type { Component } from "svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";

  interface Props {
    label: string;
    icon: Component;
    value: number;
    format?: (n: number) => string;
    hint?: string;
    tone?: "good" | "warn" | "bad" | "neutral";
    meter?: number | null; // 0..1, draws a thin gauge under the value
    delay?: number;
  }
  let {
    label,
    icon: Icon,
    value,
    format = (n) => Math.round(n).toString(),
    hint,
    tone = "neutral",
    meter = null,
    delay = 0,
  }: Props = $props();

  const shown = new Tween(0, { duration: 900, easing: cubicOut });
  const gauge = new Tween(0, { duration: 900, easing: cubicOut });
  $effect(() => {
    shown.target = value;
  });
  $effect(() => {
    gauge.target = meter ?? 0;
  });
</script>

<div class="stat {tone}" style:animation-delay="{delay}ms">
  <div class="top">
    <span class="icon"><Icon size={15} strokeWidth={2.1} /></span>
    <span class="label">{label}</span>
    <span class="dot" aria-hidden="true"></span>
  </div>
  <div class="value num">{format(shown.current)}</div>
  {#if meter !== null}
    <div class="meter"><span style:width="{Math.min(1, gauge.current) * 100}%"></span></div>
  {/if}
  {#if hint}<div class="hint">{hint}</div>{/if}
</div>

<style>
  .stat {
    position: relative;
    overflow: hidden;
    padding: 18px 18px 16px;
    border-radius: var(--radius-lg);
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    animation: rise 0.6s var(--ease-out) both;
    transition:
      transform 0.3s var(--ease-out),
      border-color 0.3s;
  }

  .stat:hover {
    transform: translateY(-2px);
    border-color: var(--border-strong);
  }

  .top {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-dim);
    font-size: 12.5px;
    font-weight: 520;
  }

  .icon {
    display: grid;
    color: var(--violet);
  }

  .label {
    flex: 1;
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-faint);
  }

  .good .dot {
    background: var(--green);
    box-shadow: 0 0 0 0 rgba(94, 234, 212, 0.6);
    animation: pulse 2.4s infinite;
  }
  .warn .dot {
    background: var(--amber);
  }
  .bad .dot {
    background: var(--red);
    animation: pulse-red 1.6s infinite;
  }

  .value {
    margin-top: 10px;
    font-size: 28px;
    font-weight: 640;
    letter-spacing: -0.03em;
    line-height: 1.1;
  }

  .meter {
    height: 4px;
    margin-top: 12px;
    border-radius: 99px;
    background: rgba(255, 255, 255, 0.07);
    overflow: hidden;
  }

  .meter span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--violet);
  }

  .hint {
    margin-top: 8px;
    font-size: 12.5px;
    color: var(--text-faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(12px);
    }
  }

  @keyframes pulse {
    70% {
      box-shadow: 0 0 0 7px rgba(94, 234, 212, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(94, 234, 212, 0);
    }
  }

  @keyframes pulse-red {
    50% {
      opacity: 0.35;
    }
  }
</style>
