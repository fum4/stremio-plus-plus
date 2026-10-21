<script lang="ts">
  import { Tv } from "@lucide/svelte";
  import AddonInstall from "../lib/components/AddonInstall.svelte";
  import Card from "../lib/components/Card.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import { app } from "../lib/state.svelte";
</script>

<PageHeader title="Install" subtitle="Add stremio++ to Stremio once; your account syncs it everywhere." />

<Card title="Your addon" icon={Tv}>
  <AddonInstall url={app.status?.addon.manifest_url ?? null} />
</Card>
