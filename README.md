# Agam Automation Hub

A fully local, Python-powered personal automation system that handles daily job searching, LinkedIn content creation, Gmail triage, and morning briefings — all orchestrated through a Telegram bot and a unified CLI. Built for a Data Scientist's workflow with Claude AI at the core, every outward-facing action (posting, emailing, applying) has a human-in-the-loop gate so nothing fires without explicit approval.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or higher |
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
