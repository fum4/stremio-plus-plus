<script lang="ts">
  // Find the TV, pair with it, and let this Mac enter Stremio's server URL on it. Every part has
  // a manual fallback: TVs we can't control still get the URL to copy and the steps to follow.
  import {
    Check,
    Keyboard,
    LoaderCircle,
    Radar,
    Tv,
    Undo2,
    Wand,
  } from "@lucide/svelte";
  import { onDestroy, onMount } from "svelte";
  import { fly, slide } from "svelte/transition";
  import { api, ApiError } from "../../lib/api";
  import Badge from "../../lib/components/Badge.svelte";
  import CopyField from "../../lib/components/CopyField.svelte";
  import { app } from "../../lib/state.svelte";
  import type { FoundTv, TvOs, TvState } from "../../lib/types";

  const OS_LABEL: Record<TvOs, string> = {
    samsung: "Samsung (Tizen)",
    webos: "LG (webOS)",
    androidtv: "Android TV / Google TV",
    firetv: "Fire TV",
  };
  const POLL_MS = 1500;

  let tv = $state<TvState | null>(null);
  let found = $state<FoundTv[] | null>(null);
  let searching = $state(false);
  let changing = $state(false);
  let busy = $state<string | null>(null);
  let message = $state<{ ok: boolean; text: string } | null>(null);
  let code = $state("");
  let timer: ReturnType<typeof setInterval> | undefined;

  const url = $derived(app.setup?.tv.server_url ?? null);
  const revert = $derived(app.setup?.tv.revert_url ?? "http://127.0.0.1:11470");
  const connected = $derived(app.setup?.checks.find((c) => c.id === "tv_connected")?.level === "ok");
  const chosen = $derived(found?.find((f) => f.host === tv?.target?.host));
  const controllable = $derived(!!tv?.target && tv.paired);

  async function refresh() {
    tv = await api.tv();
  }

  onMount(() => {
    void refresh();
    timer = setInterval(() => void refresh(), POLL_MS);
  });
  onDestroy(() => clearInterval(timer));

  async function act(name: string, fn: () => Promise<unknown>, ok?: string) {
    busy = name;
    message = null;
    try {
      await fn();
      if (ok) message = { ok: true, text: ok };
    } catch (e) {
      message = { ok: false, text: e instanceof ApiError ? e.message : String(e) };
    } finally {
      busy = null;
      await refresh();
    }
  }

  async function search() {
    searching = true;
    found = await api.discoverTvs().catch(() => []);
    searching = false;
  }

  async function choose(f: FoundTv) {
    if (!f.os) return;
    await act("choose", () => api.chooseTv(f.host, f.os!));
    changing = false;
  }
</script>

