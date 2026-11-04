#!/usr/bin/env bash
# Same as the pre-commit hook, for running by hand: options first, then certificate files.
exec coi-lint-precommit "$@"
