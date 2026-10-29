"""Grey carapace bunker with a stepped pyramid roof (newsh2.shp, assembly of 4 pieces): a 3D
version of its sprites.

Seen in episode 1 (levels 1.28 and 1.3) and episode 3. Four 2x2 ground sprites (newsh2-81 and
newsh2-83 on top, newsh2-119 and newsh2-121 below; sprite.json `assemblyLayout`) make one 48x56
px tile of dirt with a structure on it: a dark grey armoured carapace, rounded at the back (top of
the screen) and splitting into two pointed prongs at the front, with a tan stepped pyramid roof on
its middle whose wide base ends in two wing tips, two pipe legs a side running from the carapace
down into the dirt, a faceted tan spike between the prongs and a long cast shadow to the lower
right. The newsh2-229 piece listed below it in the layout is a separate object (another batch), so
it isn't built here.

Remodelled on the concept (assets/blender/features/concepts/): each part sits where the registered
concept (assets/blender/textures/<name>/concept.png, the concept's whole frame on the 48x56 tile)
draws it, so the detail texture_bake.py projects onto it lands on the right part. The carapace is
a chamfered armour shell with an outer rim and three raised plates on top (side plates and a
centre band split by grooves, a cross seam on each side plate and each prong); the pyramid is three
stacked stages: a wide base with blade-like wing tips, a chevron step, and a four-faced point with
crisp ridges. The legs are round pipes with collars at the shell and elbows down into flanged
foot plates. Broken struts lie in the cast shadow (the concept's debris).

The sprites fill their tiles with dirt, so the model is a thin dirt platform (base at z = 0)
with the structure on it, built once in assembly coordinates and cut into the four pieces with
common.split_assembly. The structure is mirror symmetric about pixel-edge column 20.5. The sprite
draws the pyramid's right faces and the right prong dark: that is the light, not paint, so both
halves share one colour.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-119.py [-- --preview out.png]
(the preview is the whole tile; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b129 as lib  # noqa: E402

NAME = "assembly-newsh2-119"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-81", "newsh2-83", "newsh2-119", "newsh2-121"]
# Assembly pixel (0, 0) is the top-left corner of newsh2-81 (screen cx 248 - 12, cy 139 - 14);
# the assembly is 48 x 56 px and its centre (screen 260, 153) is the Blender origin.
CX0, CY0 = 260, 153
W, H = 48, 56
G = lib.Grid(W, H)
PX = lib.PX
AXIS = 20.5  # mirror axis, in pixel-edge columns

SHELL_Z = 0.26  # carapace shell top
PLATE_Z = 0.31  # raised plates on it


def E(c, r, z=0.0):
    """Pixel-edge column and row (as traced on concept.png) to a Blender point."""
    return Vector(((c - W / 2) * PX, (H / 2 - r) * PX, z))


def M(pts):
    """Mirror (col, row) points about the axis, keeping the winding usable."""
    return [(2 * AXIS - c, r) for c, r in reversed(pts)]


def inset(pts, d):
    """Offset a closed (col, row) outline inward by d px (mitred corners)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        k = d / max(0.3, b.dot(n0))
        q = p1 + b * k
        out.append((q.x, q.y))
    return out


def loft(bm, rings, mat, cap_start=True, cap_end=True):
    """Side faces between closed outlines [(pts, z)] of equal length, capped at both ends."""
    vr = [[bm.verts.new(E(c, r, z)) for c, r in pts] for pts, z in rings]
    return lib._faces(bm, vr, True, mat, False, cap_start, cap_end)


def bevel_plate(bm, pts, z0, z1, bevel_px, mat, bevel_z=None):
    """A plate with vertical sides from z0 and a chamfered top edge (inset bevel_px)."""
    bz = bevel_z if bevel_z is not None else min(z1 - z0, bevel_px * PX) * 0.8
    loft(bm, [(pts, z0), (pts, z1 - bz), (inset(pts, bevel_px), z1)], mat)


