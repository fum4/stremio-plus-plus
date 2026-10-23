<script lang="ts">
  interface Props {
    value: number;
    min: number;
    max: number;
    step?: number;
    unit?: string;
  }
  let { value = $bindable(), min, max, step = 1, unit = "" }: Props = $props();
  const pct = $derived(((value - min) / (max - min)) * 100);
</script>

<div class="slider">
  <input type="range" {min} {max} {step} bind:value style:--pct="{pct}%" />
  <span class="out num">{value}<small>{unit}</small></span>
</div>

<style>
  .slider {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  input {
    flex: 1;
    appearance: none;
    height: 6px;
    border-radius: 99px;
    background: linear-gradient(var(--violet), var(--violet)) 0 / var(--pct) 100% no-repeat,
      rgba(255, 255, 255, 0.08);
    outline: none;
    cursor: pointer;
  }

  input::-webkit-slider-thumb {
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #fff;
    border: none;
    box-shadow:
      0 0 0 4px rgba(164, 139, 255, 0.25),
      0 4px 10px rgba(0, 0, 0, 0.5);
    transition:
      transform 0.2s var(--ease-spring),
      box-shadow 0.2s;
  }

  input:hover::-webkit-slider-thumb {
    transform: scale(1.12);
  }

  input:active::-webkit-slider-thumb {
    transform: scale(0.95);
    box-shadow:
      0 0 0 7px rgba(164, 139, 255, 0.3),
      0 4px 10px rgba(0, 0, 0, 0.5);
  }

  input::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #fff;
    border: none;
  }

  .out {
    min-width: 72px;
    padding: 6px 10px;
    text-align: right;
    font-weight: 600;
    border-radius: var(--radius-sm);
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid var(--border);
  }

  small {
    margin-left: 3px;
    color: var(--text-faint);
    font-weight: 500;
  }
</style>
