#!/usr/bin/env bash
# Scan the tracked tree for terms that must never be published.
#   deny-scan.sh [terms-file]     terms also read from $DENY_TERMS (newline separated)
# The terms file stays out of git: publishing it would leak exactly what it protects.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
terms_file=${1:-$root/deny-terms.txt}
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
{ [ -f "$terms_file" ] && cat "$terms_file"; printf '%s\n' "${DENY_TERMS:-}"; } | grep -v '^\s*$' | grep -v '^#' > "$tmp" || true

status=0
cd "$root"
if [ -s "$tmp" ] && git grep -n -i -F -f "$tmp" -- . ':!deny-terms.txt'; then
  echo "deny-scan: listed terms found above" >&2; status=1
fi
# Generic shapes no public file needs: ticket keys and 12-digit account ids.
# No \b: git grep -E ignores it on macOS, which left this scan blind there. The edges are spelled out instead.
edge='(^|[^A-Za-z0-9_])' end='($|[^A-Za-z0-9_])'
if git grep -n -E "${edge}[A-Z]{2,6}-[0-9]{2,6}${end}|${edge}[0-9]{12}${end}" -- . ':!LICENSE' ':!scripts/deny-scan.sh'; then
  echo "deny-scan: ticket-key or account-id shapes found above; rename or allow explicitly" >&2; status=1
fi
[ $status -eq 0 ] && echo "deny-scan: clean"
exit $status
