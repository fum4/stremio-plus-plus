<script lang="ts" generics="T extends string | number">
  // A row of mutually exclusive options with a sliding highlight.
  interface Option {
    value: T;
    label: string;
    disabled?: boolean;
  }
  interface Props {
    options: Option[];
    value: T;
    label: string;
  }
  let { options, value = $bindable(), label }: Props = $props();
  const index = $derived(Math.max(0, options.findIndex((o) => o.value === value)));
</script>

<div class="seg" role="radiogroup" aria-label={label} style:--n={options.length} style:--i={index}>
  <span class="thumb" aria-hidden="true"></span>
  {#each options as o (o.value)}
    <button
      role="radio"
      aria-checked={o.value === value}
      class:on={o.value === value}
      disabled={o.disabled}
      onclick={() => (value = o.value)}
    >
      {o.label}
    </button>
  {/each}
</div>

<style>
  .seg {
    position: relative;
    display: grid;
    grid-template-columns: repeat(var(--n), 1fr);
    padding: 4px;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid var(--border-strong);
  }

  .thumb {
    position: absolute;
    top: 4px;
    bottom: 4px;
    left: 4px;
    width: calc((100% - 8px) / var(--n));
    border-radius: 9px;
    background: var(--accent-soft);
    border: 1px solid rgba(164, 139, 255, 0.45);
    transform: translateX(calc(var(--i) * 100%));
    transition: transform 0.35s var(--ease-spring);
  }

  button {
    position: relative;
    padding: 8px 6px;
    font-size: 13px;
    font-weight: 560;
    color: var(--text-dim);
    background: none;
    border: none;
    border-radius: 9px;
    white-space: nowrap;
    transition: color 0.2s;
  }

  button:hover:not(:disabled) {
    color: var(--text);
  }

  button.on {
    color: var(--violet);
  }

  button:disabled {
    opacity: 0.35;
    cursor: default;
  }
</style>
