"""Large grey asteroid with a glowing vent (newshd.shp frames 18, 55, 93): a 3D version of its sprite.

Seen in episodes 1-3. The same kind of lumpy grey rock as newshd-5 (see lib_b014.rock), with a
small pit on its right side (columns 18-20, rows 10-14) glowing yellow at the centre and red
round the rim. The frames only cool the glow (bright, dim, out), so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshd-18.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
from lib_b014 import common, px, row  # noqa: E402

NAME = "newshd-18"
FIRE = (115, 117, 119, 120, 122, 124, 126, 166, 168)  # the vent and its scorched lip
VENT = (px(19), row(12))  # the vent's centre
VW, VH = 1.7 / 12, 2.6 / 12  # its half width and half height


def surface_z(bm, x, y, reach=0.12):
    """The rock's top surface height near (x, y): the highest vertex within `reach`."""
    near = [v.co.z for v in bm.verts if (v.co.x - x) ** 2 + (v.co.y - y) ** 2 < reach ** 2]
    return max(near) if near else 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    bm, mats, _ = lib.rock(sprite, NAME, sprite["frames"][0]["pixels"], size=2, half_height=0.26,
                           relief=0.07, seed=18, subdiv=3, skip=FIRE)
    rock = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # The vent: a red-rimmed pit with a yellow-hot core, set into the rock's top.
    vmats = [
        common.palette_material(sprite, 117, NAME, metallic=0.1, roughness=0.6, emission_strength=2.0),
        common.palette_material(sprite, 122, NAME, emission_strength=4.0),
        common.palette_material(sprite, 126, NAME, emission_strength=6.0),
        common.palette_material(sprite, 166, NAME, metallic=0.1, roughness=0.9),
    ]
    RIM, HOT, CORE, LIP = range(4)
    import bmesh
    vb = bmesh.new()
    cx, cy = VENT
    rb = bmesh.new()
    rb.from_mesh(rock.data)
    z = surface_z(rb, cx, cy)
    rb.free()
    # Scorched lip, red rim sloping into the pit, then the glowing core.
    lip = [(cy - VH * 1.25, 0.0, 0.0, z - 0.02), (cy - VH * 1.1, VW * 1.3, 0.035, z - 0.02),
           (cy + VH * 1.1, VW * 1.3, 0.035, z - 0.02), (cy + VH * 1.25, 0.0, 0.0, z - 0.02)]
    start = len(vb.verts)
    common.loft(vb, lip, sides=10, mat_index=LIP)
    common.shift_x(vb, start, cx)
    rim = [(cy - VH, 0.0, 0.0, z), (cy - VH * 0.85, VW, 0.03, z), (cy, VW * 1.05, 0.035, z),
           (cy + VH * 0.85, VW, 0.03, z), (cy + VH, 0.0, 0.0, z)]
    start = len(vb.verts)
    common.loft(vb, rim, sides=10, mat_index=RIM)
    common.shift_x(vb, start, cx)
    hot = [(cy - VH * 0.75, 0.0, 0.0, z + 0.01), (cy - VH * 0.5, VW * 0.8, 0.03, z + 0.01),
           (cy + VH * 0.5, VW * 0.8, 0.03, z + 0.01), (cy + VH * 0.75, 0.0, 0.0, z + 0.01)]
    start = len(vb.verts)
    common.loft(vb, hot, sides=10, mat_index=HOT)
    common.shift_x(vb, start, cx)
    core = [(cy - VH * 0.45, 0.0, 0.0, z + 0.02), (cy, VW * 0.5, 0.03, z + 0.02), (cy + VH * 0.45, 0.0, 0.0, z + 0.02)]
    start = len(vb.verts)
    common.loft(vb, core, sides=8, mat_index=CORE)
    common.shift_x(vb, start, cx)
    vent = common.mesh_object(f"{NAME}_vent", vb, vmats, coll, smooth=True)
    return [(NAME, [rock, vent], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
