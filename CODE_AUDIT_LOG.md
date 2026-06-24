# Forensic Code Audit Log

All changes to core R/Python scripts and LLM prompts are logged here.

## 2026-06-24

### Rebranded Pipeline to Push Media
- **Files**: `alpha/model_adapter.py`, `alpha/pipeline_runner.R`, `alpha/static/index.html`, `alpha/model_adapter.R`, `alpha/translation_ollama.R`, `METHODOLOGY.md`, `README.md`, `CODE_AUDIT_LOG.md`
- **Strategic Intent**: Disassociate the pipeline from "Narrative Intelligence" branding as that is a completely separate project, renaming all occurrences across workspace and documentation to "Push Media".

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

### Added Interactive Sensitivity Slider and Client-Side CSV Export
- **Files**: `alpha/static/index.html`, `alpha/static/styles.css`, `alpha/static/dashboard.js`
- **Strategic Intent**: Empower dashboard users to dynamically adjust vector search sensitivity (cosine similarity score thresholds) client-side in real-time. Implement dynamic CSV results export complete with entity resolution mappings, summaries, and match scores.

### Implemented User Personalization, Search History, Saved Searches, and In-App Notifications
- **Files**: `alpha/app.py`, `alpha/static/index.html`, `alpha/static/styles.css`, `alpha/static/dashboard.js`, `scratch/test_auth_notifications.py`
- **Strategic Intent**: Deliver full-featured dashboard personalization and alerts. Implemented standard library password-hashed auth gating, SQLite session database tracking user profiles, saved query parameters, and search history. Wired a client-side Workspace containing Recent and Saved searches, an unread notification bell dropdown, automatic Authorization bearer header injection, active search state auto-triggering on history clicks, and a manual "Run Daily Check" trigger mimicking the cron ingestion script. Verified end-to-end integration via mock tests.

## 2026-05-20

### Implemented Forensic LLM Response Logging
- **Files**: `alpha/config.R`, `alpha/model_adapter.R`
- **Strategic Intent**: Meet the governance and audit requirements for persistent logging of LLM requests. Logs the active provider, model, system instructions, user prompts, thinking/reasoning outputs (where available), and final completions to the forensic log file (`FORENSIC_LOG`). Allows customization of the log file path via the `FORENSIC_LOG_PATH` environment variable.

### Created Regional Media Ingestion Survey Application
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`, `alpha_survey/static/styles.css`, `alpha_survey/static/app.js`, `scratch/test_survey_api.py`
- **Strategic Intent**: Deliver an audit-compliant, self-contained media discovery survey workspace. Includes SQLite database schema tracking active and soft-deleted sources, automated ID serialization (`{Country}_{Platform}_{Topic}_{Num}`), robust text-based activity log files, a user attribution field (`input_by`) cached locally via the browser, and coordinator authorization passcode gating (`admin123` via `X-Admin-Token` headers) for administrative operations (delete, restore, verify, CSV export). Verified and compiled utilizing built-in test suites.

### Implemented Auditor Allocation and User Access Control
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`, `alpha_survey/static/app.js`, `scratch/test_survey_api.py`
- **Strategic Intent**: Establish a coordinator-driven auditor management pipeline. Added database seeding for initial auditor accounts, designed secure admin user management endpoints (`GET`, `POST`, `DELETE` under `/api/admin/users`) protected by admin passcode validation, integrated a dynamic user allocation modal in the coordinator panel, and updated the client-side login screen to be strictly credentials-based. Updated integration test suite to verify all auth, login, allocation, and revocation paths.

### Corrected Admin Mode Toggle Layout Stretching
- **Files**: `alpha_survey/static/index.html`
- **Strategic Intent**: Restructured the toggle switch markup to align with designed `.toggle-container` and `.switch` relative classes in `styles.css`. This prevents the absolute-positioned `.slider` element from stretching across the entire width of the page container.

