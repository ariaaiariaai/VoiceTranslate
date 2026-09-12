# VoiceTranslate — Travel Checklist

Print this page. Check off before each trip.

## Before leaving home

- [ ] Mac mini power LED is on
- [ ] Mac mini connected to UPS (battery backup)
- [ ] Mac mini network: primary Ethernet, fallback = iPhone USB hotspot
- [ ] macOS auto-updates paused: `sudo softwareupdate --ignore`
- [ ] System Settings → Energy → "Start up automatically after power failure" = ON
- [ ] Test: `curl http://localhost:8000/api/health` → `{"status":"ok",...}`

## From iPhone (test before trip)

- [ ] Open `https://<your-hostname>/` in Safari
- [ ] Add to Home Screen
- [ ] Open PWA from home screen — should show full-screen UI
- [ ] Tap Start → grant microphone permission
- [ ] Speak Japanese (or play a YouTube clip) — Chinese text + audio appear within ~5 s

## Day of travel

- [ ] iPhone charged (50%+)
- [ ] AirPods charged
- [ ] Cellular data plan active (will be used if home Wi-Fi fails)

## During travel

If the app says "重新連線中…" or doesn't connect:

1. Check Mac mini is reachable: from another device, `curl https://<hostname>/api/health`
2. If 503 / connection refused → Mac mini may be offline (power outage, ISP issue)
3. Accept the downtime, or use Mac mini's USB-tethered iPhone hotspot for network failover

If translation is slow (> 8 s per segment):

1. MT model was idle-unloaded. First request after that takes ~2 s extra for model reload.
2. If persistent → `launchctl kickstart -k gui/$(id -u)/com.voicetranslate.backend`

## Coming home

- [ ] Re-enable macOS auto-updates: `sudo softwareupdate --reset-default`
- [ ] Verify backend still running: `launchctl list | grep voicetranslate`
- [ ] Check disk usage: `du -sh ~/Models` (≈ 30 GB total)

## Emergency contacts (template)

- Cloudflare account email: ___
- Cloudflare domain registrar: ___
- Mac mini Tailscale/SSH access: ___