<div class="sections">
  <!-- 1. Which TV -->
  <section>
    <h3><span class="n" class:done={!!tv?.target}>{#if tv?.target}<Check size={12} strokeWidth={3} />{:else}1{/if}</span> Your TV</h3>
    {#if tv?.target && !changing}
      <div class="tv-card" in:fly={{ y: 6, duration: 250 }}>
        <Tv size={18} />
        <div>
          <strong>{chosen?.name ?? `TV at ${tv.target.host}`}</strong>
          <span>{OS_LABEL[tv.target.os]} · {tv.target.host}</span>
        </div>
        {#if !tv.pinned_by_env}
          <button class="btn ghost small" onclick={() => { changing = true; void search(); }}>Change</button>
        {/if}
      </div>
    {:else}
      <p class="hint">Find the TV on your network, so this Mac can type on it for you.</p>
      <button class="btn" onclick={search} disabled={searching}>
        {#if searching}<LoaderCircle size={15} class="spin" /> Looking…{:else}<Radar size={15} /> Find my TV{/if}
      </button>
      {#if found && !searching}
        <div class="found" transition:slide={{ duration: 250 }}>
          {#each found as f, i (f.host)}
            <button
              class="tv-card pick"
              disabled={!f.os}
              onclick={() => choose(f)}
              in:fly={{ y: 6, duration: 250, delay: i * 60 }}
            >
              <Tv size={18} />
              <div>
                <strong>{f.name}</strong>
                <span>{f.manufacturer} {f.model} · {f.host}</span>
              </div>
              {#if f.os}<Badge tone="accent">{OS_LABEL[f.os]}</Badge>{:else}<Badge>can't be controlled</Badge>{/if}
            </button>
          {:else}
            <p class="hint">No TV answered. Is it on and on the same network? You can still do the steps below by hand.</p>
          {/each}
        </div>
      {/if}
    {/if}
  </section>

  <!-- 2. Pair -->
  {#if tv?.target}
    <section transition:slide={{ duration: 250 }}>
      <h3><span class="n" class:done={tv.paired}>{#if tv.paired}<Check size={12} strokeWidth={3} />{:else}2{/if}</span> Connect to it</h3>
      {#if tv.paired}
        <p class="hint">Paired: this Mac can press buttons and type on the TV.</p>
      {:else if tv.pairing.state === "waiting"}
        <div class="waiting"><span class="pulse"><Tv size={18} /></span> Look at the TV and choose <strong>Allow</strong>.</div>
      {:else if tv.pairing.state === "code"}
        <form class="code" onsubmit={(e) => { e.preventDefault(); void act("code", () => api.tvCode(code)); }}>
          <span>Type the code the TV shows:</span>
          <input type="text" class="mono" bind:value={code} maxlength="8" autocomplete="off" />
          <button class="btn primary small" disabled={!code.trim()}>Pair</button>
        </form>
      {:else}
        {#if tv.pairing.state === "failed"}<p class="error">{tv.pairing.error}</p>{/if}
        <button class="btn" onclick={() => act("pair", api.pairTv)}>
          <Tv size={15} /> {tv.pairing.state === "failed" ? "Try again" : "Connect to the TV"}
        </button>
      {/if}
    </section>
  {/if}

  <!-- 3. Server URL -->
  <section>
    <h3><span class="n" class:done={connected}>{#if connected}<Check size={12} strokeWidth={3} />{:else}{tv?.target ? 3 : 2}{/if}</span> Point Stremio at this Mac</h3>
    {#if !url}
      <p class="hint">Finish the Streaming server step first.</p>
    {:else}
      {#if controllable && tv?.can_drive}
        <button class="btn primary" onclick={() => act("apply", () => api.applyOnTv("server"), "Done on the TV")} disabled={!!busy}>
          {#if busy === "apply"}<LoaderCircle size={15} class="spin" />{:else}<Wand size={15} />{/if} Set it up on my TV
        </button>
      {/if}
      <ol class="manual">
        <li>On the TV, open <strong>Stremio → Settings → Streaming → Server URL</strong> and select the field so the keyboard opens.</li>
        <li>
          {#if controllable}
            Then
            <button class="btn small" onclick={() => act("type", () => api.typeOnTv("server"), "Typed on the TV: confirm it there")} disabled={!!busy}>
              {#if busy === "type"}<LoaderCircle size={14} class="spin" />{:else}<Keyboard size={14} />{/if} Type it for me
            </button>
            and confirm on the TV. Or type it yourself:
          {:else}
            Replace what's there with this, and confirm:
          {/if}
          <div class="url"><CopyField value={url} /></div>
        </li>
      </ol>
      {#if message}<p class={message.ok ? "ok" : "error"} transition:slide={{ duration: 200 }}>{message.text}</p>{/if}
      <div class="status" class:connected>
        {#if connected}
          <Check size={15} /> The TV is using this Mac's server.
        {:else}
          <span class="dot"></span> Waiting for the TV to connect… (it shows <em>online</em> once it does)
        {/if}
      </div>
    {/if}
  </section>

  <!-- Undo -->
  <section class="undo">
    <Undo2 size={14} />
    <span>
      To undo, set the server URL back to <code>{revert}</code>: the TV then plays everything on its own again.
      {#if controllable}
        <button class="link" onclick={() => act("revert", () => api.typeOnTv("revert"), "Typed the original URL: confirm it on the TV")}>Type it for me</button>
      {/if}
    </span>
  </section>
</div>

<style>
  .sections {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    margin-bottom: 10px;
  }

  .n {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 700;
    color: var(--violet);
    background: var(--accent-soft);
    transition: background 0.3s, color 0.3s;
  }

  .n.done {
    color: #10201d;
    background: var(--green);
  }

  .hint {
    margin: 0 0 12px;
    color: var(--text-dim);
  }

  .tv-card {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 14px;
    text-align: left;
    color: var(--text);
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
  }

  .tv-card div {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .tv-card span {
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .tv-card :global(svg) {
    color: var(--violet);
    flex: none;
  }

  .pick {
    transition: border-color 0.2s, transform 0.2s var(--ease-out);
  }

  .pick:not(:disabled):hover {
    border-color: rgba(164, 139, 255, 0.55);
    transform: translateY(-1px);
  }

  .pick:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .found {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
  }

  .waiting {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--text-dim);
  }

  .waiting strong {
    color: var(--text);
  }

  .pulse {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    color: var(--violet);
    background: var(--accent-soft);
    animation: breathe 1.4s ease-in-out infinite;
  }

  .code {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .code input {
    width: 130px;
    letter-spacing: 0.15em;
  }

  .manual {
    margin: 14px 0 0;
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    color: var(--text-dim);
  }

  .manual strong {
    color: var(--text);
  }

  .url {
    margin-top: 10px;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 14px;
    padding: 10px 14px;
    border-radius: var(--radius);
    font-size: 13px;
    color: var(--text-dim);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
    transition: border-color 0.3s, color 0.3s;
  }

  .status.connected {
    color: var(--green);
    border-color: rgba(94, 234, 212, 0.25);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--amber);
    animation: breathe 1.4s ease-in-out infinite;
  }

  .ok {
    margin: 10px 0 0;
    color: var(--green);
    font-size: 13px;
  }

  .error {
    margin: 10px 0;
    color: var(--red);
    font-size: 13px;
  }

  .undo {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .undo :global(svg) {
    flex: none;
    margin-top: 2px;
  }

  .link {
    padding: 0;
    color: var(--violet);
    background: none;
    border: none;
    font: inherit;
  }

  @keyframes breathe {
    50% {
      opacity: 0.45;
      transform: scale(0.92);
    }
  }
</style>
