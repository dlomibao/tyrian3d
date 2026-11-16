"""Rock shoulder (newsh3.shp frame 262, 24x28, top layer) of SURFACE's sandy rock arch (4.4 SURFACE,
4.10 DESERTRUN): the crown's right end turning down into the right leg, at arch (96, 14).

Since D209 the arch, its edge rocks (newsh3-262 / -180 / -282, D196) and its leg tiles are ONE 3D rock
(lib_arch_rock, run by assembly-newsh3-198.py's builder); this wrapper exports only newsh3-262.
newsh3-180.py and newsh3-282.py run this file and export only their own model.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh3-262.py
"""

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("assembly_newsh3_198", Path(__file__).resolve().with_name("assembly-newsh3-198.py"))
builder = importlib.util.module_from_spec(_spec)
sys.modules["assembly_newsh3_198"] = builder
_spec.loader.exec_module(builder)


def main(only=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    builder.build_and_export(["edge"], argv, only=only)


if __name__ == "__main__":
    main(only={"newsh3-262"})
