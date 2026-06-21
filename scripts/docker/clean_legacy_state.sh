#!/usr/bin/env bash
set -euo pipefail

LEGACY_PREFIX="platform33_"
FORCE=false

if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
fi

echo "=== Docker Compose Stability Check ==="
echo "Scanning for legacy containers/volumes with prefix: ${LEGACY_PREFIX}"
echo ""

legacy_containers=$(docker ps -a --filter "name=${LEGACY_PREFIX}" --format "{{.Names}}" 2>/dev/null || true)
legacy_volumes=$(docker volume ls --filter "name=${LEGACY_PREFIX}" --format "{{.Name}}" 2>/dev/null || true)

found_issues=false

if [[ -n "$legacy_containers" ]]; then
  found_issues=true
  echo "⚠️  LEGACY CONTAINERS DETECTED:"
  echo "$legacy_containers" | sed 's/^/  - /'
  echo ""
fi

if [[ -n "$legacy_volumes" ]]; then
  found_issues=true
  echo "⚠️  LEGACY VOLUMES DETECTED:"
  echo "$legacy_volumes" | sed 's/^/  - /'
  echo ""
fi

if [[ "$found_issues" == false ]]; then
  echo "✅ No legacy state found. Docker Compose environment is clean."
  exit 0
fi

echo "❌ ISSUE: Legacy containers/volumes from manual 'docker run' detected."
echo ""
echo "WHY THIS BREAKS COMPOSE:"
echo "  - Wrong volume prefix (${LEGACY_PREFIX}* instead of mahoun_*)"
echo "  - Outdated credentials (e.g., mahoun123 instead of .env values)"
echo "  - Port conflicts and stale configuration"
echo ""

if [[ "$FORCE" == true ]]; then
  echo "🔧 --force mode: Removing legacy state..."
  echo ""
  
  if [[ -n "$legacy_containers" ]]; then
    echo "Stopping and removing legacy containers..."
    echo "$legacy_containers" | xargs -r docker stop
    echo "$legacy_containers" | xargs -r docker rm
    echo "✅ Containers removed."
  fi
  
  if [[ -n "$legacy_volumes" ]]; then
    echo "Removing legacy volumes..."
    echo "$legacy_volumes" | xargs -r docker volume rm
    echo "✅ Volumes removed."
  fi
  
  echo ""
  echo "✅ Legacy state cleaned. You can now run:"
  echo "   COMPOSE_PROFILES=full docker compose up -d"
  exit 0
else
  echo "RECOMMENDED ACTION:"
  echo "  1. Run this script with --force to remove legacy state:"
  echo "     ./scripts/docker/clean_legacy_state.sh --force"
  echo ""
  echo "  2. Recreate services with Docker Compose:"
  echo "     COMPOSE_PROFILES=full docker compose up -d"
  exit 1
fi
