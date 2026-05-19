# Rules
- **No Refactoring Unless Asked**: Do not suggest "improvements" to existing logic unless they fix a specific bug.
- **Alpha Experimental Features Isolation & Sandbox Segregation**: Any new or experimental functionality proposed for the pipeline must be designated as **"Alpha"** and developed in a segregated sandbox environment.
  * **User-Audited Alpha Sandbox (`alpha/` directory)**: Any candidate pipeline scripts, logic extensions, or prototype modules intended for eventual production integration and manual review MUST reside in the `alpha/` root directory. These scripts are designated for manual user audit and formal promotion.
  * **Agent Temporary Utility Directory (`scratch/` directory)**: Any agent-created temporary sidecar scripts, database/API test sandboxes, debugging tools, and active automated diagnostic scripts must reside strictly in the `scratch/` root directory.
  * **Output Directory Separation**: Agent diagnostic outputs must go to `scratch/` or `projects/<Project>/scratch/`. Candidate Alpha experimental feature outputs must be written to isolated directories (e.g., `projects/<Project>/alpha/`).
  * **Zero Contamination**: Alpha sandbox and scratch scripts **NEVER** modify or edit existing production pipeline scripts; they are strictly additive and side-by-side.
  * **Promotion Pathway**: Alpha feature scripts can only transition to **"Beta"** and be integrated into the main `scripts/` pipeline upon explicit, manual instruction and approval from the user.
- **Anti-Patch Pipeline Hardening**: Code corrections must address the systemic cause of an issue rather than being symptomatic patches targeting a single symptom or specific run artifact. Every code change must focus exclusively on the robustness, portability, and long-term replicability of the pipeline. Ad-hoc symptomatic patches to output files, intermediate data, or cosmetic overrides are strictly prohibited as they break downstream pipeline integrity.
- **Strict Typing**: All R code must use S3 classes where applicable; all SQL must be BigQuery standard.
- **Forensic Code Audit Log**: Every change to core R/Python scripts or LLM prompts must be logged in `CODE_AUDIT_LOG.md` specifying the strategic intent.
- **Governance Compliance**: All pipeline modifications must strictly adhere to the [GOVERNANCE_PROTOCOL.md](file:///Volumes/Lexar%20R/R_projects_local/narrative_intelligence_engine/GOVERNANCE_PROTOCOL.md) regarding strategic portability and resilience.
- **R-Native RDS Operational Mandate**: Using `.rds` as the primary file format for all inter-script data communication ensures that all R dataframe and variable types remain perfectly consistent. By saving as CSV and then ingesting them, there is a high risk that variables are not typed correctly or contents are truncated. Flat CSV files are strictly reserved as export/backup formats, never as the source of truth for downstream pipeline steps.



# Slash Commands
/status: "Summarize the current technical architecture, the last 3 tasks completed, and the current active file constraints."

/reconfirm: "Check the PIPELINE_GUIDE.md and GOVERNANCE_PROTOCOL.md to ensure that current processes are compliant with the project pipeline, logic, and portability mandates."
