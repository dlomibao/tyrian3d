"""Retired stub: newshu-38 is now built and exported by assembly-newshu-15.py (the intact ground
station it is the west fringe of). Kept so the old entry point does not write a second, conflicting
model. lib_b136 is no longer used by anything."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().with_name("assembly-newshu-15.py")), run_name="__main__")
