#!/bin/bash
# Build Windows executable on macOS/Linux using Wine
# Requires Wine to be installed

set -e

echo "🍷 Building Windows executable using Wine..."

# Check if Wine is installed
if ! command -v wine &> /dev/null; then
    echo "❌ Wine is not installed. Please install it first:"
    echo "   macOS: brew install --cask wine-stable"
    echo "   Linux: sudo apt-get install wine64 wine32"
    exit 1
fi

# Download Python for Windows if not present
PYTHON_VERSION="3.12.0"
PYTHON_INSTALLER="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_INSTALLER}"

if [ ! -f "$PYTHON_INSTALLER" ]; then
    echo "📥 Downloading Python ${PYTHON_VERSION} for Windows..."
    curl -O "$PYTHON_URL"
fi

# Create Wine prefix if it doesn't exist
export WINEPREFIX="$PWD/.wine"
export WINEARCH=win64

if [ ! -d "$WINEPREFIX" ]; then
    echo "🔧 Creating Wine prefix..."
    winecfg
fi

# Install Python in Wine
echo "🐍 Installing Python in Wine..."
wine "$PYTHON_INSTALLER" /quiet InstallAllUsers=1 PrependPath=1

# Install dependencies and build
echo "📦 Building Windows executable..."
wine python -m pip install uv
wine python -m uv sync --all-extras --dev
wine python -m uv run python build_all_platforms.py --platform windows-x86_64

echo "✅ Windows build complete!"
echo "📁 Executable is in dist/windows-x86_64/"