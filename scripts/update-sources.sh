#!/usr/bin/env bash
# update-sources.sh -- Fetch fresh internet sources, analyze for changes,
# and propose updates to Humanize reference files.
#
# This script is ADVISORY. It fetches, compares, and reports. It does NOT
# overwrite reference files automatically. A human reviews the report and
# decides what to incorporate.
#
# Usage:
#   ./scripts/update-sources.sh              # full update (fetch + analyze)
#   ./scripts/update-sources.sh --fetch-only # just download, skip analysis
#   ./scripts/update-sources.sh --analyze    # analyze cached fetches only
#
# Output goes to .test-output/update-report/
#
# Requirements: curl, python3 (stdlib only -- no pip packages needed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/.test-output/update-report"
FETCH_DIR="$REPORT_DIR/fetched"
ANALYSIS_DIR="$REPORT_DIR/analysis"

MODE="${1:-full}"

# --- Colors (disabled if not a terminal) ---
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

log()  { echo -e "${BLUE}[update]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[ok]${NC} $*"; }

# --- Source Registry ---
# Each source has: slug, URL, description
# Add new sources here. The fetch step downloads them all.
# The analyze step compares against previous fetches and current reference files.

declare -A SOURCES
declare -A SOURCE_DESCS

# Primary: Wikipedia Signs of AI Writing
SOURCES[wikipedia-aisigns]="https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing"
SOURCE_DESCS[wikipedia-aisigns]="Wikipedia field guide to AI writing tells"

# Detection research
SOURCES[gptzero-how]="https://gptzero.me/news/how-ai-detectors-work/"
SOURCE_DESCS[gptzero-how]="GPTZero detection methodology"

SOURCES[gptzero-perplexity]="https://gptzero.me/news/perplexity-and-burstiness-what-is-it/"
SOURCE_DESCS[gptzero-perplexity]="GPTZero perplexity/burstiness explainer"

SOURCES[pangram-limits]="https://www.pangram.com/blog/why-perplexity-and-burstiness-fail-to-detect-ai"
SOURCE_DESCS[pangram-limits]="Pangram Labs on statistical detection limits"

SOURCES[copyleaks-edu]="https://copyleaks.com/blog/what-educators-should-know-about-ai-detection-in-2026"
SOURCE_DESCS[copyleaks-edu]="Copyleaks educator guide"

# Code detection
SOURCES[blueoptima-code]="https://www.blueoptima.com/post/how-to-detect-ai-generated-code-in-your-software-projects"
SOURCE_DESCS[blueoptima-code]="BlueOptima code detection patterns"

SOURCES[hackerrank-code]="https://www.hackerrank.com/writing/how-hackerrank-catches-ai-generated-code-advanced-ml-plagiarism-detection"
SOURCE_DESCS[hackerrank-code]="HackerRank multi-signal code detection"

# Writing improvement
SOURCES[beutler-wikipedia]="https://www.beutlerink.com/blog/how-to-spot-ai-writing"
SOURCE_DESCS[beutler-wikipedia]="Beutler Ink analysis of WP:AISIGNS"

SOURCES[augmented-educator]="https://www.theaugmentededucator.com/p/the-ten-telltale-signs-of-ai-generated"
SOURCE_DESCS[augmented-educator]="Ten telltale signs of AI text"

SOURCES[undetectable-words]="https://undetectable.ai/blog/common-ai-words/"
SOURCE_DESCS[undetectable-words]="Common AI vocabulary list"

SOURCES[bouchard-editing]="https://www.louisbouchard.ai/ai-editing/"
SOURCE_DESCS[bouchard-editing]="How to clean up AI drafts"

# --- Personal Sources (voice calibration) ---
# Check XDG config dir first, then repo-local. These are gitignored so
# each user can point to their own writing samples.
# See personal-sources.yml.example for format.
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
if [ -f "$XDG_CONFIG_HOME/humanize/personal-sources.yml" ]; then
    PERSONAL_SOURCES_FILE="$XDG_CONFIG_HOME/humanize/personal-sources.yml"
else
    PERSONAL_SOURCES_FILE="$PROJECT_ROOT/personal-sources.yml"
