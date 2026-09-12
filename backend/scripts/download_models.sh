#!/usr/bin/env bash
# Download ML models from HuggingFace into ~/Models/.
# Run once during initial setup; re-run only when model versions change.
set -euo pipefail

MODELS_DIR="${HOME}/Models"
mkdir -p "${MODELS_DIR}"

# Use a recent snapshot of huggingface_hub; no auth required for these repos.
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-0}"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# 1) Japanese STT — distilled Whisper, kotoba-tech v2.2 (HF: kotoba-tech/kotoba-whisper-v2.2)
KOTOBA_DIR="${MODELS_DIR}/kotoba-whisper-v2.2"
if [[ ! -f "${KOTOBA_DIR}/config.json" ]]; then
  log "Downloading kotoba-whisper-v2.2 (~1.4 GB) → ${KOTOBA_DIR}"
  huggingface-cli download kotoba-tech/kotoba-whisper-v2.2 \
    --local-dir "${KOTOBA_DIR}" \
    --exclude "*.bin" "*.msgpack" "*.h5" "*.onnx" "*.onnx_data" "training_args.bin" "*.tflite" "*.msgpack" "flax_model.msgpack" "tf_model.h5" "rust_model.ot" "*.ckpt" "*.pt" "*.pth"
else
  log "kotoba-whisper-v2.2 already present, skipping"
fi

# 2) Translation — Sakura-7B-Qwen2.5-v1.0 base (full precision, will quantise separately)
SAKURA_DIR="${MODELS_DIR}/sakura-base"
if [[ ! -f "${SAKURA_DIR}/config.json" ]]; then
  log "Downloading Sakura-7B-Qwen2.5-v1.0 (~14 GB) → ${SAKURA_DIR}"
  huggingface-cli download SakuraLLM/Sakura-7B-Qwen2.5-v1.0 \
    --local-dir "${SAKURA_DIR}" \
    --exclude "*.bin" "*.msgpack" "*.h5" "flax_model.msgpack" "tf_model.h5" "rust_model.ot" "*.ckpt"
else
  log "Sakura base already present, skipping"
fi

# 3) Silero VAD — downloaded automatically on first instantiation of the Python wrapper.
#    We just leave a marker so the script is idempotent.
log "Silero VAD will download on first backend start (~2 MB)."

# 4) MeloTTS — downloaded automatically on first instantiation.
#    We just leave a marker so the script is idempotent.
log "MeloTTS will download on first backend start (~300 MB)."

log "All model downloads complete."
log "Next step: run scripts/convert_kotoba.sh and scripts/quantize_sakura.sh"
