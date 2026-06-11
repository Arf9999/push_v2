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
- **Strategic Intent**: Add capability to ingest public posts from Fediverse/Mastodon handles (e.g. `@username@domain`) into the Narrative Intelligence pipeline. Features public RSS feed resolving with primary/fallback URLs, HTML stripping, stable MD5 hash UIDs, and integration in `pipeline_runner.R`. Verified via `scratch/test_fediverse.R`.

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
