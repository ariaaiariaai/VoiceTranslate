#!/usr/bin/env bash
# Switch the MT model to Sakura-7B-Qwen2.5-v1.0 (specialised JA→ZH).
#
# Prereqs:
#   1. Accept license at https://huggingface.co/SakuraLLM/Sakura-7B-Qwen2.5-v1.0
#   2. huggingface-cli login  (paste token from https://huggingface.co/settings/tokens)
#
# This script will:
#   - Download the full Sakura model to ~/Models/sakura-base (~14 GB)
#   - Convert HF → fp16 GGUF (~14 GB)
#   - Quantise fp16 → Q4_K_M (~4.5 GB)
#   - Tell the backend to use it (edit config.py: mt_dirname = "sakura-gguf")
#
# Sakura outputs Simplified Chinese by default. The pipeline runs OpenCC s2twp
# + zh-HK substitutions afterwards, so the final output is still Traditional
# Chinese (HK).
set -euo pipefail

if ! command -v huggingface-cli >/dev/null 2>&1; then
  echo "Installing huggingface-cli..."
  pip install --user huggingface_hub[cli]
fi

echo "→ Logging into Hugging Face..."
huggingface-cli login

SAKURA_DIR="${HOME}/Models/sakura-base"
if [[ ! -d "${SAKURA_DIR}" ]]; then
  echo "→ Downloading Sakura-7B-Qwen2.5-v1.0 (~14 GB)..."
  mkdir -p "${SAKURA_DIR}"
  huggingface-cli download SakuraLLM/Sakura-7B-Qwen2.5-v1.0 \
    --local-dir "${SAKURA_DIR}" \
    --exclude "*.bin" "*.msgpack" "*.h5" "flax_model.msgpack" "tf_model.h5" \
    "rust_model.ot" "*.ckpt"
else
  echo "Sakura base already present at ${SAKURA_DIR}"
fi

echo "→ Quantising to GGUF Q4_K_M..."
MODELS_DIR_SRC="${SAKURA_DIR##*/}" \
  MODELS_DIR_DST="sakura-gguf" \
  bash "$(dirname "$0")/quantize_mt.sh"

echo
echo "✅ Sakura-7B GGUF ready at ~/Models/sakura-gguf/q4_k_m.gguf"
echo
echo "To switch the backend to Sakura, edit backend/app/config.py:"
echo "  mt_dirname: str = \"sakura-gguf\"    # was \"qwen2.5-7b-instruct-gguf\""
echo
echo "Then restart:"
echo "  launchctl kickstart -k gui/\$(id -u)/com.voicetranslate.backend"
