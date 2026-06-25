#!/bin/bash
# capture-dayz-error.sh
# Captures DayZ server crashes and appends to local error log
#
# Usage: ./capture-dayz-error.sh [--watch]
#   --watch    Continuously monitor for crashes
#   (no args)  One-shot capture of latest crash

set -e

# Configuration - adjust for your install
DAYZ_PROFILES="${DAYZ_PROFILES:-/c/Program Files (x86)/Steam/steamapps/common/DayZServer/profiles}"
ERROR_LOG="${ERROR_LOG:-.claude/dayz-errors.jsonl}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Find the most recent RPT file
find_latest_rpt() {
    find "$DAYZ_PROFILES" -name "*.RPT" -type f -printf '%T@ %p\n' 2>/dev/null | \
        sort -rn | head -1 | cut -d' ' -f2-
}

# Extract error context from RPT
extract_error_snippet() {
    local rpt_file="$1"
    local lines="${2:-50}"
    
    # Look for crash indicators
    local crash_start=$(grep -n "SCRIPT.*ERROR\|SCRIPT.*Can't compile\|crash\|Exception" "$rpt_file" 2>/dev/null | head -1 | cut -d: -f1)
    
    if [ -n "$crash_start" ]; then
        # Extract context around the error
        local start_line=$((crash_start - 5))
        [ $start_line -lt 1 ] && start_line=1
        
        tail -n +$start_line "$rpt_file" | head -n $lines
    else
        # Just get the last N lines
        tail -n $lines "$rpt_file"
    fi
}

# Create JSON entry for error log
create_json_entry() {
    local timestamp="$1"
    local snippet="$2"
    
    # Escape the snippet for JSON
    local escaped_snippet=$(echo "$snippet" | jq -Rs .)
    
    cat <<EOF
{
  "timestamp": "$timestamp",
  "source": "rpt_log",
  "error_snippet": $escaped_snippet,
  "captured_at": "$(date -Iseconds)"
}
EOF
}

# Append to JSONL file
append_to_log() {
    local json_entry="$1"
    
    # Ensure directory exists
    mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true
    
    # Append entry
    echo "$json_entry" >> "$ERROR_LOG"
    log_info "Error appended to $ERROR_LOG"
}

# Main capture function
capture_error() {
    log_info "Looking for DayZ server logs in: $DAYZ_PROFILES"
    
    local latest_rpt=$(find_latest_rpt)
    
    if [ -z "$latest_rpt" ]; then
        log_error "No RPT files found in $DAYZ_PROFILES"
        exit 1
    fi
    
    log_info "Latest RPT: $latest_rpt"
    
    # Get file modification time as timestamp
    local timestamp=$(stat -c %Y "$latest_rpt" 2>/dev/null || stat -f %m "$latest_rpt")
    local readable_time=$(date -d "@$timestamp" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$timestamp" '+%Y-%m-%d %H:%M:%S')
    
    log_info "File timestamp: $readable_time"
    
    # Extract error context
    local snippet=$(extract_error_snippet "$latest_rpt" 50)
    
    # Create and append JSON entry
    local json_entry=$(create_json_entry "$readable_time" "$snippet")
    append_to_log "$json_entry"
    
    log_info "Capture complete. Preview:"
    echo "$snippet" | head -10
}

# Watch mode - monitor for new crashes
watch_mode() {
    log_info "Starting watch mode. Press Ctrl+C to stop."
    log_info "Monitoring: $DAYZ_PROFILES"
    
    local last_check=$(date +%s)
    
    while true; do
        sleep 5
        
        local latest_rpt=$(find_latest_rpt)
        if [ -n "$latest_rpt" ]; then
            local file_time=$(stat -c %Y "$latest_rpt" 2>/dev/null || stat -f %m "$latest_rpt")
            
            if [ "$file_time" -gt "$last_check" ]; then
                log_warn "New RPT activity detected!"
                capture_error
                last_check=$file_time
            fi
        fi
    done
}

# Main entry point
main() {
    # Check for jq dependency
    if ! command -v jq &> /dev/null; then
        log_warn "jq not found - JSON formatting may be basic"
    fi
    
    if [ "$1" == "--watch" ]; then
        watch_mode
    else
        capture_error
    fi
}

main "$@"
