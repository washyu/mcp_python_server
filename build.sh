#!/bin/bash
# Build script for creating standalone homelab-mcp-server executable

set -e

echo "🔨 Building homelab-mcp-server executable with Nuitka..."

# Ensure we have uv and dependencies installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Ensure dependencies are installed
echo "📦 Installing dependencies..."
uv sync

# Run the build script
echo "🏗️ Starting Nuitka compilation..."
uv run python build_executable.py

echo "✅ Build complete!"