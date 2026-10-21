<script lang="ts">
  // Translator provider cards, plus the API key field when the chosen provider needs one.
  import { KeyRound, Terminal } from "@lucide/svelte";
  import { fly, slide } from "svelte/transition";
  import Field from "../components/Field.svelte";
  import ProviderCard from "../components/ProviderCard.svelte";
  import SecretField from "../components/SecretField.svelte";
  import { app } from "../state.svelte";

  const tr = $derived(app.draft!.subtitles.translator);
  const icons = { "claude-cli": Terminal, anthropic: KeyRound } as const;
  const provider = $derived(app.providers.find((p) => p.id === tr.provider));
</script>

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
  <div class="key" transition:slide={{ duration: 300 }}>
    <Field label="API key" hint="Write-only: stored in secrets.toml (mode 600), never shown again.">
      <SecretField name={provider.secret} placeholder="sk-ant-…" />
    </Field>
  </div>
{/if}

<style>
  .providers {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
  }

  .key {
    margin-top: 18px;
  }
</style>
