# Narrative Intelligence Engine - Phase 2 (Model-Agnostic Local Pipeline)

An infrastructure-independent, local-first platform designed to fetch multilingual, multi-source newsletter and PR content, extract structured metadata and narrative insights using model-agnostic LLMs, store data in a local high-performance DuckDB, and serve searches and analytics through a FastAPI dashboard.

---

## Architecture Overview

1. **Ingestion Layer (R)**: Modular fetching scripts retrieve content from unread emails via IMAP ([email_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/email_ingester.R)), XML feed resources ([rss_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/rss_ingester.R)), subscription publications ([subscription_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/subscription_ingester.R)), public Telegram channel previews ([telegram_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/telegram_ingester.R)), and Mastodon/Fediverse profiles ([fediverse_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/fediverse_ingester.R)) including automatic extraction and scraping of nested web links. All ingesters return self-describing records with uniform `platform` and `raw_source` fields.
2. **Real-Time Email Daemon (Python)**: A persistent Python daemon ([email_daemon.py](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/email_daemon.py)) uses IMAP IDLE for instant push-based email notification, with auto-sync on reconnect. A companion script ([fast_ingest_mailbox.py](file:///Users/arf/R_projects_local/newsletter_phase2/scratch/fast_ingest_mailbox.py)) handles parallelized historical backfill.
3. **Analysis & Vectorization (LLM/Embeddings)**: A unified model adapter ([model_adapter.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/model_adapter.R)) interfaces with OpenRouter (Liquid LFM-2), OpenAI, Gemini, or local models (Ollama). All API calls enforce explicit `httr2::req_timeout()` limits. Standardized LLM prompts ([prompts.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/prompts.R)) detect source language, generate English translations/summaries, and extract metadata. A dedicated translation module ([translation_ollama.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/translation_ollama.R)) handles low-resource African languages (isiXhosa, isiZulu, Setswana, Kinyarwanda, Sesotho, siSwati, Wolof) with SQLite caching and generic LLM fallback. Dual vector columns store multilingual original embeddings and English summary embeddings side-by-side.
4. **Entity Deduplication Engine**: A lexicon lookup resolver ([entity_resolver.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/entity_resolver.R)) deduplicates extracted entities using compiled Jaro-Winkler string similarity from the `stringdist` C library (threshold ≥ 0.88).
5. **Storage (DuckDB)**: All data resides in a local `newsletters.db` DuckDB file ([db_manager.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/db_manager.R)). Memory limits (`1.5GB`) and single-thread CPU constraints are enforced to run reliably on resource-limited cloud VMs.
6. **Configuration Manifest**: A central project-level manifest ([manifest.json](file:///Users/arf/R_projects_local/newsletter_phase2/manifest.json)) declares active models/providers across extraction, embeddings, and evaluation phases. The R config layer ([config.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/config.R)) parses this file and uses its settings as defaults, overridable by environment variables.
7. **Dashboard Layer (FastAPI & HTML5)**: A Python FastAPI backend ([app.py](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/app.py)) serves API routes (search, stats, auth, history, saved searches, and notifications). A secondary SQLite database (`users.db`) isolates user profiles, saved query parameters, notifications, and search history to prevent file-locking conflicts with the read-only DuckDB instance. A responsive glassmorphic HTML5/vanilla CSS single-page frontend ([static/](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/static/)) delivers sub-millisecond search results.
8. **Regional Survey Application**: A companion FastAPI application ([alpha_survey/](file:///Users/arf/R_projects_local/newsletter_phase2/alpha_survey/)) enables auditor-scoped regional media source discovery. Sources logged here are consumed by `run_cron.R` to dynamically populate the ingestion pipeline.

---

## Directory Structure

```
manifest.json                 # Central model/provider configuration manifest
alpha/
├── config.R                  # Configuration parser (manifest.json + env vars + provider tokens)
├── db_manager.R              # DuckDB database connection & table schemas
├── model_adapter.R           # Model-agnostic LLM interface (OpenRouter, Ollama, OpenAI, Gemini)
├── prompts.R                 # Standardized multilingual LLM extraction prompts
├── email_ingester.R          # Email ingestion layer (IMAP mRpostman retrieval)
├── rss_ingester.R            # Fetch and clean RSS/Atom XML feeds
├── subscription_ingester.R   # Scrapes and extracts Substack/Ghost content
├── telegram_ingester.R       # Scrapes public t.me/s/[channel] posts
├── fediverse_ingester.R      # Mastodon RSS profile post parser & webpage scraper
├── entity_resolver.R         # Jaro-Winkler entity lexicon deduplication (via stringdist)
├── translation_ollama.R      # Local Ollama translation for low-resource African languages
├── evaluate_nuance.R         # Nuance & translation LLM-as-a-judge validation script
├── pipeline_runner.R         # Orchestrates ingestion, LLM, embedding, DB commit
├── run_cron.R                # Daily cron entry point: loads sources from survey DB, runs pipeline
├── email_daemon.py           # Python IMAP IDLE daemon for real-time Gmail ingestion
├── email_ingester.py         # Python email MIME parser and DuckDB writer
├── app.py                    # Python FastAPI server (search, stats, auth, history, notifications)
├── search_parser.py          # Boolean/phrase/proximity search query parser
├── pipeline.md               # Detailed pipeline architecture documentation
├── users.db                  # SQLite database tracking user sessions, history, and alerts (auto-created)
├── newsletters.db            # DuckDB primary data store (auto-created)
└── static/                   # Self-contained dashboard files
    ├── index.html            # Dashboard structure
    ├── styles.css            # Dark mode, glassmorphism CSS
    └── dashboard.js          # Fetch requests, search state, rendering, and chart metrics

alpha_survey/                 # Regional media source discovery survey app
├── app.py                    # FastAPI backend with auditor-scoped views
├── static/                   # Survey frontend (index.html, styles.css, app.js)
└── sources.db                # SQLite database of ingestion sources (consumed by run_cron.R)
```

---

## Environment Setup

Create an environment configuration (e.g. `.Renviron` for R or `.env` for Python) with the following parameters:

```env
# Ingestion Credentials
GMAIL_USERNAME=your-ingestion-inbox@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# LLM Provider Configuration (override manifest.json defaults)
LLM_PROVIDER=openrouter          # openrouter | ollama | openai | gemini
LLM_MODEL=liquid/lfm-2-24b-a2b  # model identifier for chat completions
EMBEDDING_PROVIDER=ollama        # provider for vector embeddings
EMBEDDING_MODEL=nomic-embed-text:latest

# Provider API Keys (at least one required)
OPENROUTER_API_KEY=your-openrouter-key
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key

# Translation
TRANSLATION_MODEL=afriqueqwen-14b-multiturn  # local Ollama model for low-resource languages

# Forensic Logging
FORENSIC_LOG_PATH=FORENSIC_LOG  # path for LLM response audit log

# Storage & Sync (Optional)
DUCKDB_PATH=alpha/newsletters.db
GCS_BUCKET_NAME=your-gcs-bucket

# Personalization Database Configuration (Optional, defaults to alpha/users.db)
USERS_DB_PATH=alpha/users.db
```

---

## Quick Start

### 1. Real-Time Email Daemon (Python)
Start the IMAP IDLE daemon for push-based Gmail ingestion:
```bash
.venv/bin/python alpha/email_daemon.py
```

### 2. Daily Ingestion Pipeline (R)
Ensure R dependencies are installed:
```bash
Rscript -e "renv::restore()"
```
Run the full multi-source cron ingestion:
```bash
Rscript alpha/run_cron.R
```
This loads dynamic sources from the survey database, then runs the R pipeline across Gmail, RSS, Telegram, Fediverse, and Subscription ingesters.

### 3. FastAPI Dashboard (Python)
Install Python dependencies:
```bash
pip install fastapi uvicorn duckdb pandas pydantic python-dotenv httpx
```
Run the FastAPI web server locally:
```bash
uvicorn alpha.app:app --reload --port 8000
```
Open `http://localhost:8000` in your web browser.

### 4. Survey Application (Python)
Start the regional source discovery survey:
```bash
uvicorn alpha_survey.app:app --reload --port 8080
```

### 5. Verification Test Suites (Python & R)
Run the Python authentication and notifications integration tests:
```bash
python scratch/test_auth_notifications.py
```
Run the Fediverse RSS ingestion and external page scraping tests:
```bash
Rscript scratch/test_fediverse.R
```

---

## Commercial Licensing Compliance
* **DuckDB**: MIT License (Commercial-friendly)
* **SQLite**: Public Domain (No restrictions)
* **FastAPI/Uvicorn**: MIT/BSD (Commercial-friendly)
* **stringdist**: GPL-3 (Copyleft — review if redistributing)
* **Liquid LFM-2 (OpenRouter)**: API usage (No local weight distribution)
