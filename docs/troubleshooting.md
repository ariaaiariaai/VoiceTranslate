# Troubleshooting

## "AudioContext was not allowed to start" in Safari console

iOS Safari requires a user gesture before any audio. The "開始翻譯" button is the gesture. If you see this, the user clicked through a programmatic path — refactor to always require a real tap.

## "Cannot read properties of undefined (reading 'getUserMedia')"

Page is not served over HTTPS, or the user navigated to an `http://` URL. Cloudflare Tunnel always serves HTTPS, but for local dev use Safari with `http://localhost:5173` (localhost is exempt).

## WebSocket disconnects every 30 s on cellular

iOS Safari aggressively suspends background tabs. The reconnect logic in `lib/net/ws-client.ts` handles this — the WS reconnects within 8 s of resume. If it's worse than this, check whether Wake Lock is held (it shouldn't be after Stop).

## Translation returns empty string

Check `tail -f ~/Library/Logs/VoiceTranslate/backend.out.log`:

```
stt.transcribed text_len=0       # STT got nothing — VAD dropped it
```

Either:
- Mic input too quiet → speak closer / increase mic gain in iOS Settings
- VAD threshold wrong → lower VOICETRANSLATE_VAD_THRESHOLD in launchd plist env

```
mt.translated zh_len=0           # MT returned empty — usually a model loading issue
```

```
tts.edge_tts.error 403           # Edge TTS rate-limited
```

Wait 30 s and retry, or switch to MeloTTS (requires installing MeCab + melotts from git).

## llama-server crashes with OOM

16 GB is tight with MT loaded. Solutions:
- Use Q3_K_M quantisation (smaller, ~3.2 GB): `bash backend/scripts/quantize_mt.sh q3_k_m`
- Reduce context: edit `backend/app/config.py` → `mt_ctx_size = 2048`
- Or use NLLB-200-distilled-600M (much smaller MT, but lower quality)

## Backend won't start after reboot

```bash
launchctl print gui/$(id -u)/com.voicetranslate.backend 2>&1 | head -30
```

Common boot failures:
- `/Users/ariaai/.local/bin` not in PATH (uvicorn shim missing) — install via `pip install --user` or fix PATH
- Models not yet on disk → re-run model download scripts

## Cloudflare tunnel "no such host"

If `cloudflared tunnel run` fails with DNS errors:
- `cloudflared tunnel info voicetranslate` to verify tunnel exists
- `cloudflared tunnel route dns voicetranslate <hostname>` to recreate DNS record

## Edge TTS keeps failing

Microsoft occasionally tightens the public endpoint. Workarounds:
- Update: `pip install -U edge-tts`
- Fall back to MeloTTS: `pip install mecab mecab-python3 unidic-lite && pip install git+https://github.com/myshell-ai/MeloTTS.git`
- Or accept the temporary outage and use text-only mode

## Performance degraded over time

```bash
# Check for memory leaks
ps -o pid,rss,command -p $(pgrep -f "uvicorn app.main")

# Check llama-server memory
ps -o pid,rss,command -p $(pgrep -f llama-server)
```

If RSS keeps growing across hours, restart: `launchctl kickstart -k gui/$(id -u)/com.voicetranslate.backend`.
