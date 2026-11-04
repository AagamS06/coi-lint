#!/usr/bin/env bash
# pre-commit passes options first, then the changed certificate files. Check each file.
set -u
opts=(); files=()
while [ $# -gt 0 ]; do
  case "$1" in
    --*) opts+=("$1" "$2"); shift 2 ;;
    *) files+=("$1"); shift ;;
  esac
done
rc=0
for f in "${files[@]}"; do
  coi-lint check "$f" "${opts[@]}" --no-color || rc=1
done
exit $rc
