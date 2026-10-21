<script lang="ts">
  import { onMount } from "svelte";
  import { fade, fly } from "svelte/transition";
  import { CircleAlert, Gauge, HardDriveDownload, Link2, ListChecks, Subtitles } from "@lucide/svelte";
  import Sidebar, { type NavItem } from "./lib/components/Sidebar.svelte";
  import SaveBar from "./lib/components/SaveBar.svelte";
  import Toasts from "./lib/components/Toasts.svelte";
  import { app } from "./lib/state.svelte";
  import Overview from "./pages/Overview.svelte";
  import SubtitlesPage from "./pages/Subtitles.svelte";
  import Downloads from "./pages/Downloads.svelte";
  import Install from "./pages/Install.svelte";
  import Setup from "./pages/Setup.svelte";

  const pages = {
    overview: { label: "Overview", icon: Gauge, component: Overview },
    subtitles: { label: "Subtitles", icon: Subtitles, component: SubtitlesPage },
    downloads: { label: "Downloads", icon: HardDriveDownload, component: Downloads },
    install: { label: "Install", icon: Link2, component: Install },
    setup: { label: "Setup", icon: ListChecks, component: Setup },
  } as const;
  type PageId = keyof typeof pages;
  const nav: NavItem[] = $derived(
    Object.entries(pages).map(([id, p]) => ({
      id,
      label: p.label,
      icon: p.icon,
      badge: id === "setup" && app.setup && !app.setup.completed ? "to do" : undefined,
    })),
  );

  const fromHash = (): PageId => {
    const id = location.hash.slice(1);
    return id in pages ? (id as PageId) : "overview";
  };
  let page = $state<PageId>(fromHash());
  let failed = $state<string | null>(null);
  const Page = $derived(pages[page].component);

  onMount(() => {
    app
      .start()
      .then(() => {
        // First run: open the setup instead of an empty dashboard.
        if (app.setup && !app.setup.completed && !location.hash) location.hash = "#setup";
      })
      .catch((e: unknown) => (failed = String(e)));
  });
</script>

<svelte:window onhashchange={() => (page = fromHash())} />

<div class="aurora" aria-hidden="true"><span></span><span></span></div>

<div class="shell">
  <Sidebar items={nav} current={page} />
  <main>
    {#if app.view?.error}
      <div class="banner" transition:fly={{ y: -12, duration: 300 }}>
        <CircleAlert size={16} />
        <div>
          <strong>config.toml has an error, so the last good settings are still running.</strong>
          <code>{app.view.error}</code>
        </div>
      </div>
    {/if}
    {#if failed}
      <div class="banner">
        <CircleAlert size={16} />
        <div><strong>Can't reach the companion.</strong> <code>{failed}</code></div>
      </div>
    {:else if app.view && app.draft}
      {#key page}
        <div class="page" in:fly={{ y: 14, duration: 420, delay: 80 }} out:fade={{ duration: 80 }}>
          <Page />
        </div>
      {/key}
    {:else}
      <div class="loading"><span></span><span></span><span></span></div>
    {/if}
  </main>
</div>

<SaveBar />
<Toasts />

<style>
  .shell {
    position: relative;
    display: grid;
    grid-template-columns: 248px 1fr;
    min-height: 100vh;
  }

  main {
    min-width: 0;
    padding: 36px clamp(20px, 4vw, 56px) 120px;
    max-width: 1180px;
  }

  .page {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .aurora {
    position: fixed;
    inset: 0;
    z-index: -1;
    overflow: hidden;
    pointer-events: none;
  }

  .aurora span {
    position: absolute;
    width: 620px;
    height: 620px;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.09;
    animation: drift 26s ease-in-out infinite alternate;
  }

  .aurora span:first-child {
    top: -260px;
    right: -120px;
    background: #6d4dff;
  }

  .aurora span:last-child {
    bottom: -320px;
    left: 18%;
    background: #ff8a5c;
    opacity: 0.04;
    animation-duration: 34s;
    animation-delay: -10s;
  }

  .banner {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 20px;
    padding: 14px 16px;
    border-radius: var(--radius);
    color: var(--red);
    background: rgba(255, 125, 142, 0.08);
    border: 1px solid rgba(255, 125, 142, 0.25);
  }

  .banner div {
    display: flex;
    flex-direction: column;
    gap: 4px;
    color: var(--text);
  }

  .banner code {
    color: var(--text-dim);
    white-space: pre-wrap;
  }

  .loading {
    display: flex;
    gap: 8px;
    justify-content: center;
    padding: 120px 0;
  }

  .loading span {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--violet);
    animation: bounce 1s ease-in-out infinite;
  }

  .loading span:nth-child(2) {
    animation-delay: 0.15s;
  }
  .loading span:nth-child(3) {
    animation-delay: 0.3s;
    background: var(--peach);
  }

  @keyframes bounce {
    50% {
      transform: translateY(-10px);
      opacity: 0.5;
    }
  }

  @keyframes drift {
    to {
      transform: translate(-120px, 80px) scale(1.15);
    }
  }

  @media (max-width: 860px) {
    .shell {
      grid-template-columns: 1fr;
    }
  }
</style>
