#!/usr/bin/env bash
# HowlForge - one-shot setup for a small VPS (Ubuntu/Debian, ARM or x86_64).
#
#   * installs Docker Engine + compose plugin (if missing)
#   * clones the repo, prompts for .env, builds and starts the stack
#
# Run as a sudo-capable user:
#   bash setup.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/adrian-wulf/howlforge.git}"
APP_DIR="${APP_DIR:-$HOME/howlforge}"
BRANCH="${BRANCH:-main}"
COMPOSE="docker compose"

say()  { printf '\033[36m[howlforge]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || {
  say "Docker not found - installing Docker Engine..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
  say "Docker installed. A logout/login may be needed for group membership."
}

docker compose version >/dev/null 2>&1 || COMPOSE="docker-compose"

if [ ! -d "$APP_DIR/.git" ]; then
  say "Cloning repo into $APP_DIR..."
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  say "Updating existing repo in $APP_DIR..."
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  say "Created .env from template. Edit it now:"
  say "   nano $APP_DIR/.env"
  say "Set at least: HOWLFORGE_PANEL_PASSWORD and (for the bot) TELEGRAM_BOT_TOKEN."
  read -r -p "Press Enter when .env is ready..." _
else
  say ".env already present - keeping it."
fi

mkdir -p vault
# Ensure the vault is owned by the current user (not root), so local edits work.
chown -R "$(id -u)":"$(id -g)" vault 2>/dev/null || true

say "Building and starting services (api + bot)..."
sudo -E env "PATH=$PATH" $COMPOSE -f deploy/oracle/docker-compose.prod.yml up -d --build

say "Done."
say "  Panel:   http://<server-ip>:8000   (or HTTPS via Caddy if you add a domain)"
say "  Logs:    sudo docker compose -f $APP_DIR/deploy/oracle/docker-compose.prod.yml logs -f"
