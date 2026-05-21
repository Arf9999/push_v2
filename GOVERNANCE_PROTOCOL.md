# 🏛️Newsletetr_phase2: Project Governance Protocol

**Version**: 1.0 (Sandbox Segregated)

## 💎 1. The Principle of Sacrosanct Rows

* **Unique Key Enforcement**: Every dataset must contain a guaranteed unique identifier for every row (e.g., `Resource Id`). If no unique key is provided in the source, a synthetic `Engine_Id` must be generated immediately upon ingestion.
* **Zero Deletion**: Input rows are immutable. We never delete records from the original corpus.
* **Contextual Preservation**: Even 'out-of-scope' or 'silent' nodes (no extraction) must remain in the dataset. They provide the necessary structural density for network and statistical baselines.
* **Metadata Integrity**: All original source metadata columns must be preserved as a backup file, even if not pushed to production database

## 🗂️ 2. Safe Mutation & Archival

* **Snapshot-Before-Action**: No script may overwrite a dataset (`.rds` or `.csv`) without first creating a timestamped backup in the `output/archive/` directory.
* **Intelligence Layering**: Analysis must be performed as an 'Append Only' operation.We add new columns or fields, never replacing original data.
* **Traceability**: Every analytical row or table must maintain its original unique identifier (e.g., `Resource Id` or `Mention Id`) to ensure 1:1 mapping back to the raw source.
* **R-Native RDS Operational Mandate**: Using `.rds` as the primary file format for all inter-script data communication ensures that all R dataframe and variable types remain perfectly consistent. By saving as CSV and then ingesting them, there is a high risk that variables are not typed correctly or contents are truncated. Flat CSV files are strictly reserved as export/backup formats, never as the source of truth for downstream pipeline steps.

## 🌍 3. Strategic Portability & Universal Resilience

* **Zero Hardcoding Policy**: Prompts, examples, and instructions must never contain dataset-specific entities (e.g., specific country names or publications). Use generic placeholders or inject context dynamically via the project `manifest.json` if it exists.
* **Agnostic Architectures**: Logic must be designed to handle data variation gracefully. If a dataset or ingestion is large enough to cause truncation or timeouts, implement batched processing and checkpointing as a standard, universal pattern rather than a one-off fix.

* **Anti-Patch Pipeline Hardening**: Code corrections must address the systemic cause of an issue rather than being symptomatic patches targeting a single symptom or specific run artifact. Every code change must focus exclusively on the robustness, portability, and long-term replicability of the pipeline. Ad-hoc symptomatic patches to output files, intermediate data, or cosmetic overrides are strictly prohibited as they break downstream pipeline integrity.

## 🚀 4. Pipeline Integrity (Sequential Batching & Experimental Isolation)

* **Context Safety**: Long-form extraction must be performed in batches of 1,000 to prevent LLM context drift and semantic decay.
* **Hardware Isolation**: To prevent VRAM corruption, local large-model extractions should run sequentially (Process-Locked) rather than in parallel.
* **Human-in-the-Loop Monitoring**: Spawning interactive terminals for batch progress ensures real-time auditability of the extraction 'heartbeat'.
* **Forensic LLM Response Logging**: A `FORENSIC_LOG` of LLM script responses must be saved. For thinking processes, this should document the process.
* **Alpha Experimental Features Isolation & Sandbox Segregation**: Any new or experimental functionality proposed for the pipeline must be designated as **"Alpha"** and developed in a segregated sandbox environment.
  * **User-Audited Alpha Sandbox (`alpha/` directory)**: Any candidate pipeline scripts, logic extensions, or prototype modules intended for eventual production integration and manual review MUST reside in the `alpha/` root directory. These scripts are designated for manual user audit and formal promotion.
  * **Agent Temporary Utility Directory (`scratch/` directory)**: Any agent-created temporary sidecar scripts, database/API test sandboxes, debugging tools, and active automated diagnostic scripts must reside strictly in the `scratch/` root directory.
  * **Output Directory Separation**: Agent diagnostic outputs must go to `scratch/` or `projects/<Project>/scratch/`. Candidate Alpha experimental feature outputs must be written to isolated directories (e.g., `projects/<Project>/alpha/`).
  * **Zero Contamination**: Alpha sandbox and scratch scripts **NEVER** modify or edit existing production pipeline scripts; they are strictly additive and side-by-side.
  * **Promotion Pathway**: Alpha feature scripts can only transition to **"Beta"** and be integrated into the main `scripts/` pipeline upon explicit, manual instruction and approval from the user.

## 5. Error management and patching


* **Agent Error Resolution Mandate**: If an AI agent or developer encounters a runtime error:
  1. The agent **MUST** trace the error back to its systemic root cause before creating scratch files or writing patches.
  2. If the issue is a genuine code error in an existing script that is already working for other datasets, the agent **MUST NOT** modify the script immediately.
  3. Instead, the agent **MUST** present the user with a detailed breakdown explaining:
     * The exact **Root Cause** of the error.
     * The **Proposed Fix** and how it corrects the system.

  4. The agent **MUST obtain explicit user confirmation** and approval before making any modifications to the production pipeline code.
* **Mandatory Documentation**: Every approved change to core R/Python scripts or LLM prompts must be logged in `CODE_AUDIT_LOG.md`.
* **Rationale Capture**: Logs must specify the *strategic intent* behind the logic change (e.g., 'Switching to Resource Id join for 100% volume recovery').
* **Version Traceability**: Every major pipeline run must reference the logic version documented in the audit log to ensure forensic reproducibility.

---
*This protocol ensures that all project outputs are stable, audit-ready, and strategically grounded.*

