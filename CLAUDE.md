# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Personal AI automation system targeting LinkedIn, job platforms, Telegram, and Gmail. Built with Python 3.11.

## Environment Setup

```bash
# Activate virtual environment (Windows)
source venv/Scripts/activate

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt
```

## Project Status

This repository is in early setup — the venv is initialized but no source code, dependencies, or configuration exists yet. When building out the project, expect to create:

- `requirements.txt` — Python dependencies
- `src/` — main source directory with per-platform modules (linkedin, gmail, telegram, jobs)
- `.env` — credentials and API keys (never commit this)
- Entry point (e.g., `main.py` or `src/main.py`)

## Architecture Intent

Modular design with separate integration modules per platform, an AI orchestration layer (likely via Claude/Anthropic SDK), and a scheduler or event-driven trigger mechanism to run automations.
