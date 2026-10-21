<script lang="ts">
  import type { Component, Snippet } from "svelte";

  interface Props {
    title?: string;
    subtitle?: string;
    icon?: Component;
    actions?: Snippet;
    children: Snippet;
    delay?: number;
  }
  let { title, subtitle, icon: Icon, actions, children, delay = 0 }: Props = $props();
</script>

<section class="card" style:animation-delay="{delay}ms">
  {#if title}
    <header>
      {#if Icon}
        <span class="icon"><Icon size={16} strokeWidth={2} /></span>
      {/if}
      <div class="titles">
        <h2>{title}</h2>
        {#if subtitle}<p>{subtitle}</p>{/if}
      </div>
      {#if actions}<div class="actions">{@render actions()}</div>{/if}
    </header>
  {/if}
  {@render children()}
</section>

<style>
  .card {
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 22px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(18px);
    animation: rise 0.55s var(--ease-out) both;
  }

  header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 18px;
  }

  .icon {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    flex: none;
    border-radius: 9px;
    color: var(--violet);
    background: var(--accent-soft);
  }

  .titles {
    flex: 1;
    min-width: 0;
  }

  h2 {
    font-size: 15px;
    line-height: 30px;
  }

  p {
    margin: -4px 0 0;
    color: var(--text-dim);
    font-size: 13px;
  }

  .actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.99);
    }
  }
</style>
