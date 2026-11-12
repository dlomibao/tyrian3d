"""newshc-77: the flamethrower head on top of each DELIANI tower (assembly-newshc-283).

newshc.shp frames 77-89 (one shape per frame) plus the damaged frame 91, one model per frame. The
head is the top of a STANDING tower (D82's approach C for sprite models, D165; assembly-newshc-283.py's
docstring): a steel ball on a machined ram that slides up out of the tower's vent cup (frames
77/79/81 show it rising), a flame nozzle raked 38 deg up its front with a lit core (glow 112-118 on
frames 79-87), a red fuel line over its crown, and a red clamshell hood round the lower ball whose
halves part on rear guide posts (frames 85-89) to show the flame chamber. Frame 91 is the wreck:
the ram's torn collar in the cup's bore and a bent feed rod.

The geometry is lib_deliani_tower.head / wreck, built in the true tower's frame (the ball's centre
about 83 px up); the build, bake (the tower body as the occluder; no projection), outline shells,
the upright export with the `tyrian_oblique` and `tyrian_depth_band` extras, and the measure are
assembly-newshc-283.py's (heads_main). Each glb is tagged frame_part([frame]).

  blender --background --python assets/blender/enemies/newshc-77.py -- [--no-bake] [--measure DIR]
      [--views DIR]
(exports public/models/enemies/newshc-77.glb, newshc-77-f2 .. -f8 and their spriteModels entries)
"""

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "assembly_newshc_283", Path(__file__).resolve().parent / "assembly-newshc-283.py")
asm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(asm)


if __name__ == "__main__":
    asm.heads_main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
