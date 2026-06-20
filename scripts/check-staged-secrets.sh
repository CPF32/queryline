#!/usr/bin/env bash
# Fail if staged files look like they contain secrets or local env files.
set -euo pipefail

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

staged="$(git diff --cached --name-only --diff-filter=ACMR)"
if [ -z "$staged" ]; then
  exit 0
fi

is_blocked_path() {
  case "$1" in
    .env|docker.env) return 0 ;;
    .env.example|docker.env.example) return 1 ;;
    .env.*) return 0 ;;
    *.pem|*.key) return 0 ;;
    *) return 1 ;;
  esac
}

blocked=""
while IFS= read -r file; do
  [ -n "$file" ] || continue
  if is_blocked_path "$file"; then
    blocked="${blocked}${file}"$'\n'
  fi
done <<< "$staged"

if [ -n "$blocked" ]; then
  echo "error: refusing to commit local env or key files:" >&2
  printf '%s' "$blocked" >&2
  echo "These paths belong in .gitignore — keep secrets in .env locally only." >&2
  exit 1
fi

patterns=(
  'GEMINI_API_KEY=[^y][^o]'
  'ANTHROPIC_API_KEY=sk-ant-'
  'sk-ant-[A-Za-z0-9]{20,}'
  'AIzaSy[A-Za-z0-9_-]{20,}'
  'AQ\.[A-Za-z0-9_-]{20,}'
)

while IFS= read -r file; do
  [ -n "$file" ] || continue
  case "$file" in
    scripts/check-staged-secrets.sh|.githooks/pre-commit) continue ;;
  esac
  content="$(git show ":$file" 2>/dev/null || true)"
  [ -n "$content" ] || continue
  for pattern in "${patterns[@]}"; do
    if echo "$content" | grep -Eq "$pattern"; then
      echo "error: staged file may contain a secret: $file" >&2
      echo "Remove the secret, use .env.example placeholders, or unstage the file." >&2
      exit 1
    fi
  done
done <<< "$staged"

exit 0
