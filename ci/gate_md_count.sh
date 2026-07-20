#!/bin/bash
set -euo pipefail

# Find all .md files in the root directory (excluding dotfiles and directories)
MD_FILES=$(find . -maxdepth 1 -name "*.md" -type f)
MD_COUNT=$(echo "$MD_FILES" | wc -l)

MAX_MD_FILES=3

echo "Root .md files found: $MD_COUNT"

if [ "$MD_COUNT" -gt "$MAX_MD_FILES" ]; then
    echo "CRITICAL ERROR: Too many root .md files ($MD_COUNT > $MAX_MD_FILES)."
    echo "Root directory is cluttered. Move historical reports to reports/."
    echo "Files found:"
    echo "$MD_FILES"
    exit 1
fi

echo "Root .md file count is acceptable ($MD_COUNT <= $MAX_MD_FILES)."
exit 0
