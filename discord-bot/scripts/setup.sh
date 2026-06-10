#!/usr/bin/env bash
# One-time setup: clone verialabs/ctf-agent and build Docker sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor/ctf-agent"

echo "==> ctf-discord-bot setup"
echo "Root: $ROOT"

if ! command -v git >/dev/null; then
  echo "git is required"
  exit 1
fi
if ! command -v uv >/dev/null; then
  echo "uv is required: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
if ! command -v docker >/dev/null; then
  echo "docker is required for ctf-agent sandboxes"
  exit 1
fi

mkdir -p "$ROOT/vendor"

if [ ! -d "$VENDOR/.git" ]; then
  echo "==> Cloning verialabs/ctf-agent"
  git clone https://github.com/verialabs/ctf-agent.git "$VENDOR"
else
  echo "==> Updating verialabs/ctf-agent"
  git -C "$VENDOR" pull --ff-only
fi

echo "==> Installing ctf-agent dependencies (Python 3.14+)"
cd "$VENDOR"
uv sync

echo "==> Building Docker sandbox image (ctf-sandbox)"
docker build -f sandbox/Dockerfile.sandbox -t ctf-sandbox .

echo "==> Installing discord bot"
cd "$ROOT"
uv sync

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env — edit DISCORD_TOKEN, CTFD_URL, CTFD_TOKEN, ALLOWED_DISCORD_USER_IDS"
fi

# Share LLM + CTFd vars with ctf-agent
grep -E '^(CTFD_|ANTHROPIC_|OPENAI_|GEMINI_)' "$ROOT/.env" > "$VENDOR/.env" 2>/dev/null || true
if [ ! -s "$VENDOR/.env" ]; then
  cp "$VENDOR/.env.example" "$VENDOR/.env"
  echo "Edit $VENDOR/.env with CTFD_URL, CTFD_TOKEN, and at least one LLM API key"
fi

mkdir -p "$VENDOR/challenges" "$ROOT/data/logs"

echo ""
echo "Setup complete."
echo "1. Edit $ROOT/.env"
echo "2. Run: cd $ROOT && uv run ctf-discord-bot"
echo "3. In Discord: /list, /solve <id>, /coordinator start"
