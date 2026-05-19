# Narrative Intelligence Engine - Phase 2 (Model-Agnostic local Pipeline)

An infrastructure-independent, local-first platform designed to fetch multilingual, multi-source newsletter and PR content, extract structured metadata and narrative insights using model-agnostic LLMs, store data in a local high-performance DuckDB, and serve searches and analytics through a FastAPI dashboard.

---

## Architecture Overview

1. **Ingestion Layer (R)**: Modular fetching scripts fetch unread newsletters via IMAP (`email_ingester.R`), parse XML releases (`rss_ingester.R`), read subscription platform pages (`subscription_ingester.R`), and scrape public Telegram previews (`telegram_ingester.R`).
2. **Analysis & Vectorization (LLM/Embeddings)**: A unified model adapter (`model_adapter.R`) interfaces with OpenRouter (Deepseek, Kimi) or local models (Ollama). Standardized LLM prompts detect source language, produce English summaries, and extract metadata. Dual vector columns store multilingual original embeddings and English summary embeddings side-by-side.
3. **Deduplication Engine**: A lexicon lookup resolver (`entity_resolver.R`) cleans extracted entity records using Jaro-Winkler string similarity and periodic LLM-assisted grouping.
4. **Storage (DuckDB)**: All data resides in a local `newsletters.db` DuckDB file. Memory limits (`512MB`) and CPU constraints are enforced to run reliably on resource-limited cloud VMs.
5. **Dashboard Layer (FastAPI & HTML5)**: A Python FastAPI backend (`app.py`) serves API routes (search, stats, list) and handles Cloud Storage sync. A responsive vanilla CSS single-page frontend (`static/`) delivers sub-millisecond search results.

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
├── entity_resolver.R         # Entity lexicon matching & deduplication resolver
├── evaluate_nuance.R         # Nuance & translation LLM-as-a-judge validation script
├── pipeline_runner.R         # Orchestrates ingestion, LLM, embedding, DB, and Cloud Sync
├── app.py                    # Python FastAPI server (serves search API, handles DB range queries)
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
pip install fastapi uvicorn duckdb pandas pydantic python-dotenv
```
Run the FastAPI web server locally:
```bash
uvicorn alpha.app:app --reload --port 8000
```
Open `http://localhost:8000` in your web browser.

---

## Commercial Licensing Compliance
* **DuckDB**: MIT License (Commercial-friendly)
* **SQLite**: Public Domain (No restrictions)
* **FastAPI/Uvicorn**: MIT/BSD (Commercial-friendly)
* **Deepseek (OpenRouter)**: MIT License (Commercial-friendly)
