#!/usr/bin/env bash
# Uninstall VoiceTranslate launchd services.
set -euo pipefail

LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
PLIST_USER="gui/$(id -u)"

for label in com.voicetranslate.backend com.voicetranslate.tunnel; do
  launchctl bootout "${PLIST_USER}/${label}" 2>/dev/null && echo "→ Unloaded ${label}" || true
  rm -f "${LAUNCH_AGENTS}/${label}.plist" && echo "→ Removed ${label}.plist" || true
done

echo "✅ launchd services uninstalled."
