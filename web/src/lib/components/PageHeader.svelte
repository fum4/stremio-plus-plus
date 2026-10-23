<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    subtitle: string;
    children?: Snippet;
  }
  let { title, subtitle, children }: Props = $props();
</script>

<header>
  <div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>
  {#if children}<div class="side">{@render children()}</div>{/if}
</header>

<style>
  header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 6px;
  }

  h1 {
    font-size: 30px;
    font-weight: 680;
    letter-spacing: -0.035em;
  }

  p {
    margin: 4px 0 0;
    color: var(--text-dim);
  }
</style>
