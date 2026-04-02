#!/usr/bin/env bash
# Git Auto Helper for Unix/Linux/macOS

set -euo pipefail

ROOT_DIR="${1:-.}"
OPERATION="${2:-status}"
MESSAGE="${3:-Auto commit}"

find_repos() {
    for dir in "$ROOT_DIR"/*/; do
        if [ -d "$dir/.git" ]; then
            echo "$dir"
        fi
    done
}

for repo in $(find_repos); do
    echo "[$(basename "$repo")] Operation: $OPERATION"
    pushd "$repo" > /dev/null || continue
    case "$OPERATION" in
        status)
            git status --short
            ;;
        pull)
            git pull
            ;;
        commit-push)
            git add .
            git commit -m "$MESSAGE" || true
            git push || true
            ;;
        *)
            echo "Unknown operation: $OPERATION"
            ;;
    esac
    popd > /dev/null || true
done
