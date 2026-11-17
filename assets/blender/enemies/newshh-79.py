"""Grey dome (newshh.shp frame 79): the silver cap on the organism's stalk, a 3D version of its sprites.
The damaged frame 41 is drawn with this intact model (D87). Built by lib_b063.

The shape is lib_b063's build_cap; this wrapper repaints it (QA 2026-11-17: in game the cap read dull slate where the
sprite draws BRIGHT SILVER with a white crown highlight). The sprite's own ramp by plan row, on the cap's row rings
(so every boundary is a clean ring): the crown (rows 17-22, 108-111, median 109) 109, the band under it (rows 23-24,
106-107) 107, the south lip (rows 25-27, 104-106) 106, the lip's camera-facing face 104. Nearly no metal (lib's
0.55-0.6 renders this mid-grey steel charcoal, D201), a tight roughness and full F0 (D176), so the
white of 110-111 comes as sheen on the crown. lib_b063 is shared with the block, orbs and thorn, so the change
lives here.

Run: blender --background --python assets/blender/enemies/newshh-79.py
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

# index: metallic, roughness, Specular IOR Level
RAMP = {104: (0.08, 0.3, 1.0), 106: (0.08, 0.26, 1.0), 107: (0.08, 0.24, 1.0), 109: (0.08, 0.2, 1.0)}
_build_cap = lib.build_cap


def build_cap(coll):
    ob, sp = _build_cap(coll)
    me = ob.data
    me.materials.clear()
    slot = {}
    for i, (m, rgh, spec) in RAMP.items():
        slot[i] = len(me.materials)
        mat = lib.common.palette_material(sp, i, "nshh79B", metallic=m, roughness=rgh)
        lib.set_spec(mat, spec)
        me.materials.append(mat)
    for p in me.polygons:
        r = 14 - p.center.y / lib.PX  # tile row
        if p.normal.y < -0.85:
            p.material_index = slot[104]
        elif r < 23.0:
            p.material_index = slot[109]
        elif r < 25.0:
            p.material_index = slot[107]
        else:
            p.material_index = slot[106]
    return ob, sp


lib.build_cap = build_cap

if __name__ == "__main__":
    lib.export_cap()
