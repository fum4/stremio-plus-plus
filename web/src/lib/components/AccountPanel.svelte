<script lang="ts">
  // Connect a Stremio account (email + password, or a pasted authKey for Google/Facebook
  // sign-ins), then install Stremio++ in one click and see where it sits in the addon list.
  import { Check, KeyRound, LoaderCircle, LogIn, LogOut, Mail, MoveUp, Puzzle } from "@lucide/svelte";
  import { onMount } from "svelte";
  import { fly, slide } from "svelte/transition";
  import { api, ApiError } from "../api";
  import type { AccountState } from "../types";
  import Badge from "./Badge.svelte";
  import CopyField from "./CopyField.svelte";

  interface Props {
    compact?: boolean; // the setup step: hide the full addon list
    onchange?: (state: AccountState) => void;
  }
  let { compact = false, onchange }: Props = $props();
  const SNIPPET = 'JSON.parse(localStorage.getItem("profile")).auth.key';

  let acct = $state<AccountState | null>(null);
  let mode = $state<"password" | "key">("password");
  let email = $state("");
  let password = $state("");
  let authKey = $state("");
  let busy = $state<string | null>(null);
  let error = $state<string | null>(null);

  async function run(name: string, fn: () => Promise<AccountState>) {
    busy = name;
    error = null;
    try {
      acct = await fn();
      onchange?.(acct);
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e);
    } finally {
      busy = null;
      password = ""; // secrets don't linger in the form
      authKey = "";
    }
  }

  onMount(() => void run("load", api.account));
  const ours = $derived(acct?.position ?? null);
  // Connected = a key Stremio hasn't signed out; an outage shows as an error, not a sign-out.
  const signedIn = $derived(!!acct?.connected);
</script>

