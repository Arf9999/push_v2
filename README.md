# Narrative Intelligence Engine - Phase 2 (Model-Agnostic local Pipeline)

An infrastructure-independent, local-first platform designed to fetch multilingual, multi-source newsletter and PR content, extract structured metadata and narrative insights using model-agnostic LLMs, store data in a local high-performance DuckDB, and serve searches and analytics through a FastAPI dashboard.

---

## Architecture Overview

1. **Ingestion Layer (R)**: Modular fetching scripts retrieve content from unread emails via IMAP ([email_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/email_ingester.R)), XML feed resources ([rss_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/rss_ingester.R)), subscription publications ([subscription_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/subscription_ingester.R)), public Telegram channel previews ([telegram_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/telegram_ingester.R)), and Mastodon/Fediverse profiles ([fediverse_ingester.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/fediverse_ingester.R)) including automatic extraction and scraping of nested web links.
2. **Analysis & Vectorization (LLM/Embeddings)**: A unified model adapter ([model_adapter.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/model_adapter.R)) interfaces with OpenRouter (Deepseek, Kimi), OpenAI, Gemini, or local models (Ollama). Standardized LLM prompts ([prompts.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/prompts.R)) detect source language, generate English translations/summaries, and extract metadata. Captures and propagates the original target source/article URLs. Dual vector columns store multilingual original embeddings and English summary embeddings side-by-side.
3. **Deduplication Engine**: A lexicon lookup resolver ([entity_resolver.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/entity_resolver.R)) cleans extracted entity records using Jaro-Winkler string similarity and periodic LLM-assisted grouping.
4. **Storage (DuckDB)**: All data resides in a local `newsletters.db` DuckDB file ([db_manager.R](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/db_manager.R)). Memory limits (`512MB`) and CPU constraints are enforced to run reliably on resource-limited cloud VMs.
5. **Dashboard Layer (FastAPI & HTML5)**: A Python FastAPI backend ([app.py](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/app.py)) serves API routes (search, stats, auth, history, saved searches, and notifications). A secondary SQLite database (`users.db`) isolates user profiles, saved query parameters, notifications, and search history to prevent file-locking conflicts with the read-only DuckDB instance. A responsive glassmorphic HTML5/vanilla CSS single-page frontend ([static/](file:///Users/arf/R_projects_local/newsletter_phase2/alpha/static/)) delivers sub-millisecond search results.

---

## Directory Structure

```
alpha/
├── config.R                  # Configuration parser (env vars, provider tokens)
├── db_manager.R              # DuckDB database connection & table schemas
├── model_adapter.R           # Model-agnostic LLM interface (R)
├── email_ingester.R          # Rewritten email ingestion layer (IMAP mRpostman retrieval)
├── rss_ingester.R            # Fetch and clean RSS XML feeds
├── subscription_ingester.R   # Scrapes and extracts Substack/Ghost content
├── telegram_ingester.R       # Scrapes public t.me/s/[channel] posts
├── fediverse_ingester.R      # Mastodon RSS profile post parser & webpage scraper
├── entity_resolver.R         # Entity lexicon matching & deduplication resolver
├── evaluate_nuance.R         # Nuance & translation LLM-as-a-judge validation script
├── pipeline_runner.R         # Orchestrates ingestion, LLM, embedding, DB, and Cloud Sync
├── app.py                    # Python FastAPI server (search, stats, auth, history, notifications)
├── users.db                  # SQLite database tracking user sessions, history, and alerts (auto-created)
└── static/                   # Self-contained dashboard files
    ├── index.html            # Dashboard structure
    ├── styles.css            # Dark mode, glassmorphism CSS
    └── dashboard.js          # Fetch requests, search state, rendering, and chart metrics
```

---

## Environment Setup

Create an environment configuration (e.g. `.Renviron` for R or `.env` for Python) with the following parameters:

```env
# Ingestion Credentials
GMAIL_USERNAME=your-ingestion-inbox@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# LLM Providers (At least one)
OPENROUTER_API_KEY=your-openrouter-key
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key

# Storage & Sync (Optional)
GCS_BUCKET_NAME=your-gcs-bucket
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Personalization Database Configuration (Optional, defaults to alpha/users.db)
USERS_DB_PATH=alpha/users.db
```

---

## Quick Start

### 1. Ingestion Pipeline (R)
Ensure R dependencies are installed:
```bash
Rscript -e "renv::restore()"
```
Run the full ingestion schedule manually:
```bash
Rscript alpha/pipeline_runner.R
```

### 2. FastAPI Dashboard (Python)
Install Python dependencies:
```bash
pip install fastapi uvicorn duckdb pandas pydantic python-dotenv httpx
```
Run the FastAPI web server locally:
```bash
uvicorn alpha.app:app --reload --port 8000
```
Open `http://localhost:8000` in your web browser.

### 3. Verification Test Suites (Python & R)
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
* **Deepseek (OpenRouter)**: MIT License (Commercial-friendly)
