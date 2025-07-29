#!/usr/bin/env python3
"""
Launcher script for homelab-mcp-server that avoids relative imports.
This is designed to work well with PyInstaller.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the server
from homelab_mcp.server import main

if __name__ == "__main__":
    main()