<script lang="ts">
  // The film as a timeline: subtitled ranges filled, the TV's playhead as a caret.
  interface Props {
    duration: number;
    covered: [number, number][];
    playhead: number; // seconds
    failed?: boolean;
  }
  let { duration, covered, playhead, failed = false }: Props = $props();
  const pct = (s: number) => `${(Math.min(Math.max(s, 0), duration) / duration) * 100}%`;
</script>

<div
  class="track"
  class:failed
  role="img"
  aria-label="Subtitled ranges of the film, with the current playhead"
>
  {#each covered as [start, end] (start)}
    <span class="span" style:left={pct(start)} style:width="calc({pct(end)} - {pct(start)})"></span>
  {/each}
  <span class="caret" style:left={pct(playhead)}></span>
</div>

<style>
  .track {
    position: relative;
    height: 8px;
    border-radius: 99px;
    background: rgba(255, 255, 255, 0.07);
  }

  .span {
    position: absolute;
    top: 0;
    bottom: 0;
    min-width: 2px;
    border-radius: 99px;
    background: var(--violet);
    transition:
      left 0.8s var(--ease-out),
      width 0.8s var(--ease-out);
  }

  .failed .span {
    background: var(--text-faint);
  }

  .caret {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 2px;
    margin-left: -1px;
    border-radius: 2px;
    background: var(--text);
    transition: left 1.2s var(--ease-out);
  }
</style>
