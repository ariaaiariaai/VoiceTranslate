#!/usr/bin/env bash
# Convert kotoba-whisper-v2.2 (HF transformers format) into CTranslate2 int8 weights
# so faster-whisper can use them with low RAM and fast CPU inference.
set -euo pipefail

MODELS_DIR="${HOME}/Models"
SRC_DIR="${MODELS_DIR}/kotoba-whisper-v2.2"
DST_DIR="${MODELS_DIR}/kotoba-whisper-v2.2-ct2-int8"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "ERROR: ${SRC_DIR} does not exist. Run scripts/download_models.sh first." >&2
  exit 1
fi

if [[ -f "${DST_DIR}/model.bin" ]]; then
  echo "CTranslate2 model already exists at ${DST_DIR}, skipping"
  exit 0
fi

echo "[$(date +%H:%M:%S)] Converting kotoba-whisper-v2.2 → CTranslate2 int8_float16"
echo "[$(date +%H:%M:%S)] Source: ${SRC_DIR}"
echo "[$(date +%H:%M:%S)] Destination: ${DST_DIR}"

# Prefer the python from the project venv if available.
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "/Users/ariaai/Claude/Projects/VoiceTranslate/.venv/bin/python" ]]; then
  PYTHON_BIN="/Users/ariaai/Claude/Projects/VoiceTranslate/.venv/bin/python"
fi

ct2-transformers-converter \
  --model "${SRC_DIR}" \
  --output_dir "${DST_DIR}" \
  --quantization int8_float16 \
  --copy_files tokenizer.json preprocessor_config.json \
  --force

echo "[$(date +%H:%M:%S)] Conversion complete."
du -sh "${DST_DIR}"
