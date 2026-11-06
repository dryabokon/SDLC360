"""SDLC360 entry point: `python sdlc.py scan|render|list|serve` (see README.md)."""

import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
