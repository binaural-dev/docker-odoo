#!/bin/sh
# Format XML files in the given directory using xmllint.
# Usage: xml-format.sh <directory>

set -e

TARGET_DIR="${1:-.}"

# Install xmllint if not available
if ! command -v xmllint >/dev/null 2>&1; then
    echo "xmllint not found. Installing libxml2-utils..." >&2
    apt-get update && apt-get install -y libxml2-utils
fi

cd "$TARGET_DIR"
find . -type f -name "*.xml" -exec xmllint --format {} --output {} \;

