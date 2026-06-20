# Deployment Guide

Text-to-SQL Analytics supports two deployment models:

1. **Desktop app** — downloadable single-user install (Windows, macOS, Linux)
2. **Docker server** — shared Linux server deployment for a company network

---

## Desktop app (single user)

Best for analysts running the app on their own machine. Sign-in verifies the computer login password (`AUTH_MODE=system`).

### Build installers

```bash
npm install
npm run desktop:pack
```

Outputs land in `release/`:

| Platform | Artifact |
|----------|----------|
| macOS | `.dmg`, `.zip` |
| Windows | NSIS installer |
| Linux | `.AppImage`, `.deb` |

### What the desktop bundle includes

- Electron shell
- PyInstaller-bundled Python backend
- Built React UI
- User data stored under the OS app-support directory (metadata DB, Fernet key, settings)

### Desktop configuration

On first launch the app creates a per-user data directory and stable `FERNET_KEY`. Set LLM keys in **Admin → LLM Settings**, or pre-seed `LLM_PROVIDER=ollama` with a local Ollama install.

```env
AUTH_MODE=system
AUTH_ADMIN_USERS=YOURDOMAIN\your.username
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

---

## Docker server (shared Linux deployment)

Best for IT-hosted deployments where many users access the app from a browser on the company network.

### Quick start

```bash
cp docker.env.example .env
# Edit .env: AUTH_ADMIN_USERS, SECRET_KEY, LLM settings
# Docker Compose reads .env for ${VAR} substitution below

docker compose --profile ollama up -d --build
```

Open http://localhost:5001 (or your host port).

Pull an Ollama model on first run:

```bash
docker compose exec ollama ollama pull llama3.1
```

### Without the Ollama sidecar

Use a cloud LLM instead:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
```

Then:

```bash
docker compose up -d --build
```

### Image contents

The multi-stage `Dockerfile`:

1. Builds the React frontend (`npm run build`)
2. Installs Python dependencies + gunicorn
3. Serves API + static UI on port **5001**
4. Persists app data in the **`/data`** volume (metadata DB, Fernet key)

### Authentication behind a reverse proxy

For multi-user server deployments, set:

```env
AUTH_MODE=trusted_proxy
AUTH_ADMIN_USERS=YOURDOMAIN\admin1,YOURDOMAIN\admin2
```

Configure nginx (or Apache) to authenticate users against AD/LDAP/Kerberos and forward the username:

```nginx
location / {
    auth_gssapi on;  # or your SSO module
    proxy_set_header X-Remote-User $remote_user;
    proxy_pass http://127.0.0.1:5001;
}
```

Regular users can chat; only `AUTH_ADMIN_USERS` see the Admin UI.

### Persistent data

| Mount | Purpose |
|-------|---------|
| `app-data` volume → `/data` | Metadata SQLite DB, Fernet key, runtime `.env` |
| `ollama-data` volume (optional) | Downloaded local models |

`FERNET_KEY` is auto-generated on first boot and saved to `/data/.env` if not provided. **Back up the `app-data` volume** — it holds encrypted connector passwords.

### Production notes

- Default metadata store is SQLite on the volume (one gunicorn worker). For heavier multi-user load, point `DATABASE_URL` at PostgreSQL.
- MSSQL connectors need the Microsoft ODBC driver on the host image; PostgreSQL/MySQL/SQLite work out of the box.
- Put TLS termination on the reverse proxy, not inside the app container.

### Useful commands

```bash
# Build only
docker compose build

# Logs
docker compose logs -f app

# Restart after .env changes
docker compose up -d --build

# Stop
docker compose down
```

---

## Choosing a deployment

| Need | Use |
|------|-----|
| One analyst, their laptop | Desktop (`npm run desktop:pack`) |
| IT-hosted, many users, browser access | Docker + reverse proxy SSO |
| Air-gapped / no cloud LLM | Docker `--profile ollama` or desktop + local Ollama |
| Quick local dev | `python run.py` after `npm run build` (see RUNBOOK.md) |

Both paths share the same codebase — only packaging and auth configuration differ.
