# Agam Automation Hub

A fully local, Python-powered personal automation system that handles daily job searching, LinkedIn content creation, Gmail triage, and morning briefings — all orchestrated through a Telegram bot and a unified CLI. Built for a Data Scientist's workflow with Claude AI at the core, every outward-facing action (posting, emailing, applying) has a human-in-the-loop gate so nothing fires without explicit approval.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or higher |
| **Node.js** | 18 or higher (for React frontend) |
| **Anthropic API key** | Claude Pro — [console.anthropic.com](https://console.anthropic.com/) |
| **Telegram account** | Free — for bot + notifications |
| **LinkedIn Developer App** | Free — for posting ([developers page](https://www.linkedin.com/developers/apps)) |
| **Gmail API credentials** | Free — Google Cloud Console OAuth 2.0 |
| **OS** | macOS, Linux, or Windows (WSL recommended) |

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/agamsaraswat/agam-automation-hub.git
cd agam-automation-hub

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the setup wizard
python run.py --setup
```

The setup wizard walks you through configuring each service, writing your `.env` file, creating output directories, and initialising the SQLite database.


## Daily Local Dev (One Command)

### 1) Create your local env file once

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Then fill only the services you use.

### 2) Install deps once

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 3) Start backend + frontend together (recommended)

macOS/Linux:

```bash
python run_web.py --mode both
# or: ./scripts/dev.sh
```

Windows CMD:

```bat
dev.bat
```

Windows PowerShell:

```powershell
./dev.ps1
```

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### 4) Run basic checks

macOS/Linux:

```bash
./scripts/lint.sh
./scripts/test.sh
```

Windows CMD:

```bat
lint.bat
test.bat
```

Windows PowerShell:

```powershell
./lint.ps1
./test.ps1
```

---

## One-Time Setup Per Service

### Anthropic (Claude AI)

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Create an API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### LinkedIn

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps) and create an app
2. Under **Products**, request access to **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect**
3. Generate a token at the [Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator) — select scopes: `w_member_social`, `openid`, `profile`
4. Find your Person URN: use the token to call `GET https://api.linkedin.com/v2/userinfo` — your `sub` field is your ID
5. Add to `.env`:
   ```
   LINKEDIN_ACCESS_TOKEN=<your-token>
   LINKEDIN_PERSON_URN=urn:li:person:<your-id>
   LINKEDIN_TOKEN_SET_DATE=2025-01-15
   ```
6. **Important**: Tokens expire after ~60 days. The system warns you when it's time to refresh.

### Telegram

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to create your bot
3. Copy the bot token
4. Message [@userinfobot](https://t.me/userinfobot) to get your personal chat ID
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=<bot-token>
   TELEGRAM_CHAT_ID=<your-chat-id>
   ```

### Gmail

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable the **Gmail API**
3. Go to **Credentials** → Create **OAuth 2.0 Client ID** (Desktop app type)
4. Download the JSON file as `credentials.json` into the repo root
5. On first run (`python run.py --gmail`), a browser window opens for OAuth consent
6. The resulting `token.json` is auto-saved (gitignored)

---

## Daily Usage

### Morning Workflow

```bash
# Check system status
python run.py --status

# Generate morning briefing (also sends to Telegram)
python run.py --briefing

# Run job search + tailoring
python run.py --jobs

# Generate + review + publish LinkedIn post
python run.py --linkedin
```

### Telegram Bot Commands

Once the bot is running (`python run.py --telegram`):

| Command | Action |
|---|---|
| `/briefing` | Get today's morning briefing |
| `/jobs` | Show today's job queue |
| `/linkedin` | Generate a LinkedIn post |
| `/applied Company, Role` | Mark a job as applied |
| `/status` | System status dashboard |
| *Any message* | Claude agent with tool access |

### Gmail Triage

```bash
python run.py --gmail
```

Fetches unread emails from the last 30 minutes, classifies them (urgent / normal / newsletter / spam), and sends a summary to Telegram. Urgent emails get draft reply suggestions. **Emails are never auto-sent.**

---

## Web App Skeleton (Option B)

This repo now includes an initial web stack while preserving the existing CLI:

- **FastAPI backend**: `src/web/main.py`
- **Shared service layer**: `src/services/automation.py` (used by CLI + API)
- **React + TypeScript frontend**: `frontend/`
- **Dev runner**: `run_web.py`

### Frontend Dashboard (first usable version)

The React UI now includes:

- Sidebar navigation
- Top header
- Pages: Dashboard, Jobs, LinkedIn, Gmail, Settings, Runs/Logs
- Dashboard quick actions wired to backend endpoints
- Jobs page with status/source/search filters and summary cards
- Loading and error states for API calls

### 1) Install dependencies (if not already installed)

```bash
# Python deps (includes FastAPI + uvicorn)
pip install -r requirements.txt

# Frontend deps
cd frontend
npm install
cd ..
```

Windows helper scripts:

- `dev.bat` / `dev.ps1`
- `lint.bat` / `lint.ps1`
- `test.bat` / `test.ps1`

### 2) Run backend + frontend together

```bash
python run_web.py --mode both
```

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### 3) Run services separately (optional)

```bash
# Backend only
python -m uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Frontend only
cd frontend && npm run dev
```

### 4) Verify connectivity

- Backend health endpoint: `GET /api/health`
- Backend system snapshot endpoint: `GET /api/status`
- Run jobs pipeline: `POST /api/jobs/run`
- Read jobs queue: `GET /api/jobs/queue`
- Read jobs stats: `GET /api/jobs/stats`
- Run briefing: `POST /api/briefing/run`
- Run Gmail triage: `POST /api/gmail/run`
- Recent backend runs: `GET /api/runs`
- Scheduler status/control:
  - `GET /api/scheduler/status`
  - `POST /api/scheduler/start` (requires `{"confirm_action": true}`)
  - `POST /api/scheduler/stop` (requires `{"confirm_action": true}`)
- LinkedIn status: `GET /api/linkedin/status`
- LinkedIn review workflow:
  - `GET /api/linkedin/draft`
  - `POST /api/linkedin/draft/generate`
  - `PUT /api/linkedin/draft`
  - `POST /api/linkedin/draft/approve`
  - `POST /api/linkedin/draft/reject`
  - `POST /api/linkedin/draft/publish` (requires `confirm_publish=true` and approved status)
- Settings (safe non-secret editor):
  - `GET /api/settings`
  - `PUT /api/settings`
  - Editable in UI: target roles, locations, include/exclude keywords, daily job limit, LinkedIn posting window, and source toggles.
  - Secrets are never returned; only configured/not-configured status is exposed.
- Frontend LinkedIn page now supports the full human review flow: generate, edit, approve/reject, and guarded publish.
- Frontend home page fetches `/api/health` and shows connection status.


### Scheduler controls from frontend

The Dashboard now includes scheduler controls for local single-user operation:

- View whether APScheduler is running
- Start scheduler from the UI
- Stop scheduler from the UI
- See configured jobs, cadence trigger strings, and next planned runs (when available)

This reuses the existing APScheduler implementation instead of replacing it.



### Known limitations (local single-user hardening notes)

- Scheduler state is process-local; if the backend process restarts, scheduler returns to stopped until started again.
- Run history is a local JSONL file (`output/runs/history.jsonl`), intended for single-user local operation.
- Error messages in run history are redacted for common token patterns, but you should still avoid logging full secret values in custom code.
- Destructive/state-changing actions require explicit confirmation payloads (scheduler start/stop, LinkedIn publish).

### Run observability

The backend now stores a lightweight run history for key automation tasks in `output/runs/history.jsonl` with:

- `run_id`
- `task_type`
- `start_time` / `end_time`
- `status`
- `summary`
- `error_message` (if failed)

Tracked task types: `jobs`, `briefing`, `gmail`, and `linkedin_generation`.
The frontend **Runs / Logs** page reads this via `GET /api/runs` to show latest runs and failure details.

### Settings page coverage

The **Settings** page now supports common day-to-day tuning without hand-editing YAML:

- `target_roles` (job_search.yaml)
- `locations` (job_search.yaml)
- `filters.include_keywords` / `filters.exclude_keywords` (job_search.yaml)
- `jobs.daily_limit` (settings.yaml)
- `schedule.linkedin_post_window_start` / `schedule.linkedin_post_window_end` (settings.yaml)
- `sources.*.enabled` toggles (job_search.yaml)

Still file-based for now:

- Secret values in `.env` (API keys/tokens)
- Advanced filtering knobs (e.g., include/exclude titles, minimum match threshold)
- Other scheduler settings not listed above

### Job relevance filtering (configurable)

The scraper now applies configurable relevance scoring before jobs enter the visible queue.
Tune this in `config/job_search.yaml` under `filters`:

- `include_keywords`
- `exclude_keywords`
- `include_titles`
- `exclude_titles`
- `preferred_locations`
- `remote_preference`
- `minimum_match_threshold`

Each run writes explainable keep/reject decisions to:

- `output/jobs/<YYYY-MM-DD>/filtering_report.jsonl`

### Local CORS

For local development, CORS allows:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:3000`
- `http://127.0.0.1:3000`

Override via:

```bash
export WEB_CORS_ORIGINS="http://localhost:5173,http://localhost:4173"
```

---

## Scheduler Mode

Leave running in the background for fully automated daily operations:

```bash
python run.py --schedule
```

| Time | Task |
|---|---|
| 07:00 | Morning briefing → Telegram |
| 08:00–11:00 | LinkedIn post generation (random time) |
| 08:30 | Job scraper + resume tailoring |
| Every 30 min | Gmail triage |
| 21:00 | Daily summary → Telegram |

**Tip**: Run in `tmux` or `screen` so it persists after closing the terminal:

```bash
tmux new -s hub
python run.py --schedule
# Ctrl+B, D to detach
# tmux attach -t hub to reattach
```

---

## Output Structure

```
output/
├── linkedin/
│   ├── queue/          # Drafts awaiting review
│   │   └── 2025-06-15.md
│   └── posted/         # Published posts archive
│       └── 2025-06-14.md
├── jobs/
│   └── 2025-06-15/
│       └── google_senior_data_scientist/
│           ├── resume.md           # Tailored resume
│           ├── cover_letter.md     # Tailored cover letter
│           ├── match_score.txt     # Match analysis
│           └── jd_keywords.txt     # Extracted JD keywords
└── briefings/
    └── 2025-06-15.md
```

---

## Adding Jobs Manually

If you find a job listing you want to add to the pipeline:

1. Save the job description as a text file
2. Use the Telegram bot: send a message like *"Add this job to my queue: Senior DS at Google, URL: https://..."*
3. Or directly insert into SQLite:

```python
from src.jobs.deduplicator import add_job
add_job(
    url="https://careers.google.com/jobs/12345",
    company="Google",
    title="Senior Data Scientist",
    jd_text="Full job description here...",
    status="queued",
)
```

---

## Troubleshooting

### LinkedIn Token Expired

The system warns you via Telegram and the status dashboard when your token is > 50 days old.

1. Go to the [LinkedIn Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator)
2. Generate a new token
3. Update `.env`: `LINKEDIN_ACCESS_TOKEN=<new-token>` and `LINKEDIN_TOKEN_SET_DATE=<today>`

### Gmail OAuth Issues

If `token.json` becomes invalid:

```bash
rm token.json
python run.py --gmail   # Re-triggers OAuth flow in browser
```

### Rate Limits

- **Claude API**: The system uses `claude-sonnet-4-20250514` — monitor usage at [console.anthropic.com](https://console.anthropic.com/)
- **LinkedIn API**: 100 posts/day limit (you'll never hit this)
- **Job scrapers**: RemoteOK and Himalayas are rate-limited to 1 req/sec; the scraper respects this
- **Gmail API**: 250 quota units/second — the 30-min interval keeps usage minimal

### Common Errors

| Error | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` | Run `python run.py --setup` or add to `.env` |
| `LINKEDIN_ACCESS_TOKEN not set` | Add LinkedIn token to `.env` |
| `Gmail credentials file not found` | Download `credentials.json` from Google Cloud Console |
| `Telegram: Unauthorized` | Check `TELEGRAM_CHAT_ID` matches your account |
| SQLite `database is locked` | Close other processes using `data/jobs.db` |

---

## Safety Guardrails

This system is built with strict human-in-the-loop controls:

1. **LinkedIn**: Posts NEVER auto-publish. The terminal reviewer (`reviewer.py`) requires explicit `P` + `yes` confirmation.
2. **Gmail**: Emails are NEVER auto-sent. Only drafts are created; you review in Gmail.
3. **Job Applications**: Resumes and cover letters are saved as files. You submit manually through ATS portals.
4. **Telegram**: Destructive operations require confirmation.
5. **File Safety**: All outputs go to `output/` only. The system never modifies files outside this directory.
6. **Daily Limits**: Hard cap of 10 jobs/day to prevent runaway scraping.

---

## Roadmap

- [ ] **Discord integration** — scaffolded in `src/messaging/discord_bot.py`
- [ ] **WhatsApp integration** — scaffolded in `src/messaging/whatsapp.py`
- [ ] **Auto-apply** — direct ATS submission (Lever, Greenhouse APIs) with human confirmation
- [ ] **Interview prep module** — Claude generates interview questions from JD + resume
- [ ] **Analytics dashboard** — track application funnel, response rates, and time-to-interview
- [ ] **Resume PDF generation** — auto-convert tailored `.md` resumes to formatted PDFs
- [ ] **Multi-LLM routing** — use GPT-4o for some tasks, Claude for others based on cost/quality

---

## License

Personal use. Not open-sourced.
