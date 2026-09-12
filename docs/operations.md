# Operations

Day-to-day running of VoiceTranslate.

## Quick reference

```bash
# Status
launchctl list | grep voicetranslate        # service PIDs
curl http://localhost:8000/api/health       # backend liveness
curl http://localhost:8000/api/ready        # models ready?

# Logs
tail -f ~/Library/Logs/VoiceTranslate/backend.out.log
tail -f ~/Library/Logs/VoiceTranslate/tunnel.out.log

# Restart backend (after code change)
launchctl kickstart -k gui/$(id -u)/com.voicetranslate.backend

# Stop / start
launchctl bootout gui/$(id -u)/com.voicetranslate.backend
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.voicetranslate.backend.plist

# Force-unload the MT model (release ~5 GB RAM)
curl -X POST http://localhost:8000/api/admin/unload/mt
```

## Directory layout

```
/Users/ariaai/Models/                       # large model files (not in repo)
├── llama.cpp/                              # source + Metal build
├── kotoba-whisper-v2.2/                    # raw HF model (2.8 GB)
├── kotoba-whisper-v2.2-ct2-int8/           # CTranslate2 int8 (731 MB)
├── qwen2.5-7b-instruct/                    # raw HF model (14 GB)
└── qwen2.5-7b-instruct-gguf/
    ├── fp16.gguf                           # 14 GB intermediate
    └── q4_k_m.gguf                         # 4.4 GB production quantised

/Users/ariaai/.cloudflared/
├── <UUID>.json                             # tunnel credential (BACK THIS UP)
└── config.yml

/Users/ariaai/Library/LaunchAgents/
├── com.voicetranslate.backend.plist
└── com.voicetranslate.tunnel.plist         # only if tunnel is installed

/Users/ariaai/Library/Logs/VoiceTranslate/
├── backend.out.log
├── backend.err.log
├── tunnel.out.log
└── tunnel.err.log
```

## First-time setup (already done if you followed the plan)

```bash
cd ~/Claude/Projects/VoiceTranslate

# Backend deps
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Build llama.cpp
brew install cmake go
git clone https://github.com/ggerganov/llama.cpp.git ~/Models/llama.cpp
cd ~/Models/llama.cpp
cmake -B build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j8

# Download + quantise models
bash backend/scripts/download_models.sh     # downloads HF models
bash backend/scripts/convert_kotoba.sh      # → CTranslate2 int8
bash backend/scripts/quantize_mt.sh         # → GGUF Q4_K_M

# Cloudflare tunnel
bash deploy/cloudflared/install.sh          # one-time OAuth + tunnel create

# launchd auto-start
bash deploy/launchd/install.sh
```

## iPhone setup

1. Open Safari on iPhone → `https://<your-hostname>/` (or trycloudflare.com URL).
2. Tap Share ↑ → **Add to Home Screen** → name "VoiceTranslate" → Add.
3. Open from home screen — runs as fullscreen PWA.
4. First tap on "開始翻譯" prompts for microphone permission.

## Travelling checklist

- [ ] Mac mini LED is on (not asleep)
- [ ] Mac mini power + network on UPS
- [ ] iPhone PWA opens and shows "已連線" status
- [ ] AirPods charged
- [ ] Test once with a YouTube Japanese video to confirm audio + translation

## Troubleshooting

### Backend won't start

```bash
tail -50 ~/Library/Logs/VoiceTranslate/backend.err.log
```

Common causes:
- Models dir missing → check `~/Models/`
- Port 8000 already used → `lsof -i :8000`
- Qwen GGUF corrupt → re-run `bash backend/scripts/quantize_mt.sh`

### "已連線" never appears on iPhone

- Mac mini not reachable from internet → check `https://<hostname>/api/health` from another network
- Cloudflare tunnel down → `launchctl list | grep tunnel` and `tail tunnel.err.log`
- DNS not propagated → `dig <hostname>` to confirm CNAME

### Translation is slow

```bash
curl http://localhost:8000/api/ready      # confirm mt is loaded
# If mt_loaded=false, first request after idle will pay a ~2s llama-server warm-up
```

Subsequent requests should be 2-4 s end-to-end. If consistently > 6 s, the MT model may have been swapped out (idle unload after 10 min).

### Out of memory

```bash
curl -X POST http://localhost:8000/api/admin/unload/mt   # free ~5 GB
# Subsequent request will reload in ~2 s
```

## Updating models

```bash
# Update kotoba (every 6 months)
huggingface-cli download kotoba-tech/kotoba-whisper-v2.2 --local-dir ~/Models/kotoba-whisper-v2.2
bash backend/scripts/convert_kotoba.sh
curl -X POST http://localhost:8000/api/admin/reload/stt

# Update Qwen/Sakura MT (every 3 months)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir ~/Models/qwen2.5-7b-instruct
bash backend/scripts/quantize_mt.sh
launchctl kickstart -k gui/$(id -u)/com.voicetranslate.backend
```

## Switching MT model

By default we use Qwen2.5-7B-Instruct (open, reliable). To use Sakura-7B (specialised JA→ZH but gated):

```bash
# 1. Accept license at https://huggingface.co/SakuraLLM/Sakura-7B-Qwen2.5-v1.0
huggingface-cli login
# 2. Edit backend/scripts/download_models.sh → add the Sakura repo
# 3. Edit backend/app/config.py → mt_dirname = "sakura-gguf", mt_quant = "q4_k_m"
# 4. bash backend/scripts/download_models.sh
# 5. bash backend/scripts/quantize_mt.sh
# 6. launchctl kickstart -k gui/$(id -u)/com.voicetranslate.backend
```
