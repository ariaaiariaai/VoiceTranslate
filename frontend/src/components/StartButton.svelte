<script lang="ts">
  import { connection, mode } from '../lib/stores'

  let { onStart, onStop } = $props<{
    onStart: () => void
    onStop: () => void
  }>()

  let isRecording = $derived(
    $connection === 'connected' || $connection === 'connecting'
  )
</script>

<button
  class="start-btn"
  class:recording={isRecording}
  onclick={isRecording ? onStop : onStart}
  disabled={$connection === 'connecting' || $connection === 'reconnecting'}
>
  {#if isRecording}
    <span class="pulse" aria-hidden="true"></span>
    <span class="label">停止</span>
  {:else}
    <span class="mic">🎙</span>
    <span class="label">開始翻譯</span>
  {/if}
</button>

<style>
  .start-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    width: 100%;
    max-width: 320px;
    margin: 0 auto;
    padding: 1.25rem 1.5rem;
    font-size: 1.25rem;
    font-weight: 600;
    border: none;
    border-radius: 999px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    box-shadow: 0 10px 30px rgba(79, 70, 229, 0.4);
    cursor: pointer;
    transition:
      transform 0.15s,
      box-shadow 0.15s,
      background 0.2s;
    -webkit-tap-highlight-color: transparent;
  }
  .start-btn:active {
    transform: scale(0.97);
  }
  .start-btn.recording {
    background: linear-gradient(135deg, #dc2626, #b91c1c);
    box-shadow: 0 10px 30px rgba(220, 38, 38, 0.4);
  }
  .start-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .mic {
    font-size: 1.5rem;
  }
  .pulse {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: white;
    animation: pulse 1.2s ease-out infinite;
  }
  @keyframes pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.6);
    }
    100% {
      box-shadow: 0 0 0 14px rgba(255, 255, 255, 0);
    }
  }
</style>