fi

load_personal_sources() {
    if [ ! -f "$PERSONAL_SOURCES_FILE" ]; then
        warn "No personal-sources.yml found. Voice calibration sources skipped."
        warn "Copy personal-sources.yml.example to personal-sources.yml and add your URLs."
        return
    fi

    log "Loading personal sources from personal-sources.yml..."

    # Parse YAML with Python, output JSON lines (no eval -- prevents shell injection)
    # Supports both url: and path: entries
    while IFS= read -r json_line; do
        slug=$(python3 -c "import json,sys; d=json.loads(sys.stdin.readline()); print(d['slug'])" <<< "$json_line")
        location=$(python3 -c "import json,sys; d=json.loads(sys.stdin.readline()); print(d['location'])" <<< "$json_line")
        desc=$(python3 -c "import json,sys; d=json.loads(sys.stdin.readline()); print(d['description'])" <<< "$json_line")
        src_type=$(python3 -c "import json,sys; d=json.loads(sys.stdin.readline()); print(d['type'])" <<< "$json_line")
        if [ -n "$slug" ] && [ -n "$location" ]; then
            if [ "$src_type" = "local" ]; then
                LOCAL_SOURCES[$slug]="$location"
            else
                SOURCES[$slug]="$location"
            fi
            SOURCE_DESCS[$slug]="$desc"
        fi
    done < <(python3 -c "
import json, re, sys, os
text = open('$PERSONAL_SOURCES_FILE').read()
# Match url: entries
for m in re.finditer(
    r'- slug:\s*(\S+)\s*\n\s*url:\s*(\S+)\s*\n\s*description:\s*(.+)',
    text
):
    slug, url, desc = m.group(1), m.group(2), m.group(3).strip()
    if re.match(r'^[a-zA-Z0-9_.\-]+\$', slug) and re.match(r'^https?://[^\s]+\$', url):
        print(json.dumps({'slug': slug, 'location': url, 'description': desc, 'type': 'url'}))
# Match path: entries
for m in re.finditer(
    r'- slug:\s*(\S+)\s*\n\s*path:\s*(.+)\s*\n\s*description:\s*(.+)',
    text
):
    slug, path, desc = m.group(1), m.group(2).strip(), m.group(3).strip()
    path = os.path.expanduser(path)
    if re.match(r'^[a-zA-Z0-9_.\-]+\$', slug) and os.path.exists(path):
        print(json.dumps({'slug': slug, 'location': path, 'description': desc, 'type': 'local'}))
    elif re.match(r'^[a-zA-Z0-9_.\-]+\$', slug):
        print(json.dumps({'slug': slug, 'location': path, 'description': desc + ' [NOT FOUND]', 'type': 'local'}))
" 2>/dev/null)
}

# Local sources need a separate associative array
declare -A LOCAL_SOURCES

load_personal_sources

# --- Collect local sources ---
collect_local_sources() {
    local collected=0 failed=0

    # bash 5.2: ${#arr[@]} raises "unbound variable" under nounset for a
    # declared-but-empty associative array. Guard before iterating.
    [ "${LOCAL_SOURCES[*]+set}" = set ] || return 0

    for slug in "${!LOCAL_SOURCES[@]}"; do
        local src_path="${LOCAL_SOURCES[$slug]}"
        local outfile="$FETCH_DIR/${slug}.html"
        local metafile="$FETCH_DIR/${slug}.meta"

        log "  Reading local: $slug ($src_path)"

        if [ ! -e "$src_path" ]; then
            warn "  $slug: path not found: $src_path"
            touch "$outfile"
            cat > "$metafile" <<METAEOF
slug=$slug
url=file://$src_path
description=${SOURCE_DESCS[$slug]}
http_code=404
fetch_date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
file_size=0
METAEOF
            failed=$((failed + 1))
            continue
        fi

        # Extract text using extract-text.py (handles PDF, DOCX, ODT, etc.)
        local extract_output
        extract_output=$(python3 "$SCRIPT_DIR/extract-text.py" "$src_path" -o "$outfile" 2>&1)
        local extract_rc=$?

        if [ $extract_rc -eq 0 ] && [ -s "$outfile" ]; then
            ok "  $slug: $extract_output"
            collected=$((collected + 1))
        else
            warn "  $slug: extraction failed or empty ($extract_output)"
            failed=$((failed + 1))
        fi

        cat > "$metafile" <<METAEOF
slug=$slug
url=file://$src_path
description=${SOURCE_DESCS[$slug]}
http_code=200
fetch_date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
file_size=$(stat -c%s "$outfile" 2>/dev/null || echo 0)
METAEOF
    done

    if [ "${#LOCAL_SOURCES[@]}" -gt 0 ]; then
        log "Local sources: $collected collected, $failed failed"
    fi
}

# --- Fetch remote sources ---
fetch_sources() {
    local local_count=0
    [ "${LOCAL_SOURCES[*]+set}" = set ] && local_count=${#LOCAL_SOURCES[@]}
    local total=$(( ${#SOURCES[@]} + local_count ))
    log "Collecting $total sources (${#SOURCES[@]} remote, ${local_count} local)..."
    mkdir -p "$FETCH_DIR"

    # Collect local sources first (fast, no network)
    collect_local_sources

    # Fetch remote sources
    local fetched=0 failed=0

    for slug in "${!SOURCES[@]}"; do
        local url="${SOURCES[$slug]}"
        local outfile="$FETCH_DIR/${slug}.html"
        local metafile="$FETCH_DIR/${slug}.meta"

        log "  Fetching: $slug"
        local http_code
        http_code=$(curl -sL -o "$outfile" -w '%{http_code}' \
            -H 'User-Agent: Mozilla/5.0 (compatible; Humanize-updater/1.0)' \
            --max-time 30 \
            "$url" 2>/dev/null) || http_code="000"

        # Retry once on transient HTTP errors (429 Too Many Requests, 503 Service Unavailable)
        if [ "$http_code" = "429" ] || [ "$http_code" = "503" ]; then
            warn "  $slug: HTTP $http_code -- retrying in 5s..."
            sleep 5
            http_code=$(curl -sL -o "$outfile" -w '%{http_code}' \
                -H 'User-Agent: Mozilla/5.0 (compatible; Humanize-updater/1.0)' \
                --max-time 30 \
                "$url" 2>/dev/null) || http_code="000"
        fi

        cat > "$metafile" <<METAEOF
slug=$slug
url=$url
description=${SOURCE_DESCS[$slug]}
http_code=$http_code
fetch_date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
file_size=$(stat -c%s "$outfile" 2>/dev/null || echo 0)
METAEOF

        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
            ok "  $slug: HTTP $http_code ($(stat -c%s "$outfile" 2>/dev/null || echo '?') bytes)"
            fetched=$((fetched + 1))
        else
            warn "  $slug: HTTP $http_code -- may need manual review"
            failed=$((failed + 1))
        fi
    done

    log "Remote sources: $fetched succeeded, $failed failed"
}

# --- Analyze ---
analyze_sources() {
    log "Analyzing fetched sources against current reference files..."
    mkdir -p "$ANALYSIS_DIR"

    # Run the Python analyzer
    python3 "$SCRIPT_DIR/analyze-sources.py" \
        --fetch-dir "$FETCH_DIR" \
        --reference-dir "$PROJECT_ROOT/reference" \
        --output-dir "$ANALYSIS_DIR"

    local report="$ANALYSIS_DIR/update-report.md"
    if [ -f "$report" ]; then
        echo ""
        log "========================================="
        log "Update report written to: $report"
        log "========================================="
        echo ""
        cat "$report"
    else
        err "Analysis did not produce a report. Check $ANALYSIS_DIR for errors."
        return 1
    fi
}

# --- Main ---
case "$MODE" in
    --fetch-only)
        fetch_sources
        ;;
    --analyze)
        if [ ! -d "$FETCH_DIR" ]; then
            err "No fetched data found. Run without --analyze first."
            exit 1
        fi
        analyze_sources
        ;;
    full|"")
        fetch_sources
        analyze_sources
        ;;
    *)
        err "Unknown mode: $MODE"
        echo "Usage: $0 [--fetch-only|--analyze]"
        exit 1
        ;;
esac
