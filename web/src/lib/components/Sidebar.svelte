<script lang="ts" module>
  import type { Component } from "svelte";

  export interface NavItem {
    id: string;
    label: string;
    icon: Component;
    badge?: string;
  }
</script>

<script lang="ts">
  import { FileCode2 } from "@lucide/svelte";
  import { app } from "../state.svelte";

  interface Props {
    items: NavItem[];
    current: string;
  }
  let { items, current }: Props = $props();
  const index = $derived(Math.max(0, items.findIndex((i) => i.id === current)));
  const configPath = $derived(app.view?.path.replace(/^\/Users\/[^/]+/, "~") ?? "");
</script>

<aside>
  <a class="brand" href="#overview">
    <span class="mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" width="30" height="30">
        <defs>
          <linearGradient id="brand-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#a48bff" />
            <stop offset="1" stop-color="#ffad84" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="9" fill="url(#brand-g)" />
        <path
          d="M9 16h6M12 13v6M17 16h6M20 13v6"
          stroke="#120f1a"
          stroke-width="2.6"
          stroke-linecap="round"
        />
      </svg>
    </span>
    <span class="word">stremio<span class="grad-text">++</span></span>
  </a>

  <nav style:--index={index}>
    <span class="indicator" aria-hidden="true"></span>
    {#each items as item (item.id)}
      {@const Icon = item.icon}
      <a href="#{item.id}" class:active={item.id === current}>
        <Icon size={17} strokeWidth={2} />
        {item.label}
        {#if item.badge}<span class="badge">{item.badge}</span>{/if}
      </a>
    {/each}
  </nav>

  <div class="foot">
    <div class="conn" class:off={!app.online}>
      <span class="dot"></span>
      {app.online ? "Companion online" : "Companion unreachable"}
    </div>
    {#if configPath}
      <div class="file" title="Everything here lives in this file: edit it by hand or with an agent">
        <FileCode2 size={14} />
        <code>{configPath}</code>
      </div>
    {/if}
  </div>
</aside>

<style>
  aside {
    position: sticky;
    top: 0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    gap: 28px;
    padding: 24px 16px;
    border-right: 1px solid var(--border);
    background: rgba(10, 9, 15, 0.55);
    backdrop-filter: blur(20px);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 0 8px;
    color: var(--text);
  }

  .mark {
    display: grid;
    transition: transform 0.5s var(--ease-spring);
  }

  .brand:hover .mark {
    transform: rotate(-8deg) scale(1.06);
  }

  .word {
    font-size: 18px;
    font-weight: 680;
    letter-spacing: -0.03em;
  }

  nav {
    --item: 40px;
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .indicator {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: var(--item);
    border-radius: 11px;
    background: var(--surface-strong);
    border: 1px solid var(--border);
    transform: translateY(calc(var(--index) * (var(--item) + 2px)));
    transition: transform 0.45s var(--ease-spring);
  }

  .indicator::before {
    content: "";
    position: absolute;
    left: -16px;
    top: 10px;
    bottom: 10px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--violet);
  }

  nav a {
    position: relative;
    display: flex;
    align-items: center;
    gap: 11px;
    height: var(--item);
    padding: 0 12px;
    border-radius: 11px;
    color: var(--text-dim);
    font-weight: 530;
    transition: color 0.2s;
  }

  nav a:hover {
    color: var(--text);
  }

  nav a.active {
    color: var(--text);
  }

  .badge {
    margin-left: auto;
    padding: 1px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    color: var(--amber);
    background: rgba(251, 191, 119, 0.1);
  }

  nav a.active :global(svg) {
    color: var(--violet);
  }

  .foot {
    margin-top: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0 8px;
    font-size: 12px;
    color: var(--text-faint);
  }

  .conn {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
  }

  .off .dot {
    background: var(--red);
  }

  .file {
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
  }

  .file code {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @media (max-width: 860px) {
    aside {
      position: static;
      height: auto;
      flex-direction: row;
      align-items: center;
      padding: 12px 16px;
      border-right: none;
      border-bottom: 1px solid var(--border);
      overflow-x: auto;
    }
    .word,
    .foot,
    .indicator {
      display: none;
    }
    nav {
      flex-direction: row;
    }
    nav a.active {
      background: var(--surface-strong);
    }
  }
</style>
