#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBNET_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "${SUBNET_DIR}"
export PYTHONPATH="${SUBNET_DIR}:${PYTHONPATH:-}"

"${PYTHON_BIN}" neurons/validator.py \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --subtensor.network local \
  --netuid 2 \
  --logging.debug