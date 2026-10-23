<script lang="ts">
  interface Props {
    value: number; // 0..1
    active?: boolean; // shimmer while something is moving
  }
  let { value, active = false }: Props = $props();
</script>

<div class="track">
  <div class="bar" class:active style:width="{Math.max(0, Math.min(1, value)) * 100}%"></div>
</div>

<style>
  .track {
    height: 6px;
    border-radius: 99px;
    background: rgba(255, 255, 255, 0.07);
    overflow: hidden;
  }

  .bar {
    position: relative;
    height: 100%;
    border-radius: inherit;
    background: var(--violet);
    transition: width 1s var(--ease-out);
    overflow: hidden;
  }

  .bar.active::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
    transform: translateX(-100%);
    animation: shimmer 2.4s infinite;
  }

  @keyframes shimmer {
    to {
      transform: translateX(100%);
    }
  }
</style>
