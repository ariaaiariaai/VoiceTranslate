<script lang="ts">
  import { transcripts } from '../lib/stores'

  let listEl: HTMLDivElement | null = $state(null)

  // Auto-scroll to bottom when new transcript arrives.
  $effect(() => {
    if (listEl && $transcripts.length > 0) {
      listEl.scrollTop = listEl.scrollHeight
    }
  })
</script>

<div class="transcript-list" bind:this={listEl}>
  {#if $transcripts.length === 0}
    <div class="empty">
      <div class="empty-icon">🌏</div>
      <div class="empty-text">
        按「開始翻譯」開始接收日文講解<br />
        翻譯會以文字同語音顯示
      </div>
    </div>
  {:else}
    {#each $transcripts as line (line.id)}
      <div class="line" class:partial={line.partial}>
        {#if line.ja}
          <div class="ja">{line.ja}</div>
        {/if}
        {#if line.zh}
          <div class="zh">
            {line.zh}
            {#if line.latency_ms > 0}
              <span class="latency">{Math.round(line.latency_ms / 100) / 10}s</span>
            {/if}
            {#if line.quality_score !== undefined && line.quality_score !== null}
              <span
                class="quality"
                class:quality-good={line.quality_score >= 8}
                class:quality-ok={line.quality_score >= 6 && line.quality_score < 8}
                class:quality-low={line.quality_score < 6}
                title="翻譯品質評分 (1-10)"
              >
                ★ {line.quality_score}
              </span>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
  {/if}
</div>

<style>
  .transcript-list {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    -webkit-overflow-scrolling: touch;
  }
  .empty {
    margin: auto;
    text-align: center;
    color: rgba(255, 255, 255, 0.55);
    padding: 2rem;
  }
  .empty-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }
  .empty-text {
    font-size: 0.95rem;
    line-height: 1.5;
  }
  .line {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    animation: slideIn 0.25s ease-out;
  }
  .line.partial {
    opacity: 0.5;
    background: rgba(255, 255, 255, 0.03);
  }
  .ja {
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.55);
    margin-bottom: 0.25rem;
    line-height: 1.4;
  }
  .zh {
    font-size: 1.05rem;
    color: #fff;
    line-height: 1.5;
    font-weight: 500;
  }
  .latency {
    margin-left: 0.5rem;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.4);
    font-weight: 400;
  }
  .quality {
    margin-left: 0.4rem;
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 500;
  }
  .quality-good {
    background: rgba(34, 197, 94, 0.2);
    color: #86efac;
  }
  .quality-ok {
    background: rgba(234, 179, 8, 0.2);
    color: #fde047;
  }
  .quality-low {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
  }
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
