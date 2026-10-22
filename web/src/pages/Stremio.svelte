<script lang="ts">
  import { Tv, UserRound } from "@lucide/svelte";
  import AccountPanel from "../lib/components/AccountPanel.svelte";
  import AddonInstall from "../lib/components/AddonInstall.svelte";
  import Card from "../lib/components/Card.svelte";
  import Field from "../lib/components/Field.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import Toggle from "../lib/components/Toggle.svelte";
  import { app } from "../lib/state.svelte";

  const stremio = $derived(app.draft!.stremio);
</script>

<PageHeader title="Stremio" subtitle="Your Stremio account and the Stremio++ addon in it." />

<Card title="Account" subtitle="Optional, but it makes the addon one click and keeps it on top." icon={UserRound}>
  <AccountPanel />
  <div class="keep">
    <Field
      label="Keep Stremio++ first"
      hint="Stremio lists streams in the order of your addons. When another addon gets installed in front, stremio++ moves itself back to the top (checked every 10 minutes)."
      tomlKey="stremio.keep_addon_first"
    >
      <Toggle bind:checked={stremio.keep_addon_first} label="Keep Stremio++ first" />
    </Field>
  </div>
</Card>

<Card title="Install by hand" subtitle="Without an account: add the addon from any Stremio app signed in to your account." icon={Tv} delay={60}>
  <AddonInstall url={app.status?.addon.manifest_url ?? null} />
</Card>

<style>
  .keep {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
  }
</style>
