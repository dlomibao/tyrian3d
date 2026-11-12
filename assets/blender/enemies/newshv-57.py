"""newshv-57: the small red gem (newshv.shp frame 57, 12 x 14 px), the same object as newshv-38
(green) and newshv-19 (blue) in another colour (D120/D122): one shape, recoloured.

WHAT IT IS: a colour-coded crystal riding on a GEM WAR gunship centre piece (type 806, host 797),
6 px up the screen from its host and moved with it by link ev19. Not a ground object. The shape,
the mount and the reading of the sprite are documented in newshv-38.py; this script only picks the
red ramp (76/74/72/71/74: crown, pavilion, girdle, neck, ball foot) and exports to enemies/newshv-57.

    blender --background --python assets/blender/enemies/newshv-57.py
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("newshv_38", Path(__file__).resolve().with_name("newshv-38.py"))
gem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gem)


if __name__ == "__main__":
    gem.export("red")
