#!/usr/bin/env bash
# Install VoiceTranslate launchd services.
# After install, backend and (optionally) cloudflared tunnel start automatically on login.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/VoiceTranslate"
PLIST_USER="gui/$(id -u)"

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"

# Backend plist — replace placeholder path with the actual one
BACKEND_PLIST="${LAUNCH_AGENTS}/com.voicetranslate.backend.plist"
cp "${SCRIPT_DIR}/com.voicetranslate.backend.plist" "${BACKEND_PLIST}"

# Optional tunnel plist
if [[ -f "${HOME}/.cloudflared/config.yml" ]]; then
  TUNNEL_PLIST="${LAUNCH_AGENTS}/com.voicetranslate.tunnel.plist"
  cp "${SCRIPT_DIR}/com.voicetranslate.tunnel.plist" "${TUNNEL_PLIST}"
  echo "→ Tunnel plist installed"
else
  echo "⚠ No Cloudflare config at ~/.cloudflared/config.yml — skipping tunnel plist"
fi

# Bootstrap (idempotent — bootout first if already loaded)
for label in com.voicetranslate.backend com.voicetranslate.tunnel; do
  plist="${LAUNCH_AGENTS}/${label}.plist"
  [[ ! -f "${plist}" ]] && continue
  launchctl bootout "${PLIST_USER}/${label}" 2>/dev/null || true
  launchctl bootstrap "${PLIST_USER}" "${plist}"
  echo "→ Loaded ${label}"
done

echo
echo "✅ launchd services installed."
echo
echo "Verify:"
echo "  launchctl list | grep voicetranslate"
echo "  curl http://localhost:8000/api/health"
echo
echo "Logs:"
echo "  tail -f ${LOG_DIR}/backend.out.log"
echo "  tail -f ${LOG_DIR}/tunnel.out.log"
