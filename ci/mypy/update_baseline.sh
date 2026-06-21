#!/bin/bash
#
# update_baseline.sh
# ==================
# Updates the mypy baseline after intentional improvements
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Updating mypy baseline..."
echo ""

python3 "$SCRIPT_DIR/check_mypy_non_regression.py" --update-baseline

echo ""
echo "✅ Done!"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git diff ci/mypy/baseline.txt"
echo "  2. Commit if correct: git add ci/mypy/baseline.txt && git commit -m 'chore: update mypy baseline'"

