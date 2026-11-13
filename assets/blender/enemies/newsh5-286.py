"""Cannon bolt pointing right (newsh5.shp size 1, frame 286): the mirror of newsh5-267. Loads
newsh5-267.py's builder and exports only newsh5-286 (see that script for the design)."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh5_267", Path(__file__).resolve().with_name("newsh5-267.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

if __name__ == "__main__":
    b.export(286)