{#if acct === null}
  <div class="loading"><LoaderCircle size={16} class="spin" /> Checking your Stremio account…</div>
{:else if !signedIn}
  <div in:fly={{ y: 6, duration: 250 }}>
    {#if acct.error}<p class="error">{acct.error}</p>{/if}
    <p class="lead">
      Connecting lets stremio++ install its addon for you and keep it <strong>first</strong> in
      your list, so its streams show on top. Only a login key is kept on this Mac, never your password.
    </p>
    <div class="tabs" role="tablist">
      <button role="tab" class:on={mode === "password"} onclick={() => (mode = "password")}>
        <Mail size={14} /> Email and password
      </button>
      <button role="tab" class:on={mode === "key"} onclick={() => (mode = "key")}>
        <KeyRound size={14} /> Signed in with Google or Facebook
      </button>
    </div>
    {#if mode === "password"}
      <form
        class="form"
        onsubmit={(e) => {
          e.preventDefault();
          void run("login", () => api.accountLogin(email, password));
        }}
      >
        <input type="text" bind:value={email} placeholder="Email" autocomplete="username" />
        <input type="password" bind:value={password} placeholder="Password" autocomplete="current-password" />
        <button class="btn primary" disabled={!email || !password || !!busy}>
          {#if busy === "login"}<LoaderCircle size={15} class="spin" />{:else}<LogIn size={15} />{/if} Connect
        </button>
      </form>
    {:else}
      <ol class="steps">
        <li>Open <a href="https://web.stremio.com" target="_blank" rel="noreferrer">web.stremio.com</a> and sign in.</li>
        <li>Open the browser console (<kbd>⌥⌘J</kbd> in Chrome, <kbd>⌥⌘C</kbd> in Safari) and run:</li>
      </ol>
      <CopyField value={SNIPPET} />
      <form
        class="form"
        onsubmit={(e) => {
          e.preventDefault();
          void run("key", () => api.accountKey(authKey));
        }}
      >
        <input type="password" class="mono" bind:value={authKey} placeholder="Paste the key it prints" autocomplete="off" />
        <button class="btn primary" disabled={!authKey.trim() || !!busy}>
          {#if busy === "key"}<LoaderCircle size={15} class="spin" />{:else}<KeyRound size={15} />{/if} Connect
        </button>
      </form>
    {/if}
    {#if error}<p class="error" transition:slide={{ duration: 200 }}>{error}</p>{/if}
  </div>
{:else}
  <div class="connected" in:fly={{ y: 6, duration: 250 }}>
    {#if acct.error}<p class="error">{acct.error}</p>{/if}
    <div class="who">
      <span class="avatar"><Check size={15} strokeWidth={3} /></span>
      <div>
        <strong>{acct.email ?? "Connected"}</strong>
        <span>Stremio account connected</span>
      </div>
      <button class="btn ghost small" onclick={() => run("logout", api.accountLogout)}>
        <LogOut size={14} /> Disconnect
      </button>
    </div>

    <div class="addon">
      <Puzzle size={17} />
      <div class="text">
        <strong>Stremio++</strong>
        {#if ours === null}
          <span>Not in your addons yet.</span>
        {:else if !acct.url_current}
          <span>Installed, but with an old address.</span>
        {:else}
          <span>Installed, <strong>{ours === 0 ? "first in your list" : `number ${ours + 1} in your list`}</strong>.</span>
        {/if}
      </div>
      {#if ours === null || !acct.url_current}
        <button class="btn primary small" onclick={() => run("install", api.accountInstall)} disabled={!!busy || !acct.manifest_url}>
          {#if busy === "install"}<LoaderCircle size={14} class="spin" />{/if}
          {ours === null ? "Install in one click" : "Reinstall"}
        </button>
      {:else if ours > 0}
        <button class="btn small" onclick={() => run("keep", api.accountKeep)} disabled={!!busy}>
          <MoveUp size={14} /> Move to the top
        </button>
      {:else}
        <Badge tone="good">On top</Badge>
      {/if}
    </div>
    {#if !acct.manifest_url}<p class="hint">The addon needs its HTTPS address first: finish the Streaming server step.</p>{/if}
    {#if error}<p class="error" transition:slide={{ duration: 200 }}>{error}</p>{/if}

    {#if !compact && acct.addons.length}
      <div class="list">
        <span class="label">Your addons, in the order Stremio lists their streams</span>
        <ol>
          {#each acct.addons as a, i (`${a.id}-${i}`)}
            <li class:ours={a.ours}><span class="num">{i + 1}</span> {a.name}</li>
          {/each}
        </ol>
      </div>
    {/if}
  </div>
{/if}

<style>
  .loading {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-dim);
  }

  .lead {
    margin: 0 0 14px;
    color: var(--text-dim);
  }

  .lead strong {
    color: var(--text);
  }

  .tabs {
    display: inline-flex;
    gap: 4px;
    padding: 4px;
    margin-bottom: 14px;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid var(--border);
  }

  .tabs button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 12px;
    font-size: 12.5px;
    font-weight: 550;
    color: var(--text-dim);
    background: none;
    border: none;
    border-radius: 9px;
  }

  .tabs button.on {
    color: var(--text);
    background: var(--surface-strong);
  }

  .form {
    display: flex;
    gap: 10px;
    margin-top: 12px;
  }

  .form input {
    flex: 1;
  }

  .steps {
    margin: 0 0 10px;
    padding-left: 18px;
    color: var(--text-dim);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  kbd {
    font-family: var(--mono);
    font-size: 11px;
    padding: 1px 5px;
    border-radius: 5px;
    border: 1px solid var(--border-strong);
  }

  .error {
    margin: 10px 0 0;
    color: var(--red);
    font-size: 13px;
  }

  .hint {
    margin: 8px 0 0;
    color: var(--text-faint);
    font-size: 12.5px;
  }

  .connected {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .who,
  .addon {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
  }

  .who div,
  .addon .text {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .who span,
  .addon .text span {
    font-size: 12.5px;
    color: var(--text-dim);
  }

  .avatar {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    color: #10201d;
    background: var(--green);
  }

  .addon > :global(svg) {
    color: var(--violet);
  }

  .list .label {
    font-size: 12px;
    color: var(--text-faint);
  }

  .list ol {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 6px;
  }

  .list li {
    display: flex;
    gap: 8px;
    padding: 6px 10px;
    font-size: 13px;
    color: var(--text-dim);
    border-radius: 8px;
    border: 1px solid var(--border);
  }

  .list li .num {
    color: var(--text-faint);
    min-width: 16px;
  }

  .list li.ours {
    color: var(--violet);
    border-color: rgba(164, 139, 255, 0.45);
    background: var(--accent-soft);
  }
</style>
