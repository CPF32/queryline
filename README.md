# Queryline

**Queryline** is a text-to-SQL analytics app. Connect a database, ask questions in plain English, and get SQL, results, and charts back. It ships as a **desktop app** (Windows, macOS, Linux) or as a **Docker container** for team deployments behind your reverse proxy.

[Download the latest desktop release](https://github.com/CPF32/text-to-sql-analytics/releases/latest)

---

## What it does

1. **Connect data sources** — SQLite, PostgreSQL, MySQL, or SQL Server (read-only connections recommended).
2. **Import schema** — introspect tables, views, and relationships so the model knows your data model.
3. **Chat** — ask natural-language questions; the app generates SQL, runs it, and can render charts.
4. **Admin** — manage data sources, schema metadata, glossary terms, few-shot examples, users, and LLM settings.

Supported LLM backends:

| Provider | Use case |
|----------|----------|
| **Ollama** (local) | On-prem / air-gapped; no API key |
| **Anthropic** (Claude) | Cloud API |
| **Google Gemini** | Cloud API |

---

## How it works

```
┌─────────────────────────────────────────────────────────┐
│  React UI (chat, admin, settings)                       │
└──────────────────────────┬──────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────┐
│  Python / Flask API                                     │
│  · Auth · Data sources · Schema · SQL generation        │
│  · Query execution (read-only) · Conversations          │
└──────────┬─────────────────────────────┬──────────────┘
           │                             │
┌──────────▼──────────┐       ┌──────────▼──────────┐
│  Metadata SQLite DB │       │  Your analytics DBs │
│  (users, schema,    │       │  (Postgres, MySQL,  │
│   connections)      │       │   SQLite, MSSQL)    │
└─────────────────────┘       └─────────────────────┘
```

- **Metadata database** — stores users, encrypted connection strings, imported schema, conversations, and query log. Separate from the databases you query.
- **SQL generation** — an LLM produces SQL using your schema, glossary, and examples; execution is restricted to read-only `SELECT` statements.
- **Authentication** — desktop installs verify your **OS login password**; server installs use **SSO headers** from a reverse proxy (`X-Remote-User`).

---

## Choose your deployment

| Scenario | Setup |
|----------|--------|
| One analyst on their laptop | [Desktop app](#desktop-app) |
| IT-hosted, many users in a browser | [Docker](#docker-server) |
| Local development | [Developer setup](#developer-setup) |

---

## Desktop app

Best for individual analysts. The packaged app includes the UI, Python backend, and auto-update from GitHub Releases.

### Install

1. Download the installer for your OS from [GitHub Releases](https://github.com/CPF32/text-to-sql-analytics/releases/latest).
2. Run the installer. You'll get **Queryline** in your applications folder with the Queryline icon (not the generic Electron dev icon).
3. On first launch, a short **setup wizard** asks whether to self-host **Ollama** (optional — you can configure LLM settings later in Admin).
4. Sign in with your **computer username and password**.

The OS user who installs the app becomes the **owner admin** and cannot be demoted.

### Auto-updates

Installed apps check GitHub on startup. When a newer version is available, a banner offers **Update** or **Later** (dismissed until the next app launch).

### Data location

App data (settings, metadata DB, encryption key) is stored per user:

| OS | Location |
|----|----------|
| macOS | `~/Library/Application Support/text-to-sql-analytics/` |
| Windows | `%LOCALAPPDATA%\text-to-sql-analytics\` |
| Linux | `~/.local/share/text-to-sql-analytics/` |

### Build from source

```bash
git clone https://github.com/CPF32/text-to-sql-analytics.git
cd text-to-sql-analytics
npm install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm run desktop:pack
```

Installers are written to `release/`. See [DEPLOY.md](DEPLOY.md) for publishing releases and code signing.

---

## Docker server

Best for company networks: one container (plus optional Ollama sidecar) serves the app on port **5001** for browsers on your LAN.

### Quick start

```bash
git clone https://github.com/CPF32/text-to-sql-analytics.git
cd text-to-sql-analytics
cp docker.env.example .env
# Edit .env — set AUTH_ADMIN_USERS, SECRET_KEY, and LLM settings

docker compose --profile ollama up -d --build
```

Open http://localhost:5001

Pull a model into the Ollama sidecar (first time only):

```bash
docker compose exec ollama ollama pull llama3.1
```

### Authentication

Docker defaults to `AUTH_MODE=trusted_proxy`. Put nginx or Apache in front, authenticate users (LDAP/Kerberos/SSO), and forward the username:

```nginx
proxy_set_header X-Remote-User $remote_user;
proxy_pass http://127.0.0.1:5001;
```

Users listed in `AUTH_ADMIN_USERS` get access to the Admin UI. The Linux user running the container is the default owner admin if not otherwise configured.

### Without Ollama

Use a cloud LLM in `.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
```

Then `docker compose up -d --build` (no `--profile ollama`).

### Persistent data

| Volume | Contents |
|--------|----------|
| `app-data` | Metadata DB, Fernet key, runtime settings |
| `ollama-data` | Downloaded local models (when using Ollama profile) |

Back up `app-data` — it holds encrypted database passwords.

More detail: [DEPLOY.md](DEPLOY.md)

---

## Developer setup

For hacking on the codebase locally:

```bash
git clone https://github.com/CPF32/text-to-sql-analytics.git
cd text-to-sql-analytics

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

npm install
cp .env.example .env   # add LLM keys as needed
```

**Browser + hot reload:**

```bash
npm run start:browser
```

Opens the UI at http://127.0.0.1:3000 with the API on port 5001.

**Desktop dev (Electron):**

```bash
npm run start:desktop
```

Dev mode uses the Electron binary directly; use `npm run desktop:pack` to test the branded installer.

Further reference: [RUNBOOK.md](RUNBOOK.md), [CONTRACTS.md](CONTRACTS.md)

---

## First-time admin checklist

After sign-in as an admin:

1. **Admin → LLM settings** — choose Ollama, Anthropic, or Gemini and test the connection.
2. **Admin → Add data source** — connect a read-only database user.
3. **Import schema** — select tables/views for the model to use.
4. Optional: add **glossary terms** and **SQL examples** to improve accuracy.
5. Return to **Chat** and ask a question.

---

## Project structure

```
text-to-sql-analytics/
├── app/              # Flask API, auth, SQL generation, adapters
├── src/              # React UI
├── electron/         # Desktop shell + auto-updater
├── desktop/          # Packaged backend entrypoint
├── docker/           # Container entrypoint
├── build/            # App icons for desktop installers
├── public/           # Favicon and in-app icon
└── sqlite_databases/ # Sample SQLite schemas for testing
```

---

## License

See repository license file. If none is present, contact the maintainer for terms of use.
