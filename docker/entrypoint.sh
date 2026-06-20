#!/bin/sh
set -eu

DATA_DIR="${APP_DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"

if [ -z "${DATABASE_URL:-}" ]; then
  export DATABASE_URL="sqlite:////data/text_to_sql_admin.db"
fi

# Default the machine user as owner/admin when not explicitly configured.
if [ -z "${OWNER_USERNAME:-}" ]; then
  OWNER_USERNAME="$(id -un 2>/dev/null || echo "")"
  if [ -n "$OWNER_USERNAME" ]; then
    export OWNER_USERNAME
  fi
fi

if [ -z "${AUTH_ADMIN_USERS:-}" ] && [ -n "${OWNER_USERNAME:-}" ]; then
  export AUTH_ADMIN_USERS="$OWNER_USERNAME"
fi

ENV_FILE="${DATA_DIR}/.env"
if [ -z "${FERNET_KEY:-}" ] && [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC2046
  export FERNET_KEY="$(grep -E '^FERNET_KEY=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
fi

if [ -z "${FERNET_KEY:-}" ]; then
  FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  export FERNET_KEY
  printf 'FERNET_KEY=%s\n' "$FERNET_KEY" >> "$ENV_FILE"
  echo "Generated persistent FERNET_KEY in ${ENV_FILE}" >&2
fi

exec "$@"
