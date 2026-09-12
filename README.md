# VoiceTranslate

Real-time Japanese → Traditional Chinese (Hong Kong) translation PWA for iPhone, powered by a Mac mini M4 backend.

## What it does

Capture Japanese audio on iPhone → stream over WebSocket via Cloudflare Tunnel to a FastAPI backend on Mac mini → run a VAD → STT (Whisper) → MT (Sakura-7B) → TTS (MeloTTS) pipeline → return Chinese text and Mandarin audio. Frontend served from Cloudflare Pages.

## Architecture

```
iPhone Safari PWA
    │ HTTPS / WSS
    ▼
Cloudflare Edge (Pages + Tunnel)
    │
    ▼
┌──────────────────────┐
│ Mac mini M4 (屋企)    │
│ FastAPI + uvicorn    │
│ - Silero VAD         │
│ - faster-whisper     │
│ - llama.cpp MLX      │
│ - MeloTTS            │
│ - OpenCC + zh-HK dict │
└──────────────────────┘
```

See `docs/architecture.md` for details.

## Stack

- **Frontend**: Svelte 5 + Vite + TypeScript, PWA via vite-plugin-pwa
- **Backend**: FastAPI + uvicorn (uvloop) + faster-whisper + llama.cpp MLX + MeloTTS
- **Tunnel**: Cloudflare named tunnel (cloudflared)
- **Hosting**: Cloudflare Pages (frontend), Mac mini (backend)
- **Auto-start**: launchd LaunchAgents

## Setup

See `docs/operations.md` for full operational guide.

### Quick start (after Phase 1 setup)

```bash
# Backend
cd backend && source ../.venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop

# Frontend
cd frontend && pnpm dev
```

## Repository layout

```
backend/         FastAPI service
frontend/        Svelte 5 PWA
deploy/          launchd plists, cloudflared config, helper scripts
docs/            architecture, operations, troubleshooting
.github/         CI / Pages deploy workflows
```

## Models

Stored outside the repo under `~/Models/`:

- `~/Models/llama.cpp/` — llama.cpp source + MLX build
- `~/Models/kotoba-whisper-v2.2/` — STT base
- `~/Models/kotoba-whisper-v2.2-ct2-int8/` — STT converted (CTranslate2 int8)
- `~/Models/sakura-base/` — MT base
- `~/Models/sakura-gguf/q4_k_m.gguf` — MT quantised (Q4_K_M)

## Cost

~$5/mo electricity. No recurring API costs.
