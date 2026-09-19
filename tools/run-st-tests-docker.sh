#!/usr/bin/env bash
# Runs tests_st/ headlessly against real Sublime Text via Docker, using
# SublimeText/UnitTesting's own docker/ tooling (cloned on demand into a
# gitignored cache dir so this repo doesn't vendor it).
#
# Usage:
#   ./tools/run-st-tests-docker.sh                          # run all of tests_st/
#   ./tools/run-st-tests-docker.sh --file tests_st/test_window_lifecycle.py
#   ./tools/run-st-tests-docker.sh --refresh-image           # rebuild the docker image
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$REPO_ROOT/.cache/UnitTesting"

if [ ! -d "$CACHE_DIR/.git" ]; then
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone --depth 1 https://github.com/SublimeText/UnitTesting.git "$CACHE_DIR"
else
  git -C "$CACHE_DIR" pull --ff-only
fi

PYTHON="$(command -v python3 || command -v python)"
if [ -z "$PYTHON" ]; then
  echo "error: no python3/python interpreter found on PATH" >&2
  exit 1
fi

exec "$PYTHON" "$CACHE_DIR/docker/run_tests.py" "$REPO_ROOT" --package-name SettingsUI "$@"
