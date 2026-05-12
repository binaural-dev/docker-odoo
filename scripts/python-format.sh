#!/bin/sh
# Format Python files in the given directory using black.
# Usage: python-format.sh <directory>

set -e

TARGET_DIR="${1:-.}"

# Install black if not available
if ! command -v black >/dev/null 2>&1; then
    echo "black not found. Installing via pip3..." >&2
    pip3 install black
fi

cd "$TARGET_DIR"
black ./

