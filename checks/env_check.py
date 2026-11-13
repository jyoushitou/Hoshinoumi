#!/usr/bin/env python3
"""Environment check entrypoint (v19.0).

The real checks live in scripts/preflight.py; this file only forwards.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.preflight import main

if __name__ == "__main__":
    raise SystemExit(main())
