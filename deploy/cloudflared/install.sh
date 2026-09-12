#!/usr/bin/env bash
# Install Cloudflare tunnel for VoiceTranslate.
# Prereqs:
#   - Cloudflare account (free tier is fine)
#   - A domain added to Cloudflare (or use trycloudflare.com random URL)
#
# This script:
#   1. Logs into Cloudflare via OAuth (one-time, opens browser)
#   2. Creates a named tunnel "voicetranslate"
#   3. Sets up DNS for the hostname
#   4. Writes config.yml
#   5. Tests the tunnel locally
set -euo pipefail

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared..."
  brew install cloudflared
fi

TUNNEL_NAME="${TUNNEL_NAME:-voicetranslate}"
HOSTNAME="${HOSTNAME:-translate.example.com}"
CONFIG_DIR="${HOME}/.cloudflared"

mkdir -p "${CONFIG_DIR}"

# 1. Login
echo "→ Logging into Cloudflare (browser will open)..."
cloudflared tunnel login

# 2. Create tunnel (idempotent)
if cloudflared tunnel list 2>/dev/null | grep -q "${TUNNEL_NAME}"; then
  echo "→ Tunnel '${TUNNEL_NAME}' already exists"
  TUNNEL_ID=$(cloudflared tunnel list --output json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data:
    if t['name'] == '${TUNNEL_NAME}':
        print(t['id'])
        break
")
else
  echo "→ Creating named tunnel '${TUNNEL_NAME}'..."
  cloudflared tunnel create "${TUNNEL_NAME}"
  TUNNEL_ID=$(cloudflared tunnel list --output json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data:
    if t['name'] == '${TUNNEL_NAME}':
        print(t['id'])
        break
")
fi

echo "Tunnel ID: ${TUNNEL_ID}"

# 3. Route DNS
echo "→ Routing ${HOSTNAME} → tunnel..."
cloudflared tunnel route dns "${TUNNEL_NAME}" "${HOSTNAME}" || echo "DNS route may already exist; continuing"

# 4. Write config
echo "→ Writing config.yml..."
cat > "${CONFIG_DIR}/config.yml" <<YAML
tunnel: ${TUNNEL_ID}
credentials-file: ${CONFIG_DIR}/${TUNNEL_ID}.json

ingress:
  - hostname: ${HOSTNAME}
    path: /api/.*
    service: http://127.0.0.1:8000
  - hostname: ${HOSTNAME}
    path: /ws
    service: http://127.0.0.1:8000
  - hostname: ${HOSTNAME}
    service: http_status:404
YAML

echo "✅ Cloudflare Tunnel installed."
echo
echo "Test locally:"
echo "  cloudflared tunnel run ${TUNNEL_NAME}"
echo
echo "Verify from iPhone:"
echo "  curl https://${HOSTNAME}/api/health"
