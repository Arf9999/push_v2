#!/usr/bin/env bash
# =============================================================================
# run_ingest_watchdog.sh
# Watchdog supervisor for fast_ingest_mailbox.py
# Auto-restarts on any crash. Logs all events with timestamps.
# Usage: nohup bash scratch/run_ingest_watchdog.sh > scratch/watchdog.log 2>&1 &
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/.venv/bin/python"
INGEST_SCRIPT="$SCRIPT_DIR/fast_ingest_mailbox.py"
LOG_DIR="$SCRIPT_DIR"

MAX_RESTARTS=20             # Hard ceiling on total restarts (prevents runaway loops)
RESTART_COOLDOWN_SECS=60   # Wait between restarts (separate from IMAP overquota wait)
restart_count=0

ts() { date "+%Y-%m-%d %H:%M:%S"; }

echo "[$(ts)] [WATCHDOG] ============================================="
echo "[$(ts)] [WATCHDOG] Ingestion Watchdog Starting"
echo "[$(ts)] [WATCHDOG] Project: $PROJECT_DIR"
echo "[$(ts)] [WATCHDOG] Script:  $INGEST_SCRIPT"
echo "[$(ts)] [WATCHDOG] Max restarts: $MAX_RESTARTS"
echo "[$(ts)] [WATCHDOG] ============================================="

cd "$PROJECT_DIR" || { echo "[$(ts)] [WATCHDOG] [FATAL] Cannot cd to $PROJECT_DIR"; exit 1; }

while true; do
    RUN_LOG="$LOG_DIR/ingest_run_$(date +%Y%m%d_%H%M%S).log"
    echo "[$(ts)] [WATCHDOG] --- Run #$((restart_count + 1)) starting --- Log: $RUN_LOG"

    # Reprocess flagged records first
    echo "[$(ts)] [WATCHDOG] --- Reprocessing Flagged Records ---"
    "$PYTHON" -u "$SCRIPT_DIR/reprocess_flagged.py" >> "$RUN_LOG" 2>&1

    # Run with unbuffered output so log is written in real time
    "$PYTHON" -u "$INGEST_SCRIPT" >> "$RUN_LOG" 2>&1
    EXIT_CODE=$?

    LAST_LINES=$(tail -5 "$RUN_LOG")

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(ts)] [WATCHDOG] === Ingestion completed successfully (exit 0). Watchdog exiting. ==="
        echo "[$(ts)] [WATCHDOG] Last log lines:"
        echo "$LAST_LINES"
        exit 0
    fi

    # Check if it completed normally (no new emails = success)
    if grep -q "No new emails to ingest. Complete." "$RUN_LOG"; then
        echo "[$(ts)] [WATCHDOG] === Inbox fully ingested. No new emails. Watchdog exiting. ==="
        exit 0
    fi

    restart_count=$((restart_count + 1))
    echo "[$(ts)] [WATCHDOG] [ERROR] Script exited with code $EXIT_CODE (restart $restart_count / $MAX_RESTARTS)"
    echo "[$(ts)] [WATCHDOG] Last 5 log lines from failed run:"
    echo "$LAST_LINES"

    if [ $restart_count -ge $MAX_RESTARTS ]; then
        echo "[$(ts)] [WATCHDOG] [FATAL] Max restarts ($MAX_RESTARTS) reached. Giving up."
        echo "[$(ts)] [WATCHDOG] [FATAL] Review logs in $LOG_DIR for the root cause."
        exit 2
    fi

    echo "[$(ts)] [WATCHDOG] Cooling down ${RESTART_COOLDOWN_SECS}s before restart..."
    sleep $RESTART_COOLDOWN_SECS
done
