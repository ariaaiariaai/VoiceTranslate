<script lang="ts">
  import { connection, lastLatency } from '../lib/stores'
  import versionInfo from '../version.json'

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

<div class="status-row">
  <div class="status" class:connected={$connection === 'connected'} class:error={$connection === 'error'}>
    <span class="dot"></span>
    <span class="text">{label}</span>
  </div>
  <span class="version" title="Frontend + Backend commit">
    v{versionInfo.version} · {versionInfo.git_sha}
  </span>
</div>

<style>
  .status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.75rem;
    font-size: 0.75rem;
  }
  .status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: rgba(255, 255, 255, 0.6);
  }
  .dot {
    width: 7px;
    height: 7px;
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
  .version {
    color: rgba(255, 255, 255, 0.35);
    font-family: ui-monospace, 'SF Mono', monospace;
    font-size: 0.65rem;
  }
</style>
