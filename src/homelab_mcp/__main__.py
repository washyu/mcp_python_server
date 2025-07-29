#!/usr/bin/env python3
"""
Entry point for the homelab-mcp-server package.
This allows the package to be run with `python -m homelab_mcp`.
"""

from .server import main

if __name__ == "__main__":
    main()