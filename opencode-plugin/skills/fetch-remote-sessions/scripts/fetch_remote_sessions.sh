#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <host> [local-dev-directory]" >&2
  exit 2
fi

HOST="$1"
LOCAL_DEV_DIR="${2:-${LOCAL_DEV_DIR:-$HOME/coding}}"
LOCAL_DEV_DIR="${LOCAL_DEV_DIR%/}"

LOCAL_CLAUDE_PROJECTS="${LOCAL_CLAUDE_PROJECTS:-$HOME/.claude/projects}"
LOCAL_CODEX_SESSIONS="${LOCAL_CODEX_SESSIONS:-$HOME/.codex/sessions}"

REMOTE_CLAUDE_PROJECTS='~/.claude/projects'
REMOTE_CODEX_SESSIONS='~/.codex/sessions'
REMOTE_SANDBOX_PREFIX='/home/sandbox-user/project'

encode_path_for_claude_root() {
  local raw="$1"
  printf '%s' "$raw" | sed 's#/#-#g'
}

normalize_jsonl_paths_under() {
  local root="$1"
  local old_prefix='/home/sandbox-user/project/'
  local new_prefix="${LOCAL_DEV_DIR}/"

  if [[ ! -d "$root" ]]; then
    return 0
  fi

  while IFS= read -r -d '' file; do
    sed -i "s#${old_prefix}#${new_prefix}#g" "$file"
  done < <(find "$root" -type f -name '*.jsonl' -print0)
}

mkdir -p "$LOCAL_CLAUDE_PROJECTS" "$LOCAL_CODEX_SESSIONS"

mapfile -t remote_claude_dirs < <(
  ssh "$HOST" "[ -d ${REMOTE_CLAUDE_PROJECTS} ] && find ${REMOTE_CLAUDE_PROJECTS} -mindepth 1 -maxdepth 1 -type d -printf '%f\\n' | sort || true"
)

mapfile -t remote_codex_days < <(
  ssh "$HOST" "[ -d ${REMOTE_CODEX_SESSIONS} ] && find ${REMOTE_CODEX_SESSIONS} -mindepth 3 -maxdepth 3 -type d -printf '%P\\n' | sort || true"
)

if [[ ${#remote_claude_dirs[@]} -eq 0 && ${#remote_codex_days[@]} -eq 0 ]]; then
  echo "No remote session directories discovered under ${REMOTE_CLAUDE_PROJECTS} or ${REMOTE_CODEX_SESSIONS}."
  exit 0
fi

echo "Remote host: ${HOST}"
echo "Local dev dir: ${LOCAL_DEV_DIR}"
echo "Discovered Claude project roots: ${#remote_claude_dirs[@]}"
echo "Discovered Codex date directories: ${#remote_codex_days[@]}"

remote_encoded_prefix="$(encode_path_for_claude_root "$REMOTE_SANDBOX_PREFIX")"

claude_copied=0
for remote_dir in "${remote_claude_dirs[@]}"; do
  [[ -z "$remote_dir" ]] && continue

  local_dir="$remote_dir"
  if [[ "$remote_dir" == "${remote_encoded_prefix}-"* ]]; then
    suffix="${remote_dir#"${remote_encoded_prefix}-"}"
    local_project_path="${LOCAL_DEV_DIR}/${suffix}"
    local_dir="$(encode_path_for_claude_root "$local_project_path")"
  fi

  mkdir -p "${LOCAL_CLAUDE_PROJECTS}/${local_dir}"
  scp -r "$HOST:${REMOTE_CLAUDE_PROJECTS}/${remote_dir}/." "${LOCAL_CLAUDE_PROJECTS}/${local_dir}/"
  normalize_jsonl_paths_under "${LOCAL_CLAUDE_PROJECTS}/${local_dir}"
  claude_copied=$((claude_copied + 1))
done

codex_copied=0
for rel_day in "${remote_codex_days[@]}"; do
  [[ -z "$rel_day" ]] && continue

  local_parent="${LOCAL_CODEX_SESSIONS}/$(dirname "$rel_day")"
  mkdir -p "$local_parent"
  scp -r "$HOST:${REMOTE_CODEX_SESSIONS}/${rel_day}" "$local_parent/"
  normalize_jsonl_paths_under "${LOCAL_CODEX_SESSIONS}/${rel_day}"
  codex_copied=$((codex_copied + 1))
done

echo "Copied Claude project roots: ${claude_copied}"
echo "Copied Codex date directories: ${codex_copied}"
