<script lang="ts">
  import { CircleCheck, CircleX, TriangleAlert } from "@lucide/svelte";
  import type { SetupCheck } from "../types";
  import CopyField from "./CopyField.svelte";

  interface Props {
    check: SetupCheck;
  }
  let { check }: Props = $props();
  const icons = { ok: CircleCheck, warn: TriangleAlert, bad: CircleX };
  const Icon = $derived(icons[check.level]);
  // Shell commands get a copy field; prose advice is just text; action ids are the wizard's.
  const isCommand = $derived(!!check.fix && /^(brew|mise|sudo|git) /.test(check.fix));
  const isAdvice = $derived(!!check.fix && !isCommand && check.fix.includes(" "));
</script>

<div class="row {check.level}">
  <span class="icon"><Icon size={17} /></span>
  <div class="text">
    <strong>{check.label}</strong>
    <span>{check.detail}</span>
    {#if check.level !== "ok" && isCommand}
      <div class="fix"><CopyField value={check.fix ?? ""} /></div>
    {:else if check.level !== "ok" && isAdvice}
      <span class="advice">{check.fix}</span>
    {/if}
  </div>
</div>

<style>
  .row {
    display: flex;
    gap: 12px;
    padding: 12px 14px;
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border);
    transition: border-color 0.3s;
  }

  .icon {
    display: grid;
    padding-top: 1px;
    transition: color 0.3s;
  }

  .ok .icon {
    color: var(--green);
  }
  .warn .icon {
    color: var(--amber);
  }
  .bad .icon {
    color: var(--red);
  }
  .bad {
    border-color: rgba(255, 125, 142, 0.25);
  }

  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .text span {
    color: var(--text-dim);
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  .advice {
    color: var(--text-faint) !important;
  }

  .fix {
    margin-top: 8px;
  }
</style>
