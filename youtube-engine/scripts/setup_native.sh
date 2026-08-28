#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

echo "=== AutoTube native setup ==="
echo "Project: $PROJECT_DIR"

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  ffmpeg \
  fonts-dejavu-core

if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  echo "Installing uv..."
  installer="$(mktemp)"
  curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
  sh "$installer"
  rm -f "$installer"
fi

export PATH="$HOME/.local/bin:$PATH"
UV_BIN="$(command -v uv)"
echo "Using uv: $UV_BIN"

uv python install 3.11
uv venv --clear --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

mkdir -p data secrets voices
.venv/bin/python -m piper.download_voices --data-dir voices en_US-ljspeech-medium

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env from .env.example"
else
  echo ".env already exists; leaving it unchanged"
fi

printf '\n=== Versions ===\n'
.venv/bin/python --version
ffmpeg -version | head -1
.venv/bin/python -c 'import piper; print("Piper import: OK")'
.venv/bin/python -c 'from google import genai; print("Gemini SDK import: OK")'

printf '\n=== Resources after setup ===\n'
free -h
df -h "$PROJECT_DIR"

printf '\nSetup complete. Next: add GEMINI_API_KEY to .env, then run the local generation test.\n'
