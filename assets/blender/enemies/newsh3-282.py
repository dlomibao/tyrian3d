"""Rock spur (24x28) (newsh3.shp frame 282): part of the arch's one rock (lib_arch_rock,
D209), built through newsh3-262.py; this wrapper runs that builder and exports only newsh3-282.

Run: blender --background --python assets/blender/enemies/newsh3-282.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh3_262_builder", Path(__file__).resolve().with_name("newsh3-262.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

if __name__ == "__main__":
    builder.main(only={"newsh3-282"})
