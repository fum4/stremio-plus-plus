<script lang="ts">
  import { ArrowLeft, ArrowRight, Check, PartyPopper, RefreshCw } from "@lucide/svelte";
  import { onDestroy, onMount } from "svelte";
  import { fade, fly } from "svelte/transition";
  import { backOut } from "svelte/easing";
  import { api } from "../lib/api";
  import AddonInstall from "../lib/components/AddonInstall.svelte";
  import CheckRow from "../lib/components/CheckRow.svelte";
  import { app } from "../lib/state.svelte";
  import ModelPicker from "../lib/translator/ModelPicker.svelte";
  import ProviderPicker from "../lib/translator/ProviderPicker.svelte";
  import TryIt from "../lib/translator/TryIt.svelte";
  import ModelStep from "./setup/ModelStep.svelte";
  import ServerStep from "./setup/ServerStep.svelte";
  import { confirmed, saveConfirmed, STEPS, stepChecks, stepDone, type StepId } from "./setup/steps";
  import TvStep from "./setup/TvStep.svelte";

  const POLL_MS = 3000;
  let ticked = $state(confirmed());
  let finishing = $state(false);
  let refreshing = $state(false);
  const setup = $derived(app.setup);
  const done = $derived(
    new Set(STEPS.filter((s) => setup && stepDone(setup, s, ticked)).map((s) => s.id)),
  );
  // Open on the first step that isn't done; afterwards the user moves freely.
  let current = $state<StepId>(STEPS.find((s) => setup && !stepDone(setup, s, confirmed()))?.id ?? "machine");
  const index = $derived(STEPS.findIndex((s) => s.id === current));
  const step = $derived(STEPS[index]!);
  const allDone = $derived(done.size === STEPS.length);

  let timer: ReturnType<typeof setInterval> | undefined;
  onMount(() => {
    timer = setInterval(() => void app.loadSetup(), POLL_MS);
  });
  onDestroy(() => clearInterval(timer));

  function tick(id: StepId, on: boolean) {
    const next = new Set(ticked);
    if (on) next.add(id);
    else next.delete(id);
    ticked = next;
    saveConfirmed(next);
  }

  async function next() {
    if (step.id === "translator" && app.dirty) await app.save();
    if (index < STEPS.length - 1) current = STEPS[index + 1]!.id;
  }

  async function recheck() {
    refreshing = true;
    await Promise.all([app.loadSetup(), app.loadProviders()]);
    refreshing = false;
  }

  async function finish() {
    finishing = true;
    app.setup = await api.completeSetup();
    finishing = false;
  }
</script>

<header class="top">
  <div>
    <h1>Set up stremio++</h1>
    <p>A few minutes, once. Everything here is saved to <code>config.toml</code> as you go.</p>
  </div>
  <div class="count num">{done.size} of {STEPS.length} done</div>
</header>

