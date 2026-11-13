"""Rock spur (24x28) (newsh3.shp frame 282): built by newsh3-262.py (one rock, one height field with the
shoulder and the spur); this wrapper runs that builder and exports only newsh3-282.

Run: blender --background --python assets/blender/enemies/newsh3-282.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh3_262_builder", Path(__file__).resolve().with_name("newsh3-262.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

if __name__ == "__main__":
    builder.main(only={"newsh3-282"})
