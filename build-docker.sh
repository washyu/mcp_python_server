#!/bin/bash
# Build script to create Linux executables using Docker
# This allows building Linux executables on macOS/Windows

set -e

echo "🐳 Building Linux executables using Docker..."

# Build for Linux x86_64
echo "📦 Building for linux-x86_64..."
docker run --rm -v "$PWD":/app -w /app python:3.12-slim bash -c "
    apt-get update && apt-get install -y build-essential
    pip install uv
    uv sync --all-extras --dev
    uv run python build_all_platforms.py --platform linux-x86_64
"

# Build for Linux ARM64 (if on ARM64 host or with emulation)
if [[ "$(uname -m)" == "arm64" ]] || [[ "$(uname -m)" == "aarch64" ]]; then
    echo "📦 Building for linux-arm64..."
    docker run --rm -v "$PWD":/app -w /app python:3.12-slim bash -c "
        apt-get update && apt-get install -y build-essential
        pip install uv
        uv sync --all-extras --dev
        uv run python build_all_platforms.py --platform linux-aarch64
    "
fi

echo "✅ Linux builds complete!"
echo "📁 Executables are in dist/linux-*/"