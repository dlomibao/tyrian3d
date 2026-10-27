"""Large grey asteroid with a glowing vent (newshd.shp frames 18, 55, 93): a 3D version of its sprite.

Seen in episodes 1-3. The same kind of lumpy grey rock as newshd-5 (see lib_b014.rock), with a
small pit on its right side (columns 18-20, rows 10-14) glowing yellow at the centre and red
round the rim. The frames only cool the glow (bright, dim, out), so one model covers them all: the
vent dims on frame 55 (palette_material frames=) and is gone on frame 93 (common.frame_part), and
the rock round it, lit by the glow on frame 18, darkens on the other two.

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


def face_band(shade, edges, f):
    """The shade band lib.rock paints a top face with, from a frame's Shade (None: underneath)."""
    if f.normal.z < -0.3:
        return None
    cen = f.calc_center_median()
    pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
    vals = [x for x in (shade.at(p.x, p.y, blur=0.3) for p in pts) if x is not None]
    if not vals:
        return 1 if f.normal.z > 0.3 else 0
    k = lib.band_of(edges, sum(vals) / len(vals))
    return max(0, k - 1) if f.normal.z < 0.2 else k


def glow_on_rock(sprite, bm, mats):
    """The rock round the vent is lit by its glow on frame 18 and darker on 55 and 93: give the
    faces whose shade changes a material that takes each frame's shade (palette_material frames=).
    Under the vent this also paints the bare rock frame 93 shows once the vent is gone."""
    first = sprite["frames"][0]
    reps, edges = lib.shade_slots(sprite, first["pixels"], 6, FIRE)  # as lib.rock picked them
    shades = [(f["index"], lib.Shade(sprite, f["pixels"], 2, FIRE)) for f in sprite["frames"][1:]]
    bm.normal_update()
    glow = {}
    for f in bm.faces:
        if face_band(shades[0][1], edges, f) is None:
            continue
        k0 = f.material_index
        per = {i: face_band(sh, edges, f) for i, sh in shades}
        frames = {i: reps[k] for i, k in per.items() if reps[k] != reps[k0]}
        if not frames:
            continue
        key = (k0, *(per[i] for i, _ in shades))
        if key not in glow:
            glow[key] = len(mats)
            mats.append(common.palette_material(sprite, reps[k0], f"{NAME}-glow{''.join(map(str, key))}",
                                                metallic=0.15, roughness=0.85 - 0.04 * k0, frames=frames))
        f.material_index = glow[key]


def build(sprite):
    coll = common.reset_collection(NAME)
    bm, mats, _ = lib.rock(sprite, NAME, sprite["frames"][0]["pixels"], size=2, half_height=0.26,
                           relief=0.07, seed=18, subdiv=3, skip=FIRE)
    glow_on_rock(sprite, bm, mats)
    rock = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # The vent: a red-rimmed pit with a yellow-hot core, set into the rock's top. It cools a step
    # on frame 55 (rim 117 -> 115, hot 122 -> 120, core 126 -> 124) and is out on frame 93.
    vent_tag = f"{NAME}-vent"
    vmats = [
        common.palette_material(sprite, 117, vent_tag, metallic=0.1, roughness=0.6, emission_strength=2.0,
                                frames={55: 115}),
        common.palette_material(sprite, 122, vent_tag, emission_strength=4.0, frames={55: 120}),
        common.palette_material(sprite, 126, vent_tag, emission_strength=6.0, frames={55: 124}),
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
    vent = common.frame_part(common.mesh_object(f"{NAME}_vent", vb, vmats, coll, smooth=True), [18, 55])
    return [(NAME, [rock, vent], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