{#if setup?.completed}
  <section class="finished" in:fly={{ y: 12, duration: 450 }}>
    <span class="seal" in:fly={{ y: 8, duration: 600, easing: backOut }}><PartyPopper size={26} /></span>
    <div>
      <h2>You're all set</h2>
      <p>
        Pick <strong>Romanian (AI)</strong> in the TV's subtitle menu during any film. This page stays
        here as a health check: come back if something stops working.
      </p>
      <a class="btn primary" href="#overview">Go to the overview <ArrowRight size={15} /></a>
    </div>
  </section>
{/if}

{#if setup}
  <div class="wizard">
    <nav class="steps" aria-label="Setup steps">
      {#each STEPS as s, i (s.id)}
        <button class="step" class:active={s.id === current} onclick={() => (current = s.id)}>
          <span class="dot" class:done={done.has(s.id)}>
            {#if done.has(s.id)}
              <span in:fly={{ y: 4, duration: 300 }}><Check size={13} strokeWidth={3} /></span>
            {:else}
              {i + 1}
            {/if}
          </span>
          <span class="labels">
            <strong>{s.title}</strong>
            <span>{s.blurb}</span>
          </span>
        </button>
      {/each}
    </nav>

    {#key current}
      <section class="panel" in:fly={{ x: 16, duration: 380 }} out:fade={{ duration: 60 }}>
        <div class="panel-head">
          <span class="kicker">Step {index + 1}</span>
          <h2>{step.title}</h2>
        </div>

        {#if step.id === "server"}
          <ServerStep done={done.has("server")} />
        {:else if step.id === "translator"}
          <ProviderPicker />
          <div class="block"><ModelPicker /></div>
          <div class="block"><TryIt onresult={() => void recheck()} /></div>
        {:else if step.id === "model"}
          <ModelStep done={done.has("model")} />
        {:else if step.id === "tv"}
          <TvStep />
        {:else if step.id === "addon"}
          <AddonInstall url={setup.addon_url} />
        {/if}

        {#if step.checks.length && (step.id !== "model" || done.has("model"))}
          <div class="checks" class:block={step.id !== "machine"}>
            {#each stepChecks(setup, step) as check, i (check.id)}
              <div in:fly={{ y: 8, duration: 350, delay: i * 60 }}><CheckRow {check} /></div>
            {/each}
          </div>
        {/if}

        {#if step.confirm}
          <label class="confirm block">
            <input
              type="checkbox"
              checked={ticked.has(step.id)}
              onchange={(e) => tick(step.id, e.currentTarget.checked)}
            />
            <span>{step.confirm}</span>
          </label>
        {/if}

        <footer>
          <button class="btn ghost" onclick={() => (current = STEPS[index - 1]!.id)} disabled={index === 0}>
            <ArrowLeft size={15} /> Back
          </button>
          <div class="right">
            {#if step.checks.length}
              <button class="btn ghost" onclick={recheck} disabled={refreshing}>
                <RefreshCw size={14} class={refreshing ? "spin" : ""} /> Check again
              </button>
            {/if}
            {#if index < STEPS.length - 1}
              <button class="btn" class:primary={done.has(step.id)} onclick={next}>
                {done.has(step.id) ? "Continue" : "Skip for now"} <ArrowRight size={15} />
              </button>
            {:else}
              <button class="btn primary" onclick={finish} disabled={!allDone || finishing || setup.completed}>
                <Check size={15} /> {setup.completed ? "Setup complete" : "Finish setup"}
              </button>
            {/if}
          </div>
        </footer>
      </section>
    {/key}
  </div>
{/if}

<style>
  .top {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
  }

  h1 {
    font-size: 30px;
    font-weight: 680;
    letter-spacing: -0.035em;
  }

  .top p {
    margin: 4px 0 0;
    color: var(--text-dim);
  }

  .count {
    color: var(--text-faint);
    font-size: 13px;
    white-space: nowrap;
  }

  .finished {
    display: flex;
    gap: 18px;
    align-items: flex-start;
    padding: 22px;
    border-radius: var(--radius-lg);
    background: rgba(94, 234, 212, 0.05);
    border: 1px solid rgba(94, 234, 212, 0.22);
  }

  .finished h2 {
    font-size: 17px;
  }

  .finished p {
    margin: 4px 0 14px;
    color: var(--text-dim);
  }

  .seal {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    flex: none;
    border-radius: 14px;
    color: var(--green);
    background: rgba(94, 234, 212, 0.1);
  }

  .wizard {
    display: grid;
    grid-template-columns: 250px 1fr;
    gap: 22px;
    align-items: start;
  }

  .steps {
    position: sticky;
    top: 24px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .step {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 10px 12px;
    text-align: left;
    color: var(--text);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius);
    transition:
      background 0.2s,
      border-color 0.2s;
  }

  .step:hover {
    background: var(--surface);
  }

  .step.active {
    background: var(--surface-strong);
    border-color: var(--border);
  }

  .dot {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    flex: none;
    margin-top: 1px;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 650;
    color: var(--text-dim);
    border: 1px solid var(--border-strong);
    transition:
      background 0.3s,
      color 0.3s,
      border-color 0.3s;
  }

  .active .dot {
    color: var(--violet);
    border-color: var(--violet);
  }

  .dot.done {
    color: #10201d;
    background: var(--green);
    border-color: var(--green);
  }

  .labels {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .labels strong {
    font-weight: 580;
    font-size: 13.5px;
  }

  .labels span {
    font-size: 12px;
    color: var(--text-faint);
  }

  .panel {
    padding: 24px;
    border-radius: var(--radius-lg);
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
  }

  .panel-head {
    margin-bottom: 18px;
  }

  .kicker {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--violet);
  }

  .panel-head h2 {
    font-size: 20px;
    margin-top: 2px;
  }

  .block {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
  }

  .checks {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .confirm {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-weight: 540;
  }

  .confirm input {
    width: 18px;
    height: 18px;
    accent-color: var(--violet);
  }

  footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-top: 24px;
  }

  .right {
    display: flex;
    gap: 8px;
  }

  @media (max-width: 860px) {
    .wizard {
      grid-template-columns: 1fr;
    }
    .steps {
      position: static;
      flex-direction: row;
      overflow-x: auto;
    }
    .labels span {
      display: none;
    }
  }
</style>
