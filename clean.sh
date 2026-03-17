#!/usr/bin/env bash
set -euo pipefail

echo "Cleaning Python cache files..."

# Remove all __pycache__ directories
find . -type d -name "__pycache__" -prune -exec rm -rf {} +

# Remove compiled Python artifacts
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

echo "Done."
