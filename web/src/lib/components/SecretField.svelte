<script lang="ts">
  import { KeyRound, LockKeyhole } from "@lucide/svelte";
  import { fade } from "svelte/transition";
  import { app } from "../state.svelte";

  interface Props {
    name: string;
    placeholder: string;
  }
  let { name, placeholder }: Props = $props();
  const isSet = $derived(app.view?.secrets[name] ?? false);
  let editing = $state(false);
  let value = $state("");

  async function save() {
    await app.setSecret(name, value);
    value = "";
    editing = false;
  }
</script>

{#if isSet && !editing}
  <div class="saved" in:fade={{ duration: 200 }}>
    <LockKeyhole size={15} />
    <span class="dots">••••••••••••••••</span>
    <span class="where">saved in secrets.toml</span>
    <button class="btn ghost small" onclick={() => (editing = true)}>Replace</button>
    <button class="btn ghost small" onclick={() => app.setSecret(name, null)}>Remove</button>
  </div>
{:else}
  <form
    class="entry"
    in:fade={{ duration: 200 }}
    onsubmit={(e) => {
      e.preventDefault();
      void save();
    }}
  >
    <span class="ico"><KeyRound size={15} /></span>
    <input type="password" class="mono" bind:value {placeholder} autocomplete="off" />
    <button class="btn primary small" disabled={!value.trim()}>Save key</button>
    {#if isSet}
      <button type="button" class="btn ghost small" onclick={() => (editing = false)}>Cancel</button>
    {/if}
  </form>
{/if}

<style>
  .saved,
  .entry {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .saved {
    padding: 6px 6px 6px 14px;
    border-radius: var(--radius-sm);
    background: rgba(94, 234, 212, 0.05);
    border: 1px solid rgba(94, 234, 212, 0.2);
    color: var(--green);
  }

  .dots {
    letter-spacing: 1px;
    color: var(--text-dim);
  }

  .where {
    flex: 1;
    font-size: 12px;
    color: var(--text-faint);
  }

  .entry {
    position: relative;
  }

  .ico {
    position: absolute;
    left: 12px;
    display: grid;
    color: var(--text-faint);
    pointer-events: none;
  }

  .entry input {
    padding-left: 36px;
  }
</style>
