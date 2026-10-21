<script lang="ts">
  import { LoaderCircle, Wand } from "@lucide/svelte";
  import { api, ApiError } from "../../lib/api";
  import { app } from "../../lib/state.svelte";

  interface Props {
    done: boolean;
  }
  let { done }: Props = $props();
  let busy = $state(false);
  let error = $state<string | null>(null);

  async function configure() {
    busy = true;
    error = null;
    try {
      app.setup = await api.setupServer();
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e);
    } finally {
      busy = false;
    }
  }
</script>

<p class="explain">
  The Stremio app on a TV only talks to a server over HTTPS. This sets your streaming server up
  for this Mac's address (<code>{app.setup?.lan_ip}</code>) and fetches the certificate Stremio
  provides for it. The addon reuses the same certificate, so you don't need a domain.
</p>
{#if !done}
  <button class="btn primary" onclick={configure} disabled={busy}>
    {#if busy}<LoaderCircle size={15} class="spin" />{:else}<Wand size={15} />{/if}
    {busy ? "Setting up…" : "Set up the server"}
  </button>
{/if}
{#if error}<p class="error">{error}</p>{/if}

<style>
  .explain {
    margin: 0 0 16px;
    color: var(--text-dim);
  }

  .error {
    color: var(--red);
    font-size: 13px;
  }

  :global(.spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
