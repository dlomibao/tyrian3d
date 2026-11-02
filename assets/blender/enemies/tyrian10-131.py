"""Armour crate +8 (tyrian.shp #10 frame 131, enemy type 563): a 3D version of its sprite.

The armour ship's (tyrian10-279) best drop: picking it up adds 8 armour. The strapped crate's
(tyrian10-129) silhouette and shading in blue steel with no straps, built as tyrian10-127.py builds
the grey one.

Run: blender --background --python assets/blender/enemies/tyrian10-131.py [-- --preview out.png]
"""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("crate_127", Path(__file__).with_name("tyrian10-127.py"))
crate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crate)

NAME = "tyrian10-131"
RAMP = ((49, 50, 51, 52, 53), (54, 55, 56, 57), (58, 59, 60), (61, 62))

if __name__ == "__main__":
    crate.main(NAME, ramp=RAMP, finish=dict(metallic=0.55, roughness=0.3))
