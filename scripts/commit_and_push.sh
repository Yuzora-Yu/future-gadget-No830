#!/usr/bin/env bash
set -euo pipefail

kind="${1:-DATA}"
cd "$(dirname "$0")/.."

git config user.name "fg830-local-runner"
git config user.email "fg830-local-runner@users.noreply.github.com"
git add data docs/status.json docs/protocol.json docs/history.json docs/integrity.json

if git diff --cached --quiet; then
  echo "No FG830 data changes to commit."
  exit 0
fi

git commit -m "$kind $(TZ=Asia/Tokyo date +%F): local timer record"
git pull --rebase origin main
git push origin HEAD:main
