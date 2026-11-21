"""Pytest root configuration and path registration for InvenIQ."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# Register monorepo source roots into sys.path
sys_paths = [
    ROOT_DIR / "services" / "core" / "src",
    ROOT_DIR / "services" / "api" / "src",
    ROOT_DIR / "services" / "ml" / "src",
    ROOT_DIR / "services" / "optimizer" / "src",
    ROOT_DIR / "pipelines" / "src",
]

for p in sys_paths:
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
