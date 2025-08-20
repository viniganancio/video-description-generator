#!/bin/bash

# Script to create Lambda layer with dependencies
# This script is called by the deployment script

set -e

LAYER_NAME=${1:-"dependencies"}
REQUIREMENTS_FILE=${2:-"../../requirements.txt"}

echo "Creating Lambda layer: $LAYER_NAME"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
LAYER_DIR="$TEMP_DIR/python"

echo "Installing dependencies to: $LAYER_DIR"

# Install dependencies
mkdir -p "$LAYER_DIR"
pip install -r "$REQUIREMENTS_FILE" --target "$LAYER_DIR" --no-deps --platform linux_x86_64 --only-binary=:all:

# Remove unnecessary files to reduce layer size
echo "Cleaning up unnecessary files..."
find "$LAYER_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$LAYER_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$LAYER_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "Creating layer zip file..."
cd "$TEMP_DIR"
zip -r "$LAYER_NAME.zip" python/
mv "$LAYER_NAME.zip" "$(dirname "$0")/"

# Clean up
rm -rf "$TEMP_DIR"

echo "Lambda layer created: $(dirname "$0")/$LAYER_NAME.zip"