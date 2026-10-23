<script lang="ts">
  import { HardDrive, Recycle } from "@lucide/svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";
  import Card from "../lib/components/Card.svelte";
  import Field from "../lib/components/Field.svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import Slider from "../lib/components/Slider.svelte";
  import { bytes } from "../lib/format";
  import { app } from "../lib/state.svelte";

  const dl = $derived(app.draft!.downloads); // derived: a save replaces app.draft
  const GB = 1024 ** 3;
  const free = $derived(app.status?.disk.free ?? 0);
  // Scale the picture so both the free space and the reserve fit, with some headroom.
  const span = $derived(Math.max(free, dl.min_free_gb * GB) * 1.15 || 1);
  const freeW = new Tween(0, { duration: 900, easing: cubicOut });
  const reserveW = new Tween(0, { duration: 600, easing: cubicOut });
  $effect(() => {
    freeW.target = free / span;
    reserveW.target = (dl.min_free_gb * GB) / span;
  });
</script>

<PageHeader
  title="Downloads"
  subtitle="Torrents keep downloading while you pause; old ones are cleaned up automatically."
/>

<Card
  title="Disk reserve"
  subtitle="Prefetching the next episode stops before the disk drops below this, and the nightly cleanup frees space down to it."
  icon={HardDrive}
>
  <div class="disk">
    <div class="bar">
      <span class="free" style:width="{freeW.current * 100}%"></span>
      <span class="reserve" style:width="{reserveW.current * 100}%">
        {#if reserveW.current > 0.1}<em>reserve</em>{/if}
      </span>
    </div>
    <div class="legend num">
      <span><i class="sw free"></i>{bytes(free)} free now</span>
      <span><i class="sw res"></i>{dl.min_free_gb} GB kept free</span>
    </div>
  </div>
  <Field label="Keep at least" tomlKey="downloads.min_free_gb">
    <Slider bind:value={dl.min_free_gb} min={1} max={200} step={1} unit="GB" />
  </Field>
</Card>

<Card
  title="Cleanup"
  subtitle="A daily job deletes torrents nobody has played for a while. Anything the TV is playing is never touched."
  icon={Recycle}
  delay={80}
>
  <Field
    label="Delete after"
    hint="Days since a torrent was last played."
    tomlKey="downloads.stale_after_days"
  >
    <Slider bind:value={dl.stale_after_days} min={1} max={90} step={1} unit="days" />
  </Field>
</Card>

<style>
  .disk {
    margin-bottom: 22px;
  }

  .bar {
    position: relative;
    height: 34px;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    overflow: hidden;
  }

  .bar span {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
  }

  .free {
    background: rgba(164, 139, 255, 0.4);
  }

  .reserve {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 10px;
    background: repeating-linear-gradient(
      -45deg,
      rgba(10, 9, 15, 0.55) 0 6px,
      rgba(10, 9, 15, 0.25) 6px 12px
    );
    border-right: 2px solid #fff;
  }

  .reserve em {
    font-style: normal;
    font-size: 11px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }

  .legend {
    display: flex;
    gap: 22px;
    margin-top: 10px;
    font-size: 12.5px;
    color: var(--text-dim);
  }

  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }

  .sw {
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }

  .sw.free {
    background: rgba(164, 139, 255, 0.6);
  }

  .sw.res {
    background: repeating-linear-gradient(-45deg, #555 0 3px, #222 3px 6px);
    border: 1px solid #fff;
  }
</style>