def arc(cx, cy, rad, a0, a1, n):
    return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy - rad * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def sweep_e(bm, path, **kw):
    """lib.sweep with pixel-edge (col, row) coordinates."""
    return lib.sweep(bm, G, [(c - 0.5, r - 0.5, z, w, h) for c, r, z, w, h in path], **kw)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh2_119"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(19, metallic=0.0, roughness=0.95),  # 0 dirt
        pal(2, metallic=0.0, roughness=1.0),  # 1 cast shadow
        pal(5, metallic=0.45, roughness=0.45),  # 2 carapace shell and rim
        pal(6, metallic=0.45, roughness=0.4),  # 3 raised armour plates
        pal(23, metallic=0.35, roughness=0.55),  # 4 pipes
        pal(21, metallic=0.3, roughness=0.6),  # 5 pipe collars and foot plates
        pal(24, metallic=0.15, roughness=0.6),  # 6 pyramid, spike
        pal(3, metallic=0.2, roughness=0.8),  # 7 broken struts
    ]
    DIRT, SHADOW, SHELL, PLATE, PIPE, COLLAR, PYR, STRUT = range(8)
    PYR_SIDE = PYR
    bm = bmesh.new()

    # Dirt platform over the whole tile, and the cast shadow on it.
    lib.plate(bm, G, [(0, 0), (W, 0), (W, H), (0, H)], 0.0, 0.03, mat=DIRT)
    lib.plate(bm, G, [(17, 27), (36, 27), (40.5, 30), (41.5, 36), (41, 44), (36, 46.5), (33, 51),
                      (29, 52.5), (22, 51.5), (17, 50), (14, 47.5), (17.5, 45)],
              0.03, 0.036, mat=SHADOW)

    # Carapace: one armour shell from the round back (row 3.3) down the sides and into the two
    # prongs (columns 10-18 and 23-31), whose outer front corners are chamfered to a point.
    back = arc(15.5, 8.6, 5.5, 180, 90, 5) + arc(25.5, 8.6, 5.5, 90, 0, 5)  # left to right
    shell = back + [(31, 42.5), (28.3, 47), (23.2, 47), (23.2, 29.5), (17.8, 29.5), (17.8, 47),
                    (12.7, 47), (10, 42.5)]
    bevel_plate(bm, shell, 0.03, SHELL_Z, 0.9, SHELL, bevel_z=0.06)

    # Raised plates on the shell, split by grooves (the concept's seams): a centre band between
    # columns 17.8 and 23.2, side plates with a cross seam at row 13, and two plates per prong with
    # a riveted seam at row 34.5.
    g = 0.35  # half a groove
    cband = arc(20.5, 7.0, 2.6 - g, 180, 0, 4)
    cband = [(c, r) for c, r in cband]
    plates = [
        cband + [(23.2 - g, 28.5), (17.8 + g, 28.5)],
        arc(15.5, 8.6, 4.5, 180, 100, 4) + [(17.8 - g, 4.2), (17.8 - g, 13 - g), (11.1, 13 - g)],
        [(11.1, 13 + g), (17.8 - g, 13 + g), (17.8 - g, 28.5), (11.1, 28.5)],
        [(11.1, 28.5), (17.8 - g, 28.5), (17.8 - g, 34.5 - g), (11.1, 34.5 - g)],
        [(11.1, 34.5 + g), (17.0, 34.5 + g), (17.0, 46.1), (13.2, 46.1), (11.1, 42.4)],
    ]
    for pts in plates:
        bevel_plate(bm, pts, SHELL_Z - 0.01, PLATE_Z, 0.45, PLATE, bevel_z=0.03)
    for pts in plates[1:]:
        bevel_plate(bm, M(pts), SHELL_Z - 0.01, PLATE_Z, 0.45, PLATE, bevel_z=0.03)

    # Pipe legs, two a side: a collar at the shell's flank, a straight run down and out, an elbow
    # down into a flanged foot plate in the dirt.
    for side in (1, -1):
        cx = (lambda c: c) if side == 1 else (lambda c: 2 * AXIS - c)
        for r0 in (9.8, 15.0):
            sweep_e(bm, [(cx(10.6), r0, 0.2, 0.9, 0.075), (cx(5.6), r0 + 4.3, 0.13, 0.9, 0.075),
                         (cx(4.4), r0 + 5.0, 0.09, 0.9, 0.075), (cx(3.9), r0 + 5.3, 0.04, 0.9, 0.075)],
                    sides=8, mat=PIPE)
            sweep_e(bm, [(cx(10.9), r0 - 0.25, 0.2, 1.25, 0.1), (cx(9.6), r0 + 0.85, 0.19, 1.25, 0.1)],
                    sides=8, mat=COLLAR, smooth=False)
            foot = [(2.2, r0 + 3.8), (5.6, r0 + 3.8), (5.6, r0 + 7.0), (2.2, r0 + 7.0)]
            if side == -1:
                foot = M(foot)
            bevel_plate(bm, foot, 0.02, 0.07, 0.4, COLLAR, bevel_z=0.02)

    # Stepped pyramid roof. Base stage: a wide slab with blade-like wing tips past the carapace.
    base = [(6.0, 27.6), (10.6, 22.6), (30.4, 22.6), (35.0, 27.6), (31.0, 28.9), (10.0, 28.9)]
    loft(bm, [(base, PLATE_Z - 0.02), (base, 0.33), (inset(base, 1.1), 0.42)], PYR_SIDE)
    # Second stage: a chevron step.
    mid = [(12.4, 20.0), (20.5, 15.0), (28.6, 20.0), (28.2, 23.6), (20.5, 25.6), (12.8, 23.6)]
    loft(bm, [(mid, 0.41), (mid, 0.46), (inset(mid, 0.9), 0.52)], PYR)
    # Top: a four-faced point (back point at row 12.2, front corner at row 23.2) on a thin lip.
    kite = [(20.5, 12.2), (26.2, 18.6), (20.5, 23.2), (14.8, 18.6)]
    lip = inset(kite, -0.5)
    loft(bm, [(lip, 0.5), (lip, 0.56), (kite, 0.57)], PYR_SIDE, cap_end=False)
    kv = [bm.verts.new(E(c, r, 0.57)) for c, r in kite]
    peak = bm.verts.new(E(20.5, 18.4, 0.86))
    for i in range(4):
        f = bm.faces.new((kv[i], kv[(i + 1) % 4], peak))
        f.material_index = PYR
        f.smooth = False

    # Faceted drill spike under the pyramid's front, between the prongs.
    sweep_e(bm, [(20.5, 28.4, 0.2, 1.7, 0.1), (20.5, 30.2, 0.2, 1.6, 0.1), (20.5, 30.4, 0.2, 1.35, 0.085),
                 (20.5, 32.3, 0.19, 1.25, 0.08), (20.5, 32.5, 0.19, 1.0, 0.065), (20.5, 34.4, 0.18, 0.85, 0.055),
                 (20.5, 36.6, 0.16, 0.0, 0.0)], sides=6, mat=PYR, smooth=False)

    # Broken struts lying in the shadow (the concept's debris).
    for (c0, r0), (c1, r1) in [((33, 37), (44, 44)), ((34, 43), (43, 37.5)), ((31, 46), (37, 41)),
                               ((36, 48), (41, 45))]:
        sweep_e(bm, [(c0, r0, 0.05, 0.35, 0.025), (c1, r1, 0.05, 0.35, 0.025)], sides=4, mat=STRUT,
                smooth=False)

    # The dirt's rocks and pebbles come from the concept's baked detail, not geometry.

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        tiles = [(n, cx + W // 2 - 12, cy + H // 2 - 14) for n, cx, cy in layout]
        ref, size = lib.composite_png(ROOT, tiles, W, H, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=size, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
