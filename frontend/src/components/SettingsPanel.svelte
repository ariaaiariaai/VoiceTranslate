<script lang="ts">
  import { backendUrl, connection } from '../lib/stores'
  import { promptInstall, isInstalled, deferredPrompt } from '../lib/pwa'

  let showSettings = $state(false)

  async function onInstall() {
    const ok = await promptInstall()
    if (!ok) {
      alert('如要安裝：Safari → 分享 → 加到主畫面')
    }
  }
</script>

<button class="settings-btn" onclick={() => (showSettings = !showSettings)} aria-label="設定">
  ⚙
</button>

{#if showSettings}
  <div class="overlay" onclick={() => (showSettings = false)}></div>
  <div class="panel">
    <h2>設定</h2>

    <label class="field">
      <span>後端 URL</span>
      <input
        type="url"
        bind:value={$backendUrl}
        placeholder="https://translate.example.com"
        spellcheck="false"
      />
      <small>改完需要重新整理頁面</small>
    </label>

    {#if !$isInstalled && $deferredPrompt}
      <button class="primary" onclick={onInstall}>安裝到手機主畫面</button>
    {:else if !$isInstalled}
      <div class="hint">
        iOS 安裝方法：Safari → 分享 ↑ → 加到主畫面
      </div>
    {:else}
      <div class="hint success">已安裝 ✓</div>
    {/if}

    <button class="secondary" onclick={() => (showSettings = false)}>關閉</button>
  </div>
{/if}

<style>
  .settings-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: white;
    font-size: 1.1rem;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    z-index: 10;
  }
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 20;
  }
  .panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1a1a1a;
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
    padding: 1.5rem;
    z-index: 21;
    max-height: 80vh;
    overflow-y: auto;
  }
  h2 {
    margin: 0 0 1rem;
    font-size: 1.1rem;
  }
  .field {
    display: block;
    margin-bottom: 1rem;
  }
  .field > span {
    display: block;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 0.25rem;
  }
  .field input {
    width: 100%;
    padding: 0.65rem 0.75rem;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: white;
    font-size: 0.95rem;
    box-sizing: border-box;
  }
  .field small {
    display: block;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 0.25rem;
  }
  .hint {
    background: rgba(255, 255, 255, 0.05);
    padding: 0.75rem;
    border-radius: 8px;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 0.75rem;
  }
  .hint.success {
    color: #22c55e;
  }
  button.primary,
  button.secondary {
    width: 100%;
    padding: 0.75rem;
    border: none;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    margin-bottom: 0.5rem;
    -webkit-tap-highlight-color: transparent;
  }
  .primary {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
  }
  .secondary {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
</style>
