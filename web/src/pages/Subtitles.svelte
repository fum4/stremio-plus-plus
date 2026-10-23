<script lang="ts">
  import { AudioLines, Cpu, KeyRound, Languages, Play, Terminal, Timer } from "@lucide/svelte";
  import { fly, slide } from "svelte/transition";
  import { api, ApiError } from "../lib/api";
  import Badge from "../lib/components/Badge.svelte";
  import Card from "../lib/components/Card.svelte";
  import Collapse from "../lib/components/Collapse.svelte";
  import Field from "../lib/components/Field.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import ProviderCard from "../lib/components/ProviderCard.svelte";
  import SecretField from "../lib/components/SecretField.svelte";
  import Slider from "../lib/components/Slider.svelte";
  import { app } from "../lib/state.svelte";
  import type { TranslatorTest } from "../lib/types";

  // Derived, not captured: a save or an outside edit replaces app.draft.
  const tr = $derived(app.draft!.subtitles.translator);
  const speech = $derived(app.draft!.subtitles.speech);
  const icons = { "claude-cli": Terminal, anthropic: KeyRound } as const;
  const provider = $derived(app.providers.find((p) => p.id === tr.provider));
  const known = $derived(provider?.models.some((m) => m.id === tr.model) ?? false);

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

  let testing = $state(false);
  let result = $state<TranslatorTest | null>(null);

  async function tryIt() {
    testing = true;
    result = null;
    try {
      result = await api.testTranslator($state.snapshot(tr));
    } catch (e) {
      result = { ok: false, error: e instanceof ApiError ? e.message : String(e) };
    } finally {
      testing = false;
    }
  }
</script>

<PageHeader title="Subtitles" subtitle="Speech → text on this machine, then translated by the model you pick." />

<Card
  title="Translator"
  subtitle="Which AI turns the English lines into Romanian. Swaps live; no restart."
  icon={Languages}
>
  <div class="providers" role="radiogroup">
    {#each app.providers as p, i (p.id)}
      <div in:fly={{ y: 10, duration: 400, delay: i * 70 }}>
        <ProviderCard
          icon={icons[p.id]}
          label={p.label}
          description={p.description}
          selected={tr.provider === p.id}
          status={{ ok: p.ready, text: p.ready ? "Ready" : (p.why ?? "Not ready") }}
          onselect={() => (tr.provider = p.id)}
        />
      </div>
    {/each}
  </div>

  {#if provider?.secret}
    <div class="block" transition:slide={{ duration: 300 }}>
      <Field label="API key" hint="Write-only: stored in secrets.toml (mode 600), never shown again.">
        <SecretField name={provider.secret} placeholder="sk-ant-…" />
      </Field>
    </div>
  {/if}

  <div class="block">
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
  </div>

  <div class="block try">
    <div class="try-head">
      <div>
        <strong>Try it</strong>
        <span>Translates four sample lines with the settings above, even unsaved ones.</span>
      </div>
      <button class="btn" onclick={tryIt} disabled={testing}>
        <Play size={14} />
        {testing ? "Translating…" : "Run a test"}
      </button>
    </div>
    {#if testing}
      <div class="lines" transition:slide={{ duration: 250 }}>
        {#each { length: 4 }, i (i)}
          <div class="skeleton" style:animation-delay="{i * 120}ms"></div>
        {/each}
      </div>
    {:else if result}
      <div class="lines" transition:slide={{ duration: 300 }}>
        {#if result.lines}
          {#each result.lines as line, i (i)}
            <div class="line" in:fly={{ x: -12, duration: 420, delay: i * 110 }}>
              <span class="src">{line.source}</span>
              <span class="arrow">→</span>
              <span class="dst">{line.target}</span>
            </div>
          {/each}
        {/if}
        <div class="verdict">
          {#if result.ok}
            <Badge tone="good">Works</Badge>
          {:else}
            <Badge tone="bad">{result.error}</Badge>
          {/if}
          {#if result.seconds}<Badge><Timer size={11} /> {result.seconds}s</Badge>{/if}
        </div>
      </div>
    {/if}
  </div>

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
  title="Speech to text"
  subtitle="Runs on this machine. Turns the film's audio into timed English lines."
  icon={AudioLines}
  delay={80}
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
  .providers {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
  }

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

  .models {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
    border-color: rgba(164, 139, 255, 0.6);
    background: var(--accent-soft);
    transform: translateY(-1px);
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
    border-color: rgba(164, 139, 255, 0.6);
  }

  .try-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .try-head div {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .try-head span {
    color: var(--text-faint);
    font-size: 12.5px;
  }

  .lines {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
  }

  .line {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 14px;
    align-items: center;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid var(--border);
  }

  .src {
    color: var(--text-dim);
  }

  .arrow {
    color: var(--text-faint);
  }

  .dst {
    font-weight: 560;
  }

  .verdict {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .skeleton {
    height: 40px;
    border-radius: var(--radius-sm);
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.06),
        transparent
      )
      0 0 / 200% 100%,
      rgba(0, 0, 0, 0.2);
    animation: sweep 1.3s ease-in-out infinite;
  }

  @keyframes sweep {
    from {
      background-position: 150% 0;
    }
    to {
      background-position: -50% 0;
    }
  }
</style>
