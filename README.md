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
| **OpenAI** (ChatGPT) | Cloud API |
| **Anthropic** (Claude) | Cloud API |
| **Google Gemini** | Cloud API |

---

## Data source requirements

Use a **read-only** database login for every connection. The app blocks write/DDL SQL at runtime and verifies grants when you save a connection. Step-by-step grant scripts: [docs/READONLY_SETUP.md](docs/READONLY_SETUP.md).

| Engine | What you need | Notes |
|--------|---------------|-------|
| **SQLite** | Path to a `.db` / `.sqlite` file on the machine running the app | Opens the file in read-only mode (`mode=ro`, `PRAGMA query_only`). Best for local files and desktop use. On desktop, use the file picker to choose the database. |
| **PostgreSQL** | Host, port, database, username, password | Server must be reachable from the app. Python driver (`psycopg2`) is bundled in desktop builds. Use SSL (`require` or `verify-full`) over a network. Create a login with `SELECT` only — no `INSERT`, `UPDATE`, `DELETE`, or DDL. |
| **MySQL / MariaDB** | Host, port, database, username, password | Server must be reachable from the app. Python driver (`PyMySQL`) is bundled in desktop builds. Use SSL when connecting over a network. Grant `SELECT` only on the target schema. |
| **SQL Server** | Host, port, database, authentication | Server must be reachable from the app. Requires a **system ODBC driver** (for example **ODBC Driver 18 for SQL Server**) installed on the machine running the app — this is separate from the Python package and is not bundled with the desktop installer. Use SQL authentication or Windows/AD auth (`auth_mode: windows`). Map the login to `db_datareader` only. |

**Desktop vs dev:** All four engines appear in the Add Data Source wizard. Packaged desktop builds include the Python drivers for PostgreSQL, MySQL, and SQLite; SQL Server still needs the ODBC driver installed on the OS.

**Docker:** All engines are available in the container image. SQL Server connections from Docker still require network access to your SQL Server host and an ODBC driver inside the container (included in the image).

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

### Unsigned builds (read this first)

**GitHub release installers are not code-signed or notarized.** This project does not ship with Apple Developer ID, Windows Authenticode, or other commercial signing certificates. Your operating system may block or warn about the download — that is expected, not a sign that the file is corrupted.

The app is open source; you can inspect the code and [build from source](#build-from-source) if you prefer. If you trust the project and want to use the pre-built release, follow the install steps below and **allow the app through your OS security prompts**.

| OS | What you may see | How to install anyway |
|----|------------------|------------------------|
| **macOS** | “Queryline is damaged and can’t be opened”, or “Apple cannot check it for malicious software” | Download the `.dmg` or `.zip`, open it, then **right-click Queryline → Open** (not double-click) and confirm **Open** in the dialog. If macOS still blocks it: **System Settings → Privacy & Security** → scroll down → **Open Anyway** next to the Queryline message. You only need to do this once per install. |
| **Windows** | SmartScreen: “Windows protected your PC” / “Unknown publisher” | Click **More info**, then **Run anyway**. For the NSIS installer, accept the UAC prompt when it appears. |
| **Linux** | AppImage won’t run, or `.deb` install blocked | **AppImage:** `chmod +x Queryline-*.AppImage`, then run it; if your desktop environment asks, allow executing the file. **`.deb`:** install with `sudo dpkg -i Queryline_*.deb` (or use your package manager). |

Auto-updates from GitHub may trigger the same warnings again after a major upgrade; repeat the steps above if needed.

### Install

1. Download the installer for your OS from [GitHub Releases](https://github.com/CPF32/text-to-sql-analytics/releases/latest).
2. If your browser or OS flags the download, keep the file — see [Unsigned builds](#unsigned-builds-read-this-first) above.
3. Run the installer (or open the `.dmg` / AppImage). You'll get **Queryline** in your applications folder with the Queryline icon (not the generic Electron dev icon).
4. On first launch, a short **setup wizard** asks whether to self-host **Ollama** (optional — you can configure LLM settings later in Admin).
5. Sign in with your **computer username and password**.

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

Installers are written to `release/`. Local builds are also unsigned unless you configure signing yourself. See [DEPLOY.md](DEPLOY.md) for publishing releases and optional code signing.

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
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

Or Anthropic / Gemini:

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

1. **Admin → LLM settings** — choose Ollama, OpenAI, Anthropic, or Gemini and test the connection.
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
