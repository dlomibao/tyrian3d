"""Plasma Storm (sidekick 9, tyrian.shp#8 frames 224, 243, 262, 281, 300): a 3D version of its sprite.

A first-shop sidekick, 11 x 13 px. The sprite draws a green bell: a ribbed green canister (rows 1-7)
plugged into a wide grey base (rows 8-12). As a small machine it is a plasma cannon pod lying
nose-forward (up the screen):

- The canister: a round containment tube 5 px across (as tall as it is wide; the sprite shades it
  round), ringed by three raised dark-green bands (index 193, rows 2, 4 and 6) with the glowing
  plasma (emissive) showing between them (rows 3, 5 and 7). Its nose (rows 0-2) narrows to a
  glowing emitter lens (row 1, the brightest green).
- The clamp: the grey pixels down the canister's middle (rows 5-7: 3 px wide, then 1 px) are a
  hard chamfered metal strap block on top of the tube, joined to the collar by a thin rib. Its
  near-white pixel is the metal's sheen, not a bump.
- The collar (row 8): a grey ring round the canister's root with two small green indicator lights
  on top (columns 4 and 6).
- The base: a wide flange 9 px across (row 9, its lit chamfer), a dark recessed groove behind it
  (row 10), the rear housing (row 11) narrowing to a dark back face (row 12) with two small
  thruster nozzles in it (the mid-grey pixels at columns 4 and 6).

The five frames only change the greens (the plasma pulses), so one model covers them all, its
glowing materials animated with palette_material(frames=...) (DECISIONS.md D17).

Run: blender --background --python assets/blender/sidekicks/plasma-storm.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-plasma-storm"
MODEL = "sidekicks/plasma-storm"
P = 1 / 12  # one sprite pixel
AXIS = 5.5  # the pod's centre line, a column edge (canister columns 3-7, base columns 1-9)
SHARP = math.radians(35)  # edges sharper than this stay crisp; the rest is smooth shaded


def ex(col):
    """Sprite column edge to Blender X (the 12x14 block is centred on the origin)."""
    return (col - 6) * P


def ey(row):
    """Sprite row edge to Blender Y."""
    return (7 - row) * P


def tube(bm, sections, mat, sides=16, dx=0.0, cap_start=True, cap_end=True):
    """A loft along the pod's axis; sections are (row edge, half width px, half height px, z px)."""
    start = len(bm.verts)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in sections], sides=sides,
                mat_index=mat, cap_start=cap_start, cap_end=cap_end)
    common.shift_x(bm, start, ex(AXIS + dx))


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = []

    def add(mat):
        mats.append(mat)
        return len(mats) - 1

    def grey(i):
        return add(common.palette_material(sprite, i, NAME, metallic=0.75, roughness=0.3))

    G12, G11, G10, G8, G5, G3, G1 = (grey(i) for i in (12, 11, 10, 8, 5, 3, 1))
    RING = add(common.palette_material(sprite, 193, NAME, metallic=0.55, roughness=0.3))
    RING_LIT = add(common.palette_material(sprite, 195, NAME, metallic=0.55, roughness=0.3))

    def glow(i, part, frames, strength=4.0):
        return add(common.palette_material(sprite, i, f"{NAME}-{part}", metallic=0.0, roughness=0.25,
                                           emission_strength=strength, frames=frames))

    # The pulsing greens, per frame (the brightest pixels of each band in that frame):
    LENS = glow(207, "lens", {262: 203, 281: 203, 300: 203}, 2.5)
    LENS_RIM = glow(202, "lensrim", {262: 197, 281: 197, 300: 197}, 2.5)
    BAND3 = glow(202, "band3", {243: 207, 262: 207, 281: 203, 300: 203}, 2.5)
    BAND5 = glow(196, "band5", {262: 201, 281: 201, 300: 198}, 2.0)
    BAND7 = glow(196, "band7", {262: 197, 281: 201, 300: 201}, 2.0)
    LIGHT = glow(197, "light", {262: 198, 281: 201, 300: 201}, 3.0)

    bm = bmesh.new()
    R = 2.85  # the plasma's radius between the rings, px
    RR = 3.3  # the rings' radius (covers the sprite's outline column half way)

    # --- The canister. The glowing core runs the whole length inside the rings.
    tube(bm, [(2.4, R, R, 0), (3.6, R, R, 0)], BAND3)
    tube(bm, [(4.4, R, R, 0), (5.6, R, R, 0)], BAND5)
    tube(bm, [(6.4, R, R, 0), (7.6, R, R, 0)], BAND7)
    # Raised containment rings, chamfered both sides: rows 4 and 6 (each 1 px), row 2 is the
    # nose's base ring.
    for r0, r1 in ((3.6, 4.4), (5.6, 6.4)):
        tube(bm, [(r0, R - 0.1, R - 0.1, 0), (r0 + 0.15, RR, RR, 0), (r1 - 0.15, RR, RR, 0),
                  (r1, R - 0.1, R - 0.1, 0)], RING)
    # The root ring where the canister enters the collar (row 7.6-8).
    tube(bm, [(7.6, R - 0.1, R - 0.1, 0), (7.75, RR, RR, 0), (8.3, RR, RR, 0)], RING, cap_end=False)

    # --- The nose: the base ring (row 2), a dark-green cowl narrowing over rows 2-1, and the
    # glowing emitter lens standing out of it to row 0.3.
    tube(bm, [(2.4, R - 0.1, R - 0.1, 0), (2.25, RR, RR, 0), (1.85, RR, RR, 0), (1.55, 3.0, 3.0, 0),
              (1.3, 2.45, 2.45, 0), (1.15, 2.0, 2.0, 0)], RING_LIT)
    tube(bm, [(1.2, 2.0, 2.0, 0), (1.05, 1.85, 1.85, 0), (0.95, 1.6, 1.6, 0)], LENS_RIM, cap_start=False)
    tube(bm, [(0.95, 1.6, 1.6, 0), (0.7, 1.45, 1.45, 0), (0.45, 1.05, 1.05, 0), (0.28, 0.5, 0.5, 0),
              (0.22, 0.0, 0.0, 0)], LENS, cap_start=False)

    # --- The clamp on top of the canister (rows 4.85-7, columns 4-6), a chamfered block (an
    # octagon loft is a box with bevelled edges), and its rib back to the collar (column 5).
    tube(bm, [(4.8, 1.25, 0.7, RR + 0.1), (4.95, 1.55, 0.95, RR + 0.1), (6.85, 1.55, 0.95, RR + 0.1),
              (7.0, 1.25, 0.7, RR + 0.1)], G11, sides=8)
    tube(bm, [(6.9, 0.55, 0.55, RR - 0.15), (8.2, 0.55, 0.55, RR - 0.15)], G10, sides=8)

    # --- The collar (row 8): a grey ring 7 px across round the canister's root, chamfered at
    # the front.
    tube(bm, [(7.85, RR, RR, 0), (7.9, 3.5, 3.4, 0), (8.15, 3.85, 3.7, 0), (9.0, 3.85, 3.7, 0)], G12,
         sides=24, cap_end=False)
    # Its two indicator lights on top (columns 4 and 6): small glowing pads set into it.
    for dx in (-1.0, 1.0):
        tube(bm, [(8.05, 0.0, 0.0, 3.6), (8.2, 0.4, 0.3, 3.65), (8.75, 0.4, 0.3, 3.65), (8.9, 0.0, 0.0, 3.6)],
             LIGHT, sides=8, dx=dx * 1.05)

    # --- The flange (row 9, 9 px wide plus the outline): a lit chamfer stepping out from the
    # collar, a flat rim, and a chamfer down into the groove. A little flatter than wide.
    FW, FH = 5.0, 4.25
    tube(bm, [(9.0, 3.85, 3.7, 0), (9.0, 4.2, 3.75, 0), (9.45, FW, FH, 0), (10.15, FW, FH, 0),
              (10.4, FW - 0.4, FH - 0.35, 0), (10.4, 4.0, 3.5, 0)], G11, sides=24, cap_start=False, cap_end=False)
    # The dark groove behind it (row 10).
    tube(bm, [(10.4, 4.0, 3.5, 0), (10.9, 4.0, 3.5, 0)], G3, sides=24, cap_start=False, cap_end=False)
    # The rear housing (row 11), narrowing to the back face (row 12).
    tube(bm, [(10.9, 4.0, 3.5, 0), (10.9, 4.55, 3.9, 0), (11.15, 4.75, 4.05, 0), (11.85, 4.6, 3.95, 0),
              (12.45, 3.9, 3.35, 0), (12.7, 3.3, 2.85, 0)], G8, sides=24, cap_start=False, cap_end=False)
    tube(bm, [(12.7, 3.3, 2.85, 0), (12.75, 2.9, 2.5, 0)], G3, sides=24, cap_start=False)

    # --- Two thruster nozzles out of the back face (columns 4 and 6): short grey bells, dark
    # inside.
    for dx in (-1.05, 1.05):
        tube(bm, [(12.5, 0.75, 0.75, 0), (12.8, 0.8, 0.8, 0), (13.15, 0.95, 0.95, 0)], G5, sides=10,
             dx=dx, cap_end=False)
        tube(bm, [(13.15, 0.95, 0.95, 0), (13.15, 0.65, 0.65, 0), (12.9, 0.6, 0.6, 0)], G1, sides=10,
             dx=dx, cap_start=False)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False
    return [common.mesh_object(NAME, bm, mats, coll, smooth=True)]


if __name__ == "__main__":
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    objects = build(sprite)
    common.export_sprite_model(root, objects, MODEL, sprite["sprites"])
    tris = sum(len(p.vertices) - 2 for o in objects for p in o.data.polygons)
    print(f"triangles: {tris}")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        common.render_frame_previews(objects, out, sprite, root)
