<script lang="ts">
  import { AudioLines, Cpu, Languages, Sparkles } from "@lucide/svelte";
  import Card from "../lib/components/Card.svelte";
  import Collapse from "../lib/components/Collapse.svelte";
  import Field from "../lib/components/Field.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import ProviderCard from "../lib/components/ProviderCard.svelte";
  import Slider from "../lib/components/Slider.svelte";
  import { app } from "../lib/state.svelte";
  import ModelPicker from "../lib/translator/ModelPicker.svelte";
  import ProviderPicker from "../lib/translator/ProviderPicker.svelte";
  import StyleField from "../lib/translator/StyleField.svelte";
  import TryIt from "../lib/translator/TryIt.svelte";

  // Derived, not captured: a save or an outside edit replaces app.draft.
  const tr = $derived(app.draft!.subtitles.translator);
  const speech = $derived(app.draft!.subtitles.speech);

  const LANGUAGES = [
    ["en", "English"],
    ["es", "Spanish"],
    ["fr", "French"],
    ["de", "German"],
    ["it", "Italian"],
    ["pt", "Portuguese"],
    ["ja", "Japanese"],
    ["ko", "Korean"],
  ] as const;
</script>

<PageHeader title="Subtitles" subtitle="Speech → text on this machine, then translated by the model you pick." />

<Card
  title="Translator"
  subtitle="Which AI turns the English lines into Romanian. Swaps live; no restart."
  icon={Languages}
>
  <ProviderPicker />
  <div class="block"><ModelPicker /></div>
  <div class="block">
    <Collapse label="Limits and context">
      <div class="grid">
        <Field
          label="Calls per hour"
          hint="Hard cap. Protects a subscription or a budget."
          tomlKey="max_calls_per_hour"
        >
          <Slider bind:value={tr.max_calls_per_hour} min={10} max={600} step={10} />
        </Field>
        <Field label="Timeout" hint="Per call, before it's retried." tomlKey="timeout_s">
          <Slider bind:value={tr.timeout_s} min={30} max={600} step={10} unit="s" />
        </Field>
        <Field
          label="Context lines"
          hint="Earlier subtitles sent along, for consistent pronouns and tone."
          tomlKey="context_cues"
        >
          <Slider bind:value={tr.context_cues} min={0} max={60} />
        </Field>
      </div>
    </Collapse>
  </div>
</Card>

<Card
  title="Voice"
  subtitle="Tell the translator how the subtitles should sound. The timing and line rules stay fixed."
  icon={Sparkles}
  delay={60}
>
  <StyleField />
  <div class="block"><TryIt /></div>
</Card>

<Card
  title="Speech to text"
  subtitle="Runs on this machine. Turns the film's audio into timed English lines."
  icon={AudioLines}
  delay={120}
>
  <div class="providers">
    <ProviderCard
      icon={Cpu}
      label="Whisper on MLX"
      description="Apple Silicon GPU, about 30× realtime. More engines (Linux, NVIDIA) are coming."
      selected={speech.engine === "mlx-whisper"}
      onselect={() => (speech.engine = "mlx-whisper")}
    />
  </div>
  <div class="grid block">
    <Field
      label="Whisper model"
      hint="A Hugging Face repo. After changing it, run `mise run models:fetch` once."
      tomlKey="subtitles.speech.model"
    >
      <input type="text" class="mono" bind:value={speech.model} spellcheck="false" />
    </Field>
    <Field label="Spoken language" tomlKey="subtitles.speech.source_language">
      <select bind:value={speech.source_language}>
        {#each LANGUAGES as [code, name] (code)}
          <option value={code}>{name}</option>
        {/each}
      </select>
    </Field>
  </div>
</Card>

<style>
  .block {
    margin-top: 22px;
    padding-top: 22px;
    border-top: 1px solid var(--border);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 22px;
  }

  .providers {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
  }
</style>
