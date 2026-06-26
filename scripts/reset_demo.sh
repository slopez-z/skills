#!/usr/bin/env bash
# Reset the repo to its pre-run state. Deletes everything the skills generate,
# keeps everything hand-authored (SOWs, inbox requests, config, gold labels).
# Use between demo rehearsals: ./scripts/reset_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Removing generated artifacts..."
find projects -name "baseline.json" -delete -print
find projects -name "delivery-brief.md" -delete -print
find projects -name "scope-changelog.jsonl" -delete -print
find projects -name "cr-*.md" -delete -print
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "Clean. Hand-authored files per project:"
find projects -type f | sort
