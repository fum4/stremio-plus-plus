<script lang="ts">
  // The addon URL three ways: copy, open in Stremio, QR for a phone.
  import { ExternalLink, Hourglass, QrCode, ShieldAlert } from "@lucide/svelte";
  import QRCode from "qrcode";
  import CopyField from "./CopyField.svelte";

  interface Props {
    url: string | null;
  }
  let { url }: Props = $props();
  const deepLink = $derived((url ?? "").replace(/^https?:\/\//, "stremio://"));
  let qr = $state("");
  $effect(() => {
    if (!url) return;
    void QRCode.toDataURL(url, {
      margin: 1,
      width: 400,
      color: { dark: "#17121fff", light: "#ffffffff" },
    }).then((d) => (qr = d));
  });

  const steps = [
    ["Open Stremio", "on a phone, laptop or stremio.com, signed in to the same account as the TV."],
    ["Add the addon", "with the button below, or paste the URL into Addons → search box."],
    ["Done", "Stremio syncs it to the TV. Pick “Romanian (AI)” in the subtitle menu."],
  ] as const;
</script>

{#if !url}
  <p class="pending">
    <Hourglass size={15} />
    The addon needs its HTTPS certificate first: finish the Streaming server step of the setup.
  </p>
{:else}
<div class="layout">
  <div class="left">
    <ol>
      {#each steps as [title, text], i (title)}
        <li style:animation-delay="{120 + i * 90}ms">
          <span class="n">{i + 1}</span>
          <div><strong>{title}</strong> <span>{text}</span></div>
        </li>
      {/each}
    </ol>
    <CopyField value={url} secret />
    <div class="actions">
      <a class="btn primary" href={deepLink}><ExternalLink size={15} /> Open in Stremio</a>
    </div>
    <p class="warn">
      <ShieldAlert size={14} />
      The URL contains your private token. Anyone with it can use your addon. Don't share it.
    </p>
  </div>
  <div class="qr">
    {#if qr}
      <img src={qr} alt="QR code of the addon URL" />
    {:else}
      <div class="qr-ph"><QrCode size={40} /></div>
    {/if}
    <span>Scan with your phone</span>
  </div>
</div>
{/if}

<style>
  .layout {
    display: grid;
    grid-template-columns: 1fr 210px;
    gap: 30px;
    align-items: start;
  }

  .left {
    display: flex;
    flex-direction: column;
    gap: 18px;
    min-width: 0;
  }

  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  li {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    animation: in 0.5s var(--ease-out) both;
  }

  li span:not(.n) {
    color: var(--text-dim);
  }

  .n {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    flex: none;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 700;
    color: #17121f;
    background: var(--violet);
  }

  .actions {
    display: flex;
    gap: 10px;
  }

  .warn {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 12.5px;
    color: var(--text-faint);
  }

  .qr {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-faint);
  }

  .qr img,
  .qr-ph {
    width: 200px;
    height: 200px;
    border-radius: 16px;
    background: #fff;
    padding: 10px;
    box-shadow: 0 12px 30px -18px rgba(0, 0, 0, 0.8);
    animation: pop 0.6s var(--ease-spring) both 0.2s;
  }

  .qr-ph {
    display: grid;
    place-items: center;
    color: #999;
  }

  @keyframes in {
    from {
      opacity: 0;
      transform: translateX(-8px);
    }
  }

  @keyframes pop {
    from {
      opacity: 0;
      transform: scale(0.85) rotate(-3deg);
    }
  }

  .pending {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    color: var(--text-dim);
  }

  @media (max-width: 760px) {
    .layout {
      grid-template-columns: 1fr;
    }
  }
</style>