### Implemented Auditor-Scoped Views and Administrative Filter
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`, `alpha_survey/static/app.js`
- **Strategic Intent**: Limit default user visibility to only their own inputs to ensure data privacy and scoping. Modified the FastAPI `/api/sources` and `/api/stats` endpoints to accept optional `input_by` query parameters. Modified the frontend to automatically filter tables and platform/country breakdowns by the logged-in user. Added a dropdown select in the Admin panel allowing coordinators to filter the full dataset by any active auditor or view all users' combined stats, directory, and CSV exports. Seeded default testing account `andrew` / `1234`.

## 2026-05-21

### Expanded Ingestion Source Taxonomy Classifications
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`
- **Strategic Intent**: Expand the publisher classification types and thematic topics to cover missing segments and handle unclassifiable sources. Added new validation schemas for consumer news, culture/music/art, gossip/celebrity, newsfluencers, mainstream publications, sports, technology/science, PR/News agency, and other, making sure backend validator and frontend dropdown selects remain in sync.

### Added Admin Activity Log Download Button
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`, `alpha_survey/static/app.js`, `scratch/test_survey_api.py`
- **Strategic Intent**: Provide administrative coordinators with direct access to download the backend activity log file (`survey_activity.log`) from the admin panel interface. Added a secured endpoint `/api/admin/logs` gated by admin passcode, added a matching "Download Activity Log" button visible only in admin mode, wired the frontend download trigger, and expanded integration tests to verify successful file retrieval.

### Configured Environment-Aware Storage & Cloud Run Native GCS Volume Mount Support
- **Files**: `alpha_survey/app.py`, `alpha_survey/HANDOFF.md`, `alpha_survey/requirements.txt`, `alpha_survey/Dockerfile`
- **Strategic Intent**: Hardened application portability by making SQLite database and log file paths configurable via environment variables (`SURVEY_DB_PATH` and `SURVEY_LOG_DIR`). Created deployment scaffolding (`Dockerfile`, `requirements.txt`) and documented step-by-step instructions for native Google Cloud Run GCS volume mounts in `HANDOFF.md` to support stateless, persistent container scaling.

### Implemented Fediverse Ingestion Platform Type
- **Files**: `alpha_survey/app.py`, `alpha_survey/static/index.html`, `alpha_survey/static/app.js`, `alpha_survey/static/styles.css`, `alpha_survey/HANDOFF.md`, `scratch/test_survey_api.py`
- **Strategic Intent**: Add support for logging Fediverse links (e.g. Mastodon profile/channel URLs) to the regional survey tool. Updated the backend Pydantic validators, ID serial generation prefix maps (added `FED` mapping code), and stats aggregation logic. Updated the frontend UI platform select dropdowns, platform filters, badge colors (using new `.badge-orange` style rule), and placeholder info descriptions. Added a new verification test case validating that Fediverse records ingest correctly, auto-generate matching IDs, and are counted properly in stats.


### Implemented Fediverse Ingestion Module and Pipeline Integration
- **Files**: `alpha/fediverse_ingester.R`, `alpha/pipeline_runner.R`, `scratch/test_fediverse.R`
- **Strategic Intent**: Add capability to ingest public posts from Fediverse/Mastodon handles (e.g. `@username@domain`) into the Push Media pipeline. Features public RSS feed resolving with primary/fallback URLs, HTML stripping, stable MD5 hash UIDs, and integration in `pipeline_runner.R`. Verified via `scratch/test_fediverse.R`.

### Implemented Target URL Capture Across Pipeline
- **Files**: `alpha/db_manager.R`, `alpha/pipeline_runner.R`, `alpha/rss_ingester.R`, `alpha/fediverse_ingester.R`, `alpha/subscription_ingester.R`, `alpha/telegram_ingester.R`, `alpha/email_ingester.R`, `scratch/run_integration_test.R`, `scratch/test_fediverse.R`
- **Strategic Intent**: Add a `url` column to the `newsletters` DuckDB table schema with automatic `ALTER TABLE` migrations for backward compatibility. Update all ingestion modules (Gmail, RSS, Telegram, Substack/Ghost, and Fediverse) to capture and propagate original source/article URLs. Integrate URL bindings in database insertion queries of the pipeline runner and verify with mock/live integration tests.

### Implemented External Link Detection and Scraping for Fediverse Posts
- **Files**: `alpha/fediverse_ingester.R`, `scratch/test_fediverse.R`
- **Strategic Intent**: Add capability to detect, filter, and scrape external target URLs shared inside Fediverse/Mastodon posts. Uses structural path filtering in `is_actual_article_link` to ignore Fediverse profiles, statuses, hashtags, and media attachments. Reuses `httr2` and `rvest` to fetch and extract full webpage text, appending it to the record's body and setting the target `url` column to the external link for improved LLM summarization and entity extraction. Verified via mock and live tests.

## 2026-05-22

### Adjusted Project Rollout Schedule and Timeline Dates
- **Files**: `rollout_plan/rollout_plan.md`, `rollout_plan/rollout_gantt.csv`, `rollout_plan/gantt_chart.png`
- **Strategic Intent**: Align the 6-month project rollout schedule to run precisely from May 15, 2026 to October 31, 2026. Adjusted all phase breakdowns, durations, and Gantt charts to conform to this specific timeline.

### Corrected Email Ingestion Date Parsing and Implementation of Results Timeline
- **Files**: `alpha/pipeline_runner.R`, `alpha/static/dashboard.js`, `scratch/backfill_raw_emails.R`, `scratch/backfill_email_dates.R`
- **Strategic Intent**: Ensure email dates stored in `datetime` reflect the actual email send/header date rather than falling back to ingestion system time due to `as.POSIXct` parsing failure of RFC 2822 format. Added a line chart showing search results counts grouped by actual email/item dates dynamically updating in the frontend. Created a date correction utility script and updated the backfiller to parse dates from the fetched headers.

### Updated Technical Handoff Documentation
- **Files**: `HANDOFF.md`
- **Strategic Intent**: Document the newly integrated Regional Ingestion Survey Application and 6-Month Project Rollout Plan in the central workspace handoff guide. Updated the project directory structure, listed operational setup commands for the survey tool, described the scoped data flows, and aligned roadmap details to aid smooth handover and replication.
## 2026-06-10

### Implemented MIME Header Decoding and Quoted-Printable Parser for Email Ingestion
- **Files**: `alpha/email_ingester.R`
- **Strategic Intent**: Add RFC 2047 MIME encoded-word parsing (`decode_mime_header`) to correctly decode Base64 and Quoted-Printable Subject and From headers, correcting raw encoding issues in email title fields (such as in body13912). Implement a pure, native R Quoted-Printable decoder (`decode_qp`) to replace non-existent package dependencies, fixing base64/quoted-printable payload parsing bugs in bodies and headers (such as body13914, body13915, and body13918).

### Hardened LLM Prompts for Language Detection and Original Summaries
- **Files**: `alpha/prompts.R`
- **Strategic Intent**: Refine instructions in the system prompts to enforce strict mapping between the actual written language of the source text and the `detected_language` field. Add strict instructions to write `summary_orig` in English if the detected source language is English, preventing erroneous translations into French/German based on semantic country topics.


### Resolved RFC 2822 Header Folding, Boundary Slicing, QP Decoding Order, and English Summary Consistency
- **Files**: `alpha/email_ingester.R`, `alpha/pipeline_runner.R`, `scratch/test_gmail_ingestion.R`
- **Strategic Intent**: Add RFC 2822 header unfolding to handle multiline subject/from/date headers (fixing title truncation). Fix adjacent MIME encoded words decoding space issue. Reorder transfer encoding (QP/Base64) decoding to occur before HTML parsing to prevent malformed tags/CSS bleeding. Fix boundary regex splits to use `fixed()` to escape boundary strings containing regex special characters. Programmatically override `summary_orig` to match `summary_en` when `detected_language == "en"` to prevent translation instruction degradation by smaller LLMs.

### Added Warning-Free Date Parsing to RSS Ingest Module
- **Files**: `alpha/rss_ingester.R`
- **Strategic Intent**: Add `parse_rss_date` helper function utilizing standard R `as.POSIXct` calls prior to `lubridate` fallback. This handles RFC 2822 format variations (e.g. Dakaractu with/without commas) and avoids PCRE2 duplicate named subpatterns compilation warnings on modern R environments.

## 2026-06-11

### Enforced Ingestion Tool Platform Tagging
- **Files**: `alpha/pipeline_runner.R`
- **Strategic Intent**: Enforce reliable content-type tagging based on the actual tool used for ingestion (email, rss, telegram, subscription, fediverse) by injecting a platform attribute during raw record retrieval. This overrides LLM-derived classification tags in the DuckDB `content_type` field, preventing generic "Article" or "Newsletter" designations.

### Implemented Canonical Link Extraction for Emails
- **Files**: `alpha/email_ingester.R`
- **Strategic Intent**: Parse email HTML structure during body conversion to detect and extract the "View in browser" or "Read online" URLs, setting it as the canonical URL metadata field for the email record. This enables cross-channel URL-based deduplication against RSS and web scraped resources.

### Embedded Extracted Topics and Themes for Semantic Vector Search
- **Files**: `alpha/pipeline_runner.R`, `scratch/reembed_corpus.R`
- **Strategic Intent**: Modify the embedding text construction in both the runtime pipeline orchestrator and the re-embedding maintenance utility script to append the extracted `topics` and `themes` metadata below the text summaries. This forces the vector embeddings to semantically index these structural markers, allowing vector search queries to match topic/theme keywords natively without schema migrations.

### Created Central Pipeline Models Manifest
- **Files**: `manifest.json`, `alpha/config.R`
- **Strategic Intent**: Create a central, project-level model configuration manifest `manifest.json` outlining active models/providers across Ingestion, Embeddings, and Evaluation phases. Update the R configuration layer (`alpha/config.R`) to parse this file and use its settings as fallback defaults, improving portability and easing pipeline model maintenance.

### Configured LFM-2 24B as Default Extraction Model
- **Files**: `manifest.json`
- **Strategic Intent**: Switch the default metadata extraction model from DeepSeek-Chat to Liquid LFM-2 24B (`liquid/lfm-2-24b-a2b`) in the central manifest to leverage its significantly lower token pricing ($0.03/$0.12 per 1M tokens) for cost-efficient bulk ingestion.

### Implemented Blue-Green Database Swapping in Pipeline Runner
- **Files**: `alpha/pipeline_runner.R`
- **Strategic Intent**: Modify the database connection and termination blocks in `run_pipeline` to perform ingestion and writes to a temporary workspace database (`newsletters.db.temp`) instead of the active production database. Implement an exit hook that closes the connection and performs an atomic file rename (swap) over the active database path only upon a 100% successful run. This guarantees reader uptime for the FastAPI server and prevents locks during active ingestion runs.

### Optimized Database Lock Concurrency via In-Memory Processing & Transactions
- **Files**: `alpha/pipeline_runner.R`, `scratch/ingest_500_emails.R`
- **Strategic Intent**: Transition from Blue-Green database file copies to a pure in-memory extraction model. Process all long-running LLM and embedding generation steps in memory, keeping database connections entirely closed during API calls. Open a single, short-lived transaction at the very end to batch insert the processed records in a few milliseconds. This completely eliminates file copy overhead and guarantees that the database remains unlocked and read-queryable by the dashboard throughout active ingestion runs.

### Prevented OpenRouter LFM-2 Infinite Token Generation Loops
- **Files**: `alpha/model_adapter.R`
- **Strategic Intent**: Add `max_tokens = 1500` to OpenRouter request payloads to safeguard against infinite output token generation loops. Under certain inputs in JSON mode, the `liquid/lfm-2-24b-a2b` model would loop repeating character sequences (e.g. `\u2014` or `eshini`) endlessly, inflating output token usage to over 26k tokens, incurring unnecessary costs, and stalling the ingestion runner. This constraint limits output length to a safe ceiling sufficient for the JSON extraction schema. Added a regex pattern match (`(.{3,})\\1{8,}`) to detect recurring characters and validation checks for JSON truncation, automatically triggering up to 3 retries (resubmissions) to guarantee a clean, complete response before proceeding.

### Refined Analysis Prompts to Eliminate Meta-Referential Summary Commentary
- **Files**: `alpha/prompts.R`
- **Strategic Intent**: Refine instructions in the metadata extraction system prompt to explicitly prohibit self-referential introductory phrases (e.g. \"The article discusses\", \"this text describes\", \"the author covers\"). Enforce direct summary writing in both English and original language fields to improve narrative search quality and eliminate conversational filler.

### Implemented Dashboard Enhancements, Multi-Select Type, and EML Downloader
- **Files**: `alpha/email_ingester.R`, `alpha/app.py`, `alpha/static/index.html`, `alpha/static/dashboard.js`, `scratch/backfill_raw_emails.R`
- **Strategic Intent**: Enforce dynamic fallback publisher name extraction from From headers instead of hardcoded 'Email Intake'. Expand the FastAPI REST backend to support raw email download endpoints (`/api/newsletters/{uid}/download-eml`) and query filtering across list parameters (`content_type`), sorting criteria (`similarity` vs `date`), and date ranges (`start_date` and `end_date`). Build interactive multi-select pills on the dashboard front-end alongside date range filters and a download EML button, verifying integration via automated browser subagents. Create a background migration script to backfill existing records with raw MIME payloads from Gmail IMAP.





## 2026-06-12

### Transitioned to Python-Based Low-Latency IMAP Ingestion and Real-Time Daemon
- **Files**: `alpha/email_ingester.py`, `alpha/email_daemon.py`, `alpha/model_adapter.py`, `alpha/prompts.py`, `alpha/entity_resolver.py`, `scratch/fast_ingest_mailbox.py`, `alpha/pipeline.md`
- **Strategic Intent**: Transitioned email ingestion from R's `mRpostman` to Python's `imapclient` library. Implemented a singleton persistent IMAP connection manager and a background daemon (`email_daemon.py`) using **IMAP IDLE** to receive real-time notifications of new incoming emails. Rewrote historical bulk ingestion into a parallelized Python script (`fast_ingest_mailbox.py`) that utilizes selective fetch commands (fetching only `ENVELOPE`, `BODY[TEXT]`, and `RFC822.HEADER` in a single IMAP call) and parses MIME payloads locally in memory via the Python standard `email` package. This completely eliminates concurrent connection overhead, stays within Google's 2.5 GB daily download limit, and bypasses Gmail IMAP command rate limit throttling (`[THROTTLED]` errors). Logged structural documentation in `alpha/pipeline.md`.

### Hardened IMAP and RSS Ingestion Against Null Payloads and LLM Timeouts
- **Files**: `alpha/email_ingester.py`, `alpha/pipeline_runner.R`
- **Strategic Intent**: Added Python regex rules `[\u200b\u200c\u200d\uFEFF\u200e\u200f]+` to `email_ingester.py` to aggressively strip invisible unicode formatting characters (e.g., zero-width joiners) prevalent in marketing emails (like News24). These consecutive duplicate invisible characters were systematically causing state-space language models (Liquid LFM) to hit recursive collapse states and endlessly repeat tokens until timeout. Also modified `pipeline_runner.R` to collapse the `parsed_analysis$entities` JSON arrays via `paste(..., collapse = ", ")` before duckDB insertion to explicitly prevent `dbBind` length mismatch errors, improving pipeline durability for the RSS ingestion watchdog.

## 2026-06-14

### Increased LLM max_tokens to Prevent JSON Truncation on Large Digest Emails
- **Files**: `alpha/model_adapter.py`
- **Strategic Intent**: Raised `max_tokens` from 1,500 to 4,000 in OpenRouter request payloads. Forensic log analysis revealed that large digest-style newsletters (e.g., News24 "Top 10 reads" containing 10+ summarized stories) were exceeding the token ceiling during JSON generation, causing the model to be cut off mid-entity-list. This produced malformed JSON (`finish_reason: length`) and triggered three-strikes failures. The 4,000 limit accommodates the full dual-language summary + entities + topics + themes + keywords JSON structure even for the largest observed inputs.

### Fixed Dashboard Keyword Search Binder Error (Obsolete Column References)
- **Files**: `alpha/search_parser.py`
- **Strategic Intent**: Corrected the keyword search SQL templates in `TermNode`, `PhraseNode`, and `NearNode` which referenced obsolete database columns (`summary_en`, `content`) that do not exist in the Phase 2 DuckDB schema. Updated all references to use the correct column names (`summary`, `original_language_summary`, `raw_email`). This was the root cause of the "Binder Error: Referenced column summary_en not found" crash on all keyword searches.

### Implemented Server-Side Pagination, Total Count, and Full Timeline Distribution
- **Files**: `alpha/app.py`, `alpha/static/dashboard.js`, `alpha/static/styles.css`
- **Strategic Intent**: Redesigned the search API to support proper pagination with `offset`/`limit` parameters, return a `total_count` of all matching records (not just the page), and include a `timeline` field containing date-aggregated counts for the entire result set. The frontend now displays the true total match count (e.g., "Found 6,085 matches — showing 1–20"), renders the timeline chart from server-side aggregated data covering all matches, and provides First/Prev/Next/Last pagination controls. The sensitivity threshold is now passed to the backend and applied at the SQL level, eliminating the previous client-side post-filtering that silently discarded results and produced misleading counts.

## 2026-06-16

### Fixed Pipeline Runner Translation Syntax Error and Added Generic LLM Fallback
- **Files**: `alpha/pipeline_runner.R`, `alpha/translation_ollama.R`, `alpha/config.R`
- **Strategic Intent**: Corrected corrupted translation lines and duplicate blocks in `pipeline_runner.R` causing syntactic crashes. Restructured the pipeline translation step to focus on translating original language summaries rather than full text bodies to preserve resource limits. Implemented a robust `translate_generic` function in `translation_ollama.R` as an API fallback to translate summaries using the primary extraction LLM (e.g. Liquid LFM-2) when local Ollama models fail or are unavailable. Added a configurable `translation_model` parameter to `config.R` mapping to the `TRANSLATION_MODEL` environment variable, enabling dynamic selection of local translation models (like MzansiLM vs AfriqueQwen) in the pipeline.

## 2026-06-17

### Acquired, Converted, Quantized, and Benchmarked `AfriqueQwen-14B-multiturn` for isiXhosa Translation
- **Files**: `scratch/download_multiturn.py`, `scratch/convert_and_quantize.sh`, `alpha/translation_ollama.R`, `scratch/test_afriqueqwen.R`
- **Strategic Intent**: Previous local translation models were rejected for quality reasons: `AfriqueQwen-14B-Fact-full` returns classification tokens (not translations); `mzansilm` (125M) outputs advertisement noise. `AfriqueQwen-14B-multiturn` (conversational instruction-tuned) was identified as the superior candidate. Full acquisition pipeline executed on external Lexar drive (891 GB) to bypass local SSD constraint (23 GB free): (1) downloaded 28 GB safetensors via `huggingface_hub` with retry logic to survive TCP stalls; (2) converted to f16 GGUF via `llama.cpp/convert_hf_to_gguf.py`; (3) quantized to Q4_K_M (9.0 GB) via compiled `llama-quantize`; (4) registered as `afriqueqwen-14b-multiturn` in Ollama with system prompt for translation context.

### Fixed HTTP Timeout and `keep_alive` Type Error in `translation_ollama.R`
- **Files**: `alpha/translation_ollama.R`
- **Strategic Intent**: Two bugs prevented the 14B model from working via the R HTTP client: (1) no read timeout was set — `httr2::req_perform` used its default short timeout (~10s), which expired before the CPU-bound model could load and respond (~3–10 min); fixed by adding `httr2::req_timeout(req, seconds = 1200)`. (2) `keep_alive = "-1"` was serialised as a JSON string, which Ollama rejects with HTTP 400; fixed by using R integer `-1L`, which `httr2` correctly serialises as a JSON integer.

### Improved Translation Prompt for Instruction-Tuned Models
- **Files**: `alpha/translation_ollama.R`
- **Strategic Intent**: The previous generic prompt ("Translate the following xh text to English, preserving idioms...") caused the instruction-tuned model to mix in hallucinated fragments. Replaced with a structured completion-style prompt specifying source language as "isiXhosa", demanding output-only English, and anchoring completion with "English translation:" to prevent preamble generation. Benchmark confirmed clean, accurate output with zero noise across 4 isiXhosa test sentences.

### Benchmark Results: `afriqueqwen-14b-multiturn` (Q4_K_M, CPU, warm model)
- **Files**: `scratch/test_afriqueqwen.R` (diagnostic output only — not pipeline code)
- **Strategic Intent**: Document verified translation quality for audit trail. All 4 test sentences produced accurate, clean English translations with no hallucination. Average inference time: ~53s/sentence on Apple Silicon CPU (warm model). Model deemed production-ready for alpha pipeline deployment via `TRANSLATION_MODEL=afriqueqwen-14b-multiturn`.

## 2026-06-21

### Ingester Interface Consistency: Self-Describing `platform` and `raw_source` Fields
- **Files**: `alpha/email_ingester.R`, `alpha/rss_ingester.R`, `alpha/fediverse_ingester.R`, `alpha/telegram_ingester.R`, `alpha/subscription_ingester.R`, `alpha/pipeline_runner.R`
- **Strategic Intent**: All five ingesters now return self-describing records containing `platform` (e.g. `"email"`, `"rss"`, `"fediverse"`, `"telegram"`, `"subscription"`) and `raw_source` (the original unparsed content: raw MIME for email, raw XML description for RSS/fediverse/subscription, raw HTML text for telegram). Previously `platform` was stamped externally by `pipeline_runner.R` and only the email ingester returned a `raw_email` field — the other four silently fell back to the processed `body` text. The runner now reads `item$platform` and `item$raw_source` directly from ingester records instead of injecting or guessing. The DB column name `raw_email` is preserved for backward compatibility.

### Removed Hardcoded isiXhosa Few-Shot Prompts from Model Adapter
- **Files**: `alpha/model_adapter.R`, `alpha/translation_ollama.R`
- **Strategic Intent**: The general-purpose model adapter (`model_adapter.R`) contained hardcoded isiXhosa-specific few-shot examples in the Ollama `use_generate` branch, violating model-agnosticism and hardcoding a single source language. These were removed; the `use_generate` branch now concatenates `system_prompt + user prompt` generically. The language-specific translation prompt logic was already correctly handled by `translation_ollama.R`, which was updated to use the actual detected language code (mapped from ISO 639-1 to human-readable names for all 7 configured low-resource languages: xh, zu, tn, rw, st, ss, wo) instead of hardcoding "isiXhosa".

### Ingester Commenting & Documentation Audit and Entity Data-Type Regression Fix
- **Files**: `alpha/email_ingester.R`, `alpha/rss_ingester.R`, `alpha/fediverse_ingester.R`, `alpha/subscription_ingester.R`, `alpha/translation_ollama.R`, `alpha/prompts.R`, `alpha/pipeline_runner.R`
- **Strategic Intent**: Standardize and complete Roxygen documentation blocks and package-level imports across the modified ingestion and translation modules (specifically resolving missing `translate_ollama` comments and unlisted `xml2` namespace imports). Revert the `entities` data-type regression in `pipeline_runner.R` that collapsed the LLM-extracted data frame into a flat string under a legacy/obsolete database schema constraint. Keeping `entities` as a data frame ensures that the `is.data.frame` check passes during the database write loop and allows entities to be correctly resolved and written to the `entities` table.

### Structural Performance and Reliability Hardening
- **Files**: `alpha/run_cron.R`, `alpha/entity_resolver.R`, `alpha/model_adapter.R`, `alpha/pipeline_runner.R`
- **Strategic Intent**: Resolve key operational and performance risks in the pipeline:
  1. **Query Optimization (`run_cron.R`)**: Switched dynamic source querying from a heavy DuckDB instance (which relied on loading an external SQLite scan extension) to a native RSQLite DBI connection, improving start times and reducing dependencies.
  2. **Algorithm Acceleration (`entity_resolver.R`)**: Replaced slow pure-R string looping routines ($O(N)$ overhead) in Jaro and Jaro-Winkler calculations with the compiled, high-performance C-based `stringdist` library.
  3. **Timeout Protection (`model_adapter.R`)**: Added explicit `httr2::req_timeout()` limits to all external completion (120s) and embedding (60s) API calls to prevent indefinite pipeline hangs.
  4. **Memory Reduction (`pipeline_runner.R`)**: Modified the raw records collection layer to accumulate fetched records in nested lists and perform a single `do.call(c, ...)` flatten at the end rather than growing lists incrementally via copy-on-append `c()`.

### Dead Import Cleanup (`run_cron.R`)
- **Files**: `alpha/run_cron.R`
- **Strategic Intent**: Remove vestigial `library(duckdb)` import that remained after the RSQLite migration. This file no longer calls any DuckDB functions directly — the DuckDB dependency is loaded downstream via `source("alpha/pipeline_runner.R")`. The dead import caused an unnecessary DuckDB library load on every cron run start.

### Documentation Hardening: Pipeline Architecture and README
- **Files**: `alpha/pipeline.md`, `README.md`
- **Strategic Intent**: Comprehensive rewrite of project documentation to accurately reflect the current codebase state after all performance, reliability, and interface consistency work. Key corrections:
  1. **`pipeline.md`**: Updated Mermaid architecture diagram to show `run_cron.R` → `pipeline_runner.R` flow with RSQLite source loading. Added ingester interface table documenting uniform record fields. Documented in-memory processing model, timeout enforcement, `stringdist`-based entity resolution, translation module with SQLite cache, and manifest-driven configuration.
  2. **`README.md`**: Corrected memory limit from `512MB` to `1.5GB`. Added `run_cron.R` as the primary daily entry point (replacing direct `pipeline_runner.R` invocation). Added Python email daemon, survey application, `manifest.json`, `translation_ollama.R`, `search_parser.py`, and `run_cron.R` to directory tree. Expanded environment variable documentation to include `LLM_PROVIDER`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `TRANSLATION_MODEL`, `FORENSIC_LOG_PATH`, and `DUCKDB_PATH`. Added `stringdist` GPL-3 licensing note.

### Implemented OpenRouter Routing for Translation & Configured Qwen 3.6
- **Files**: `alpha/translation_ollama.R`, `alpha/credentials.json`
- **Strategic Intent**: Add support for translating low-resource African languages using OpenRouter models (specifically Qwen 3.6 Plus) by parsing model slugs and routing them to OpenRouter's completions API. Set `TRANSLATION_MODEL` to `qwen/qwen3.6-plus` in the credentials file.

### Implemented Multimodal Vision/OCR Processing and Textless Bypass Logic for Telegram Posts
- **Files**: `alpha/config.R`, `alpha/telegram_ingester.R`, `alpha/email_ingester.R`, `alpha/rss_ingester.R`, `alpha/fediverse_ingester.R`, `alpha/subscription_ingester.R`, `alpha/model_adapter.R`, `alpha/prompts.R`, `alpha/pipeline_runner.R`
- **Strategic Intent**: Add support for Option A (vision-based OCR processing via OpenRouter) for Telegram posts containing images.
  1. **Config**: Added `VISION_MODEL` environment variable (defaults to `qwen/qwen3.6-plus`).
  2. **Ingesters**: Extracted image URLs (`image_url`) from `.tgme_widget_message_photo_wrap` elements in `telegram_ingester.R` using regex on style tags, and supported fetching textless posts that contain images. Updated other ingesters to return `image_url = NULL` for uniform schema compliance.
  3. **Model Adapter**: Added `image_url` parameter to `generate_completion` and routed requests to the configured vision model using a standard OpenRouter multimodal JSON structure.
  4. **Prompts**: Added `contains_text` boolean to the JSON extraction prompt.
  5. **Pipeline**: Handled vision responses by bypassing translation if `contains_text` is false, and appending an OCR footnote to textful image summaries.

### Hardened Generic Translation Fallback
- **Files**: `alpha/translation_ollama.R`
- **Strategic Intent**: Prevent French (or other original languages) from silently overwriting the English summary field when the primary translation model (e.g. Liquid LFM-2) returns empty responses or errors. Designed a multi-stage fallback: it attempts the primary model first, falls back to Qwen 3.6 Plus via OpenRouter if that fails or returns empty, and prepends a clear `[Translation Failed - Original Language: ...]` warning header to the original text if both fail.

### Hardened Database Schema and Removed Buggy Foreign Keys
- **Files**: `alpha/db_manager.R`
- **Strategic Intent**: Removed the `FOREIGN KEY` constraint on the `entities(uid)` table to prevent DuckDB catalog assertion failures (`INTERNAL Error: Attempting to dereference an optional pointer that is not set` in `VerifyForeignKeyConstraint` during updates/deletes). DuckDB's internal implementation of `UPDATE` via `DELETE + INSERT` triggers buggy foreign key checks that permanently invalidate database files on disk under certain conditions. This structural change ensures reliable database writes and updates.


