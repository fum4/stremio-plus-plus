<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    tone?: "good" | "warn" | "bad" | "accent" | "neutral";
    children: Snippet;
  }
  let { tone = "neutral", children }: Props = $props();
</script>

<span class="badge {tone}">{@render children()}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    white-space: nowrap;
    color: var(--text-dim);
    background: var(--surface-strong);
    border: 1px solid var(--border);
  }
  .good {
    color: var(--green);
    background: rgba(94, 234, 212, 0.08);
    border-color: rgba(94, 234, 212, 0.2);
  }
  .warn {
    color: var(--amber);
    background: rgba(251, 191, 119, 0.08);
    border-color: rgba(251, 191, 119, 0.2);
  }
  .bad {
    color: var(--red);
    background: rgba(255, 125, 142, 0.08);
    border-color: rgba(255, 125, 142, 0.22);
  }
  .accent {
    color: var(--violet);
    background: var(--accent-soft);
    border-color: rgba(164, 139, 255, 0.25);
  }
</style>
