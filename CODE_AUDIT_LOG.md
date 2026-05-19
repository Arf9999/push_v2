# Forensic Code Audit Log

All changes to core R/Python scripts and LLM prompts are logged here.

## 2026-05-19

### Created Project Structure and Configuration Layer
- **Files**: `README.md`, `alpha/config.R`
- **Strategic Intent**: Establish the workspace layout for Phase 2, move away from hardcoded variables, and support model-agnostic endpoints (OpenRouter, Ollama, OpenAI, Anthropic, Gemini) via dynamic environment parsing.
- **Commit Reference**: Scaffolding init.

### Created Database Storage Layer
- **Files**: `alpha/db_manager.R`
- **Strategic Intent**: Define local DuckDB schemas for newsletters, entities, and deduplicated lexicon tables. Enforce strict `512MB` memory limits and single-threading to prevent OOM errors on resource-constrained VM nodes.

### Created Model Adapter Layer
- **Files**: `alpha/model_adapter.R`
- **Strategic Intent**: Implement the model-agnostic layer to perform chat completions and vector embedding generation across OpenRouter (Deepseek/Kimi), Ollama, OpenAI, and Gemini with auto-retry and failover.

### Created Email Ingestion Module
- **Files**: `alpha/email_ingester.R`
- **Strategic Intent**: Rebuild the email fetching layer using modern R packages. Encapsulate IMAP operations, multipart boundary decodings, HTML-to-text sanitization, and high-watermark cursor persistence to isolate Gmail intake.

### Created RSS Ingestion Module
- **Files**: `alpha/rss_ingester.R`
- **Strategic Intent**: Implement the RSS/XML parsing system. Fetches feeds, cleans standard HTML formatting from fields, converts XML tags to structured plain text records, and resolves article links into unique MD5 hashes.

### Created Telegram Ingestion Module
- **Files**: `alpha/telegram_ingester.R`
- **Strategic Intent**: Implement scraping of public Telegram channels (`t.me/s/[channel]`) using CSS-based DOM parsing to pull date, content, and deep links without needing API keys.

### Created Subscription Ingestion Module
- **Files**: `alpha/subscription_ingester.R`
- **Strategic Intent**: Add dual capability to fetch Substack and Ghost publications using both their XML/RSS endpoints and direct HTML scraping, extracting articles into standard schema formats.

### Created Entity Resolver Module
- **Files**: `alpha/entity_resolver.R`
- **Strategic Intent**: Implement the database-backed entity resolution and deduplication algorithm. Features a pure-R Jaro-Winkler string similarity scorer (avoiding OS-dependent package compile issues) and auto-updates the `entity_lexicon` mapping table.

### Created Analysis Prompt System
- **Files**: `alpha/prompts.R`
- **Strategic Intent**: Establish standardized multilingual LLM prompts for extracting structured metadata. Requests strict JSON formatting representing detected language, English/Original summary pairs, publication tags, and raw entities.

### Created Translation Nuance Evaluation Suite
- **Files**: `alpha/evaluate_nuance.R`
- **Strategic Intent**: Establish an LLM-as-a-judge quantitative validation script. Compares generated English translations against original texts across Accuracy, Tone, Nuance, and Idiomatic metrics on a 1-5 scale.

### Created Pipeline Ingestion Orchestrator
- **Files**: `alpha/pipeline_runner.R`
- **Strategic Intent**: Integrate each module (Gmail, RSS, Telegram, Substack) into a serial loop. Enforces duplication filtering, word caps, JSON-prompt completions, dual-space vector construction, and relational database operations.

### Created FastAPI Service Backend
- **Files**: `alpha/app.py`
- **Strategic Intent**: Establish a Python-based REST API for high-performance retrieval. Features read-only DuckDB connection isolation, SQL-native cosine vector similarity searches, statistics aggregation, and entity mapping.

### Enhanced Entity Pre-Aggregation and Frontend Search
- **Files**: `alpha/app.py`, `alpha/static/dashboard.js`
- **Strategic Intent**: Optimize entity rendering on the search dashboard by performing a SQL-native subquery join in FastAPI to package associated entities within the search results payload. Clean up the frontend by removing redundant API roundtrips and introducing interactive, clickable tag filters.

### Fixed DuckDB Foreign Key Schema Constraints
- **Files**: `alpha/db_manager.R`
- **Strategic Intent**: Remove ON DELETE CASCADE referential constraint which is unsupported in DuckDB syntax, preventing table parser initialization crashes.

### Hardened Entity Resolution Logic with Guard Clauses
- **Files**: `alpha/entity_resolver.R`
- **Strategic Intent**: Implement explicit NA and NULL guard clauses in Jaro-Winkler calculations and lexicon retrieval to prevent comparison runtime crashes. Fix R descending sequence bug (`start:end` when `start > end`) by wrapping search loops in `if (start <= end)`.

### Corrected DB Parameter Binding for SQL Arrays
- **Files**: `alpha/pipeline_runner.R`, `scratch/run_integration_test.R`
- **Strategic Intent**: Wrap embedding vectors in nested `list()` before binding in DBI parameter queries to avoid length mismatch errors and correctly bind values as DuckDB FLOAT[] list arrays.
