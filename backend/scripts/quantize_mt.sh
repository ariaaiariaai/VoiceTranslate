#!/usr/bin/env bash
# Convert the MT model (default: Qwen2.5-7B-Instruct) into GGUF Q4_K_M for llama.cpp.
# For Sakura-7B-Qwen2.5-v1.0 instead:
#   - Run scripts/download_models.sh (after `huggingface-cli login` and accepting the license)
#   - Then: MODELS_DIR_SRC=sakura-base MODELS_DIR_DST=sakura-gguf bash quantize_mt.sh
set -euo pipefail

MODELS_DIR="${HOME}/Models"
MODELS_DIR_SRC="${MODELS_DIR_SRC:-qwen2.5-7b-instruct}"
MODELS_DIR_DST="${MODELS_DIR_DST:-qwen2.5-7b-instruct-gguf}"
QTYPE="${1:-q4_k_m}"

SRC_DIR="${MODELS_DIR}/${MODELS_DIR_SRC}"
DST_DIR="${MODELS_DIR}/${MODELS_DIR_DST}"
LLAMA_DIR="${MODELS_DIR}/llama.cpp"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "ERROR: ${SRC_DIR} does not exist. Run scripts/download_models.sh first." >&2
  exit 1
fi

if [[ ! -d "${LLAMA_DIR}" ]]; then
  echo "ERROR: ${LLAMA_DIR} does not exist. Clone llama.cpp first." >&2
  exit 1
fi

mkdir -p "${DST_DIR}"
FP16_GGUF="${DST_DIR}/fp16.gguf"
QUANT_GGUF="${DST_DIR}/${QTYPE}.gguf"

# Activate venv if present so we can use its python for the conversion script.
if [[ -f "/Users/ariaai/Claude/Projects/VoiceTranslate/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "/Users/ariaai/Claude/Projects/VoiceTranslate/.venv/bin/activate"
fi

# 1) HF → fp16 GGUF
if [[ ! -f "${FP16_GGUF}" ]]; then
  echo "[$(date +%H:%M:%S)] Converting HF → fp16 GGUF (this can take ~5 min for 7B)"
  python3 "${LLAMA_DIR}/convert_hf_to_gguf.py" \
    "${SRC_DIR}" \
    --outfile "${FP16_GGUF}" \
    --outtype f16
else
  echo "fp16 GGUF already exists, skipping HF conversion"
fi

# 2) Quantise
if [[ ! -f "${QUANT_GGUF}" ]]; then
  echo "[$(date +%H:%M:%S)] Quantising fp16 → ${QTYPE}"
  "${LLAMA_DIR}/build/bin/llama-quantize" "${FP16_GGUF}" "${QUANT_GGUF}" "${QTYPE}"
else
  echo "${QTYPE} GGUF already exists, skipping quantisation"
fi

echo "[$(date +%H:%M:%S)] Quantisation complete."
du -sh "${DST_DIR}"/*.gguf
