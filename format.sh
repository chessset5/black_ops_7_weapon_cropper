#!/usr/bin/env bash

set -e

# Use provided directory/file argument, or default to current directory
TARGET="${1:-.}"


echo "🔍 Running Ruff linter (with fixes) on: $TARGET..."
uvx ruff check --fix .

echo "✨ Running Ruff formatter on: $TARGET..."
uvx ruff format .

echo "✅ Formatting complete!"