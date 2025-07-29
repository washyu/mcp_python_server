# Building Homelab MCP Server Executables

This document describes how to build standalone executables for the Homelab MCP Server.

## Quick Start

Build for your current platform:
```bash
uv run python build_pyinstaller.py
```

The executable will be created in `dist/homelab-mcp-server` (or `.exe` on Windows).

## Build Scripts

### Main Build Scripts

- **`build_pyinstaller.py`** - Fast builds using PyInstaller (recommended)
- **`build_all_platforms.py`** - Cross-platform build orchestrator
- **`build_executable.py`** - Nuitka builds (slower but more optimized)
- **`build.sh`** - Simple wrapper for PyInstaller builds

### Cross-Platform Build Scripts

- **`build-docker.sh`** - Build Linux executables using Docker
- **`build-wine.sh`** - Build Windows executables on Linux/macOS (experimental)

## Platform-Specific Builds

### Build for Current Platform
```bash
uv run python build_all_platforms.py
```

### Build for Specific Platform
```bash
# Linux
uv run python build_all_platforms.py --platform linux-x86_64

# Windows
uv run python build_all_platforms.py --platform windows-x86_64

# macOS Intel
uv run python build_all_platforms.py --platform macos-x86_64

# macOS Apple Silicon
uv run python build_all_platforms.py --platform macos-arm64
```

### Cross-Platform Builds

#### Linux on macOS/Windows (using Docker)
```bash
./build-docker.sh
```

#### Windows on Linux/macOS (experimental, requires Wine)
```bash
./build-wine.sh
```

## Automated Builds (CI/CD)

GitHub Actions automatically builds executables for all platforms when:
- A version tag is pushed (e.g., `v1.0.0`)
- A PR is opened to the main branch
- Manually triggered via GitHub Actions UI

Workflow: `.github/workflows/build-executables.yml`

### Creating a Release

1. Tag your release:
   ```bash
   git tag v0.2.0
   git push --tags
   ```

2. GitHub Actions will automatically:
   - Build executables for all platforms
   - Create a GitHub release
   - Upload all executables with checksums

## Build Output

Executables are created in platform-specific directories:
- `dist/linux-x86_64/homelab-mcp-server`
- `dist/windows-x86_64/homelab-mcp-server.exe`
- `dist/macos-x86_64/homelab-mcp-server`
- `dist/macos-arm64/homelab-mcp-server`

## Dependencies

- Python 3.12+
- uv (for dependency management)
- PyInstaller (added to dev dependencies)
- Optional: Docker (for Linux cross-compilation)
- Optional: Wine (for Windows cross-compilation)

## Troubleshooting

### Import Errors
If you get import errors when running the executable, ensure all dependencies are listed in the hidden imports section of the build script.

### Large File Size
Executables are typically 20-30MB as they include Python and all dependencies. This is normal for Python executables.

### Platform Compatibility
- Linux executables work on most modern Linux distributions
- Windows executables require Windows 10 or later
- macOS executables are signed with ad-hoc signature (not notarized)

### Performance
The compiled executables start faster than the UV-based version as they don't need to resolve dependencies at runtime.