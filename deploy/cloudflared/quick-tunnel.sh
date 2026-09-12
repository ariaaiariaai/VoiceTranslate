#!/usr/bin/env bash
# Quick tunnel — no domain required. Generates a random *.trycloudflare.com URL.
# Use this for quick testing or if you don't have a Cloudflare-managed domain.
set -euo pipefail

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared..."
  brew install cloudflared
fi

echo "Starting quick tunnel..."
exec cloudflared tunnel --url http://127.0.0.1:8000
