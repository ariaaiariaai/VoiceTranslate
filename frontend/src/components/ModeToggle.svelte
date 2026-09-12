<script lang="ts">
  import { mode } from '../lib/stores'

  let { onChange } = $props<{ onChange?: () => void }>()
</script>

<div class="toggle-row">
  <div class="group">
    <span class="label">輸出</span>
    <div class="seg">
      <button
        class:active={$mode === 'text'}
        onclick={() => {
          mode.set('text')
          onChange?.()
        }}
      >文字</button>
      <button
        class:active={$mode === 'audio'}
        onclick={() => {
          mode.set('audio')
          onChange?.()
        }}
      >語音</button>
      <button
        class:active={$mode === 'both'}
        onclick={() => {
          mode.set('both')
          onChange?.()
        }}
      >兩者</button>
    </div>
  </div>
</div>

<style>
  .toggle-row {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.03);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    align-items: center;
    justify-content: center;
  }
  .group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .label {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
  }
  .seg {
    display: flex;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 2px;
  }
  .seg button {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.6);
    padding: 0.35rem 0.75rem;
    font-size: 0.85rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    -webkit-tap-highlight-color: transparent;
  }
  .seg button.active {
    background: rgba(124, 58, 237, 0.6);
    color: white;
  }
</style>
