<script lang="ts">
  // Free-form style for the translation, with a few starting points.
  import Field from "../components/Field.svelte";
  import { app } from "../state.svelte";

  const tr = $derived(app.draft!.subtitles.translator);
  const PRESETS = [
    ["Natural", ""],
    ["Formal", "Formal and polite: use the formal address (dumneavoastră), no slang."],
    ["Cowboy", "Talk like a laconic Wild West cowboy: drawl, frontier slang, short sentences."],
    ["Shakespeare", "Render every line in an Elizabethan, Shakespearean register."],
    ["Pirate", "Talk like a pirate: salty, theatrical, full of nautical slang."],
    ["Gen Z", "Casual Gen Z texting voice: current slang, playful, lowercase energy."],
  ] as const;
  const MAX = 2000;
</script>

<Field
  label="Style"
  hint="Applies to subtitles generated from now on. Use Regenerate on the Overview to redo a film."
  tomlKey="subtitles.translator.style"
>
  <div class="presets">
    {#each PRESETS as [name, text] (name)}
      <button class="chip" class:on={tr.style === text} onclick={() => (tr.style = text)}>
        {name}
      </button>
    {/each}
  </div>
  <div class="area">
    <textarea
      bind:value={tr.style}
      maxlength={MAX}
      rows="3"
      placeholder="Anything you like: “like a noir detective”, “keep it PG”, “explain jokes in brackets”…"
    ></textarea>
    <span class="count num">{tr.style.length}/{MAX}</span>
  </div>
</Field>

<style>
  .presets {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    padding: 5px 12px;
    font-size: 12.5px;
    font-weight: 540;
    color: var(--text-dim);
    border-radius: 999px;
    background: var(--surface-strong);
    border: 1px solid var(--border);
    transition:
      color 0.2s,
      border-color 0.2s,
      background 0.2s,
      transform 0.2s var(--ease-spring);
  }

  .chip:hover {
    color: var(--text);
    border-color: var(--border-strong);
  }

  .chip:active {
    transform: scale(0.95);
  }

  .chip.on {
    color: var(--violet);
    border-color: rgba(164, 139, 255, 0.55);
    background: var(--accent-soft);
  }

  .area {
    position: relative;
  }

  textarea {
    width: 100%;
    resize: vertical;
    min-height: 76px;
    font: inherit;
    color: var(--text);
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    padding: 10px 12px 22px;
    outline: none;
    transition:
      border-color 0.2s,
      box-shadow 0.2s;
  }

  textarea:focus {
    border-color: var(--violet);
    box-shadow: 0 0 0 4px rgba(164, 139, 255, 0.16);
  }

  .count {
    position: absolute;
    right: 12px;
    bottom: 8px;
    font-size: 11px;
    color: var(--text-faint);
  }
</style>
