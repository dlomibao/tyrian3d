"""Blue gem pod (newshv.shp frames 153, 155, 157): built together with its red twin.

newshv-153 is the same gem as newshv-123 in blue; both are built by newshv-123.py (the GEM WAR
gunship's launched gems). Running this script runs that one, which writes both models.

Run: blender --background --python assets/blender/enemies/newshv-153.py
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "newshv-123.py"), run_name="__main__")
