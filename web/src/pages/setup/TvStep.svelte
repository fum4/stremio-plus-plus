<script lang="ts">
  import { Keyboard, Undo2 } from "@lucide/svelte";
  import CopyField from "../../lib/components/CopyField.svelte";
  import { app } from "../../lib/state.svelte";

  const url = $derived(app.setup?.tv.server_url ?? null);
</script>

<ol>
  <li>
    <span class="n">1</span>
    <div>
      On the TV, open <strong>Stremio → Settings → Streaming → Server URL</strong> and note what it
      says now (usually <code>{app.setup?.tv.revert_url}</code>).
    </div>
  </li>
  <li>
    <span class="n">2</span>
    <div>
      Replace it with this Mac's server, then go back: it should say <strong>online</strong>.
      {#if url}
        <div class="url"><CopyField value={url} /></div>
      {:else}
        <p class="pending">Shown here once the Streaming server step is done.</p>
      {/if}
    </div>
  </li>
</ol>
<p class="tip">
  <Keyboard size={14} />
  <span>
    Typing a long URL with a remote is slow. If this Mac controls your TV (<code>TV_HOST</code> in
    <code>.env.local</code>), select the field so the keyboard opens and run
    <code>mise run tv -- text '&lt;url&gt;'</code>.
  </span>
</p>
<p class="revert">
  <Undo2 size={14} />
  <span>
    To undo at any time, set it back to <code>{app.setup?.tv.revert_url}</code>: the TV then plays
    everything on its own again, without this Mac.
  </span>
</p>

<style>
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  li {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    color: var(--text-dim);
  }

  li strong {
    color: var(--text);
  }

  .n {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    flex: none;
    margin-top: 1px;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 700;
    color: var(--violet);
    background: var(--accent-soft);
  }

  li > div {
    flex: 1;
    min-width: 0;
  }

  .url {
    margin-top: 10px;
  }

  .pending {
    margin: 8px 0 0;
    color: var(--text-faint);
  }

  .tip,
  .revert {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 18px 0 0;
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .tip :global(svg),
  .revert :global(svg) {
    flex: none;
    margin-top: 2px;
  }

  .tip + .revert {
    margin-top: 8px;
  }
</style>
