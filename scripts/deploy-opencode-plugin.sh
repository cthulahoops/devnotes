#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT="${1:-$HOME/devnotes}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SRC="$REPO_ROOT/opencode-plugin"
TARGET_PLUGIN_LINK="$TARGET_ROOT/opencode-plugin"
TARGET_OPENCODE_DIR="$TARGET_ROOT/.opencode"

if [ ! -d "$PLUGIN_SRC" ]; then
  echo "Missing plugin source directory: $PLUGIN_SRC" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT"
mkdir -p "$TARGET_OPENCODE_DIR"

ln -sfn "$PLUGIN_SRC" "$TARGET_PLUGIN_LINK"

link_component() {
  local component="$1"
  local src="$TARGET_PLUGIN_LINK/$component"
  local dst="$TARGET_OPENCODE_DIR/$component"

  if [ ! -d "$src" ]; then
    return 0
  fi

  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    echo "Refusing to replace non-symlink path: $dst" >&2
    exit 1
  fi

  ln -sfn "$src" "$dst"
}

link_component "skills"
link_component "commands"
link_component "agents"
link_component "plugins"

echo "Deployed plugin source via symlinks:"
echo "  repo source: $PLUGIN_SRC"
echo "  target root: $TARGET_ROOT"
echo "  mounted at:  $TARGET_OPENCODE_DIR"
