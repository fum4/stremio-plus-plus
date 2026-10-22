<script lang="ts">
  // Suggested models of the chosen provider as chips, or any model id.
  import Field from "../components/Field.svelte";
  import { app } from "../state.svelte";

  const tr = $derived(app.draft!.subtitles.translator);
  const provider = $derived(app.providers.find((p) => p.id === tr.provider));
  const known = $derived(provider?.models.some((m) => m.id === tr.model) ?? false);
</script>

<Field label="Model" tomlKey="subtitles.translator.model">
  <div class="models" role="radiogroup">
    {#each provider?.models ?? [] as m (m.id)}
      <button
        class="model"
        class:on={tr.model === m.id}
        role="radio"
        aria-checked={tr.model === m.id}
        onclick={() => (tr.model = m.id)}
      >
        <strong>{m.label}</strong>
        <span>{m.note}</span>
      </button>
    {/each}
  </div>
  <div class="custom" class:on={!known}>
    <span>or any model id</span>
    <input type="text" class="mono" bind:value={tr.model} spellcheck="false" />
  </div>
</Field>

<style>
  .models {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 10px;
  }

  .model {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 12px 14px;
    text-align: left;
    color: var(--text);
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
    transition:
      transform 0.25s var(--ease-spring),
      border-color 0.25s,
      background 0.25s;
  }

  .model:hover {
    border-color: var(--border-strong);
  }

  .model:active {
    transform: scale(0.97);
  }

  .model span {
    font-size: 12px;
    color: var(--text-faint);
  }

  .model.on {
    border-color: rgba(164, 139, 255, 0.55);
    background: var(--accent-soft);
  }

  .model.on strong {
    color: var(--violet);
  }

  .custom {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 4px;
    color: var(--text-faint);
    font-size: 12.5px;
    white-space: nowrap;
  }

  .custom.on input {
    border-color: rgba(164, 139, 255, 0.55);
  }
</style>
