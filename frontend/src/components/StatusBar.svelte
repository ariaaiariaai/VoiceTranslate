<script lang="ts">
  import { connection, lastLatency } from '../lib/stores'

  function computeLabel(conn: string, lat: number): string {
    switch (conn) {
      case 'idle':
        return '未連線'
      case 'connecting':
        return '連線中…'
      case 'connected':
        return `已連線 · ${lat > 0 ? Math.round(lat / 100) / 10 + 's' : ''}`
      case 'reconnecting':
        return '重新連線中…'
      case 'error':
        return '連線錯誤'
      default:
        return ''
    }
  }

  let label = $derived(computeLabel($connection, $lastLatency))
</script>

<div class="status" class:connected={$connection === 'connected'} class:error={$connection === 'error'}>
  <span class="dot"></span>
  <span class="text">{label}</span>
</div>

<style>
  .status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.6);
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
  }
  .status.connected .dot {
    background: #22c55e;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
  }
  .status.error .dot {
    background: #ef4444;
  }
</style>
