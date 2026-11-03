"""SAVARA's stone towers in the sea (Episode 1, map 1-8 SAVARA, shapesy.dat, layer 0): the worked example
of the tall-building rule (DECISIONS.md D68, docs/agents/TALL-BUILDINGS.md, lib_tall.py).

The tiles draw each tower in the art's oblique view: a grey roof of carved slabs with chamfered corners
(rows 320/330), and below it the south wall, dark stone with pairs of buttress pipes (340, 350 repeated,
360 at the foot). The wide tower (4 tiles, map rows 208-212, cols 2-5) has a 54 px wall under a 57 px
roof; the tall one (3 tiles, rows 200-206, cols 7-9) a 110 px wall under a 56 px roof. Each is built
as the real tower: on the roof's outline moved down to the wall's foot, its walls vertical and as tall
as the painted wall, the roof and the wall wearing their pixels as a low relief, and drawn by the
renderer in the art's oblique view with its depth squeezed under background 2 (lib_tall.export).

The tower tiles are a kit (320-362 also make SAVARA's walls and keeps), so the patterns need minRows
(MIN_ROWS).
Run from the repo root (needs `TILES_SHAPES=y npm run tiles` for reference/tiles/shapesy):

    blender --background --factory-startup --python assets/blender/tiles/savbld_towers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_tall  # noqa: E402

TOWERS = {
    "savbld-tower-wide": [[320, 321, 321, 322], [330, 331, 331, 332], [340, 341, 341, 342], [350, 351, 351, 352], [360, 361, 361, 362]],
    "savbld-tower-tall": [[320, 321, 322], [330, 331, 332], [340, 341, 342], [350, 351, 352], [350, 351, 352], [350, 351, 352],
                          [360, 361, 362]],
}
# Rows that must be drawn and match: all of them. Both towers share rows with shorter or taller towers of
# the same width in Episodes 1 and 4 (tests/render/remaster.test.ts). Their
# tiles show until then; the model lands exactly on them (oblique-locked), so the switch hardly shows.
MIN_ROWS = {"savbld-tower-wide": 5, "savbld-tower-tall": 7}

for name, pattern in TOWERS.items():
    t = lib_tall.TallBuilding("shapesy", pattern, layer=0, tag=name.replace("-", ""))
    print(name, "wall band", t.shift, "px, roof", t.s["roof_px"], "px, tall:", t.s["tall"])
    block = t.block(name=name)
    t.export([block], name, min_rows=MIN_ROWS[name])
