#!/bin/bash
# Daily Cron Ingestion Script
# Hardened for unattended execution from any directory.

# Exit on first error
set -e

# 1. Resolve absolute path of project directory dynamically
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1

LOG_FILE="scratch/cron_ingest.log"
CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")

echo "==========================================================" >> "$LOG_FILE"
echo "[${CURRENT_TIME}] Starting Pipeline Cron Job" >> "$LOG_FILE"
echo "==========================================================" >> "$LOG_FILE"

# 2. Source the Python virtual environment just in case it's needed
if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
fi

# 3. Execute the R pipeline orchestrator, redirecting all output to the log file
# Using stdbuf to ensure real-time log flushing
stdbuf -oL -eL Rscript alpha/run_cron.R >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# 4. Check for success
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] Cron Job Completed Successfully." >> "$LOG_FILE"
else
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] Cron Job FAILED with exit code ${EXIT_CODE}. Check logs." >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
exit $EXIT_CODE
