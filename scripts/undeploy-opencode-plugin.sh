#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT="${1:-$HOME/devnotes}"
TARGET_OPENCODE_DIR="$TARGET_ROOT/.opencode"
TARGET_PLUGIN_LINK="$TARGET_ROOT/opencode-plugin"

unlink_component() {
  local component="$1"
  local path="$TARGET_OPENCODE_DIR/$component"
  if [ -L "$path" ]; then
    rm "$path"
  fi
}

unlink_component "skills"
unlink_component "commands"
unlink_component "agents"
unlink_component "plugins"

if [ -L "$TARGET_PLUGIN_LINK" ]; then
  rm "$TARGET_PLUGIN_LINK"
fi

echo "Removed deployed plugin symlinks from $TARGET_ROOT"
