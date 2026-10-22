<script lang="ts">
  interface Props {
    checked: boolean;
    label: string;
  }
  let { checked = $bindable(), label }: Props = $props();
</script>

<button class="toggle" class:on={checked} role="switch" aria-checked={checked} aria-label={label} onclick={() => (checked = !checked)}>
  <span class="knob"></span>
</button>

<style>
  .toggle {
    position: relative;
    width: 40px;
    height: 24px;
    flex: none;
    padding: 0;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid var(--border-strong);
    transition: background 0.25s, border-color 0.25s;
  }

  .toggle.on {
    background: var(--violet);
    border-color: var(--violet);
  }

  .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
    transition: transform 0.3s var(--ease-spring);
  }

  .on .knob {
    transform: translateX(16px);
  }
</style>
