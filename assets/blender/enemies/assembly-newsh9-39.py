"""Grey robot arm (newsh9.shp, assembly of 3 pieces: newsh9-1, newsh9-3, newsh9-39): a 3D version of its sprites.

Seen in episode 4 (level 4.20). The left-hand arm (assembly-newsh9-45 is its mirror image). Three 2x2 enemies in an L make one
48x56 px arm: a rounded shoulder housing with two knuckles at the top, a jaw block under it, a
big grey upper arm with a socket ring round a dark opening, a ball joint at its lower end, and a
forearm drum beside a looped claw (a round hoop bending down into a thick pipe) holding a glowing
blue gem. Each piece is one frame, so one model per piece.

Built whole in assembly coordinates by `build_arm` here (a taller rework of lib_b028.build_arm,
using that module's geometry helpers), then cut into the pieces with common.split_assembly. The
mirrored right arm still uses lib_b028.build_arm.

Heights (sprite px): shoulder drum about 9 tall with its knuckle domes to about 11, lit upper
arm block about 9.5 with the socket ring standing proud of it, the shaded upper-arm tube beside
it about 8 (round), ball joint about 9 with a broad lit cap, forearm drum about 7, the claw one
open C of round tubing about 5 tall running on as the pipe to the gem, gem ball about 6.5.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-39.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b028 as lib  # noqa: E402
from lib_b028 import PX, W, H, X, Y, sweep, ellipsoid, plate  # noqa: E402

GEM_A, GEM_B = 2.65, 2.3
PIECES = ["newsh9-1", "newsh9-3", "newsh9-39"]


def capped_ball(bm, col, row, z, a_px, b_px, rz, mat=0, cap_mat=None, flat=0.55, segments=16, rings=8):
    """An ellipsoid centred on (col, row) at height z whose upper half is pushed out towards a
    broad, gently domed top (each vertex's height fraction t above the centre becomes t**flat),
    so it reads as a lit cap from above. Faces facing straight up take `cap_mat`."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        t = v.co.z
        if t > 0:
            t = t ** flat
        v.co = (X(col + v.co.x * a_px), Y(row + v.co.y * b_px), z + t * rz)
    new = set(bm.faces) - before
    lib._faces(bm, new, mat, True)
    if cap_mat is not None:
        for f in new:
            f.normal_update()
            if f.normal.z > 0.9:
                f.material_index = cap_mat


def paint(bm, faces, mat, test):
    """Give the faces in `faces` that pass test(normal, (col, row)) material `mat` (normals must be
    up to date)."""
    for f in faces:
        f.normal_update()
        ctr = f.calc_center_median()
        if test(f.normal, (ctr.x * 12 + W / 2, H / 2 - ctr.y * 12)):
            f.material_index = mat


def round_sweep(bm, path, sides=12, mat=0, roundness=1.0, lift=0.0, **kw):
    """sweep() for a drum lying on the ground: each ring's half-height is its half-width times
    `roundness`, and it sits on z = lift."""
    pts = []
    for c, r, w in path:
        h = w * PX * roundness
        pts.append((c, r, lift + h, w, h))
    sweep(bm, pts, sides=sides, mat=mat, **kw)


def build_arm(name, sprite, coll):
    """The whole left arm as one object in its 48 x 56 px assembly grid (pixel-edge coordinates:
    pixel column c spans c..c+1, rows count down the screen). Nothing goes below z = 0."""
    tag = name
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        # Painted grey metal throughout (metallic about 0.45, roughness about 0.4): the game's
        # light makes the sprite's drawn sheen; the dark hollows are matte.
        pal(9, metallic=0.45, roughness=0.38),  # 0 lit grey faces
        pal(5, metallic=0.45, roughness=0.42),  # 1 shaded grey faces
        pal(2, metallic=0.1, roughness=0.75),  # 2 dark undersides
        pal(3, metallic=0.05, roughness=0.85),  # 3 dark hollows
        pal(7, metallic=0.45, roughness=0.38),  # 4 mid grey housings
        pal(10, metallic=0.5, roughness=0.32),  # 5 bright rims
        pal(12, metallic=0.5, roughness=0.3),  # 6 highlights (unused: the sprite's hot spots are sheen)
        pal(4, metallic=0.4, roughness=0.45),  # 7 dark grey
        pal(6, metallic=0.45, roughness=0.4),  # 8 grey neck
        pal(153, metallic=0.0, roughness=0.1, emission_strength=4.0),  # 9 blue gem (glossy glow)
        pal(158, metallic=0.0, roughness=0.1, emission_strength=5.0),  # 10 gem highlight (unused)
        pal(8, metallic=0.45, roughness=0.38),  # 11 light-mid grey
    ]
    LIT, SHADE, UNDER, HOLLOW, MID, RIM, HI, DARK, NECK, GEM, GEMHI, LMID = range(12)
    bm = bmesh.new()

    # Shoulder housing at the top right (rows 2-11, columns 24-47): a round drum lying across the
    # screen, about as tall as it is deep (9 px), with two knuckle domes on top.
    round_sweep(bm, [(23.8, 8.1, 0.0), (24.8, 8.0, 1.3), (27.0, 7.7, 3.1), (30.0, 7.3, 3.5),
                     (34.0, 6.5, 4.4), (39.0, 6.6, 4.2), (43.0, 7.0, 3.9), (45.6, 8.2, 2.95),
                     (46.8, 8.1, 1.7), (47.3, 8.1, 0.0)], sides=14, mat=MID)
    # Knuckle domes: two low rounded knuckles (two separate bright spots, each ringed darker, so
    # real bumps), about 1.5 px proud of the drum, all one light grey; their hot spots are sheen.
    ellipsoid(bm, 37.4, 5.9, 0.70, 2.3, 2.4, 0.15, mat=RIM, segments=14, rings=8)
    ellipsoid(bm, 41.6, 6.8, 0.66, 2.0, 2.2, 0.145, mat=RIM, segments=14, rings=8)

    # Neck between the housing and the upper arm (rows 8-13).
    plate(bm, [(16.5, 12.2), (19, 9.2), (20.4, 8.05), (24.2, 7.4), (26, 7.3), (34, 8.5), (37, 11), (36, 13.5),
               (26, 13.5)], 0.0, 0.5, mat=NECK, bevel=0.8)
    # Mouth: the dark gap between the housing and the jaw (rows 11-13), with the sprite's notch.
    plate(bm, [(35, 11), (45, 10.8), (45, 12), (42.2, 12.2), (42.2, 13), (44.2, 13), (44.2, 14),
               (35, 14)], 0.0, 0.16, mat=HOLLOW)

    # Jaw block under the housing (rows 13-21, columns 35-45) and its dark underside (rows 21-27)
    # sloping away below it.
    plate(bm, [(35.5, 14), (45, 13.8), (45, 21), (43, 22), (37.5, 21.5), (35, 18.5)],
          0.0, 0.46, mat=LIT, bevel=1.0)
    plate(bm, [(35.5, 21), (45, 20.5), (44.6, 23), (41.5, 26.5), (39.5, 27.6), (36, 27.6)],
          0.0, 0.4, mat=SHADE, tilt=(0.0, -0.04, 0, 21), bevel=0.6)

    # Upper arm: the lit block (columns 17-27, rows 11-21), about 9.5 px tall, beside a round
    # shaded tube about 8 px wide and as tall running down to the lower left (columns 9-21,
    # rows 12-28), and the dark underside under it (rows 24-30) that runs down to the claw as a
    # low collar.
    plate(bm, [(17, 12.5), (20.5, 10.5), (26.5, 11), (27, 14), (26.6, 20.5), (26.2, 23), (24.5, 23.6),
               (20.5, 21), (17.6, 18)], 0.0, 0.8, mat=LIT, bevel=2.0)
    round_sweep(bm, [(19.4, 12.0, 0.0), (19.0, 12.8, 2.6), (18.4, 14.5, 3.2), (17.6, 19.0, 4.0),
                     (14.6, 22.3, 4.2), (12.5, 25.2, 3.7), (12.0, 27.4, 2.6), (11.8, 28.2, 0.0)],
                sides=12, mat=SHADE, roundness=0.95)
    # It leaves the sprite's near-black slot (columns 15-17, rows 26-29) between the tube's end
    # and the ball joint cut down to a thin dark floor.
    plate(bm, [(8.2, 24.3), (18.4, 24.5), (18.4, 25.8), (14.8, 25.8), (14.8, 29.2), (18.4, 29.2),
               (18.4, 30.6), (6.8, 30.9), (8.2, 29.6)],
          0.0, 0.42, mat=DARK, tilt=(0.0, -0.02, 0, 24.3), bevel=0.6)
    plate(bm, [(14.8, 25.8), (18.4, 25.8), (18.4, 29.2), (14.8, 29.2)], 0.0, 0.08, mat=HOLLOW)

    # Ball joint at the upper arm's lower end (columns 17-25, rows 19-30): a round ball about
    # 9 px tall in the lit grey; the sprite's lighter oval and hot spot on it are the light on a
    # metal ball, which the game draws.
    capped_ball(bm, 21.5, 24.6, 0.37, 4.75, 5.2, 0.37, mat=LIT, flat=1.0, segments=18, rings=10)

    # Socket: a dark pit (columns 26-38, rows 12-27) inside a bright ring that stands proud of the
    # arm and the jaw, and the light pipe curling through it.
    plate(bm, [(26, 14), (30, 13.5), (34, 14.5), (37, 19), (36.2, 22.5), (36.2, 27.9), (33.6, 28.1), (32.4, 27.6),
               (30.0, 25.2), (28.6, 23.8), (26.4, 22.6)],
          0.0, 0.12, mat=HOLLOW)
    plate(bm, [(28.5, 18), (31.5, 17), (34, 20), (33, 23), (30, 22)], 0.0, 0.13, mat=UNDER)
    sweep(bm, [(25.6, 15.0, 0.72, 1.5, 0.12), (27.4, 13.4, 0.7, 1.8, 0.14), (30.5, 13.0, 0.6, 1.9, 0.15),
               (33.6, 14.0, 0.55, 1.9, 0.15), (35.4, 16.0, 0.52, 1.8, 0.14), (37.0, 18.4, 0.48, 1.6, 0.13),
               (38.6, 20.0, 0.44, 1.2, 0.1)], sides=10, mat=RIM)
    sweep(bm, [(28.0, 21.0, 0.12, 0.0, 0.0), (28.8, 21.8, 0.16, 1.4, 0.11), (30.3, 24.0, 0.18, 1.7, 0.13),
               (32.6, 25.4, 0.18, 1.7, 0.13), (34.6, 26.6, 0.16, 1.4, 0.11), (35.6, 27.3, 0.12, 0.0, 0.0)],
          sides=8, mat=LMID)

    # Forearm drum hanging under the upper arm (columns 15-23, rows 29-40): a round pod about 7 px
    # tall.
    round_sweep(bm, [(18.8, 28.9, 0.0), (18.8, 29.3, 3.2), (18.8, 30.6, 4.3), (18.8, 36.0, 4.3),
                     (18.2, 38.2, 3.2), (18.2, 39.6, 2.2), (18.1, 40.3, 0.0)],
                sides=14, mat=MID, roundness=0.85)

    # The claw (columns 5-14, rows 31-46) over a flat dark plate about 3 px thick. The hole, and
    # the near-black slot between the claw and the forearm drum, cut down to a thin dark floor.
    plate(bm, [(4.9, 32.2), (6.0, 31.0), (15.2, 30.8), (15.2, 38.4), (13.2, 39.4), (5.0, 39.4)], 0.0, 0.05,
          mat=HOLLOW)
    plate(bm, [(5.0, 38.2), (15.8, 38.2), (15.9, 40.4), (15.4, 42.0), (14.9, 43.6), (14.0, 44.6), (13.4, 46.0), (12.9, 47.6),
               (11.0, 47.2), (8.6, 46.6), (4.4, 46.6), (4.3, 44.2), (5.1, 42.8)], 0.0, 0.25, mat=DARK, bevel=0.6)
    # The claw: one open C of round tubing (about 3.5 px across and 5 px tall). It starts at the
    # hoop's lower left, arcs up over the top and down the right-hand side, and runs on as the
    # pipe down the forearm's edge into the gem. Its crown takes the light greys: mid grey over
    # the top and the left, the lit grey (the sprite's light run) down the right side and the
    # pipe.
    hc, hr = 10.0, 35.6  # the hoop's centre
    path = [(7.5, 37.7, 0.0), (7.1, 37.1, 1.3), (6.9, 36.1, 1.55), (6.95, 34.8, 1.75), (7.5, 33.6, 2.0),
            (8.4, 32.85, 2.15), (9.7, 32.6, 2.25), (11.0, 32.8, 2.05), (12.1, 33.4, 1.7), (12.9, 34.4, 1.45),
            (13.2, 35.6, 1.3), (13.3, 37.0, 1.3), (13.2, 38.4, 1.35), (13.0, 39.6, 1.4), (12.6, 40.8, 1.45),
            (12.0, 42.2, 1.5), (11.3, 43.5, 1.5), (10.4, 44.7, 1.5), (9.5, 45.7, 1.45), (8.7, 46.5, 1.3)]
    zc = 2.8 * PX
    before = set(bm.faces)
    sweep(bm, [(c, r, zc, w, w * 1.35 * PX) for c, r, w in path], sides=12, mat=SHADE)
    claw = list(set(bm.faces) - before)
    bmesh.ops.recalc_face_normals(bm, faces=claw)

    def right_run(cr):
        return (cr[1] <= hr and cr[0] > hc + 0.4) or (cr[1] > hr and cr[0] > 8.6)

    # One grey per run, not the sprite's light and dark bands: the hoop light-mid grey, the
    # brighter pipe down the right side and into the gem the lit grey.
    paint(bm, claw, LMID, lambda n, cr: True)
    paint(bm, claw, LIT, lambda n, cr: right_run(cr))

    # The gem (columns 4-8, rows 47-50): a round sky-blue ball about 5 px across and 6.5 px tall
    # in a dark cup; glossy, so its pale highlight is the game's shine.
    plate(bm, [(2.6, 46.4), (10.0, 46.0), (12.0, 47.2), (11.8, 49.0), (10.8, 50.8), (9.8, 51.8), (4.9, 51.7), (3.4, 49.8)],
          0.0, 0.14, mat=UNDER, bevel=0.5)
    before = set(bm.faces)
    ellipsoid(bm, 0.0, 0.0, 3.5 * PX, GEM_A, GEM_B, 3.0 * PX, mat=GEM, segments=18, rings=10)
    gem = set(bm.faces) - before
    ca, sa = math.cos(math.radians(37)), math.sin(math.radians(37))
    for v in {v for f in gem for v in f.verts}:  # turn it to the sprite's diagonal and move it
        u, w = v.co.x * 12 + W / 2, H / 2 - v.co.y * 12  # pixel coords about (0, 0)
        v.co.x, v.co.y = X(6.55 + u * ca - w * sa), Y(48.9 + u * sa + w * ca)

    return lib.to_object(name, bm, mats, coll)


def run(script_file, name, pieces):
    """Build the arm, split it into its pieces, export each, and render previews if asked
    (lib_b028.run_assembly with this script's build_arm)."""
    root = common.repo_root(script_file)
    sprite = lib.merged_sprite(root, pieces)
    coll = common.reset_collection(name)
    obj = build_arm(name, sprite, coll)
    lay = sprite["assemblyLayout"]
    minx = min(e["cx"] for e in lay)
    miny = min(e["cy"] for e in lay)
    corners = [(e["model"], e["cx"] - minx, e["cy"] - miny) for e in lay]
    layout = [(n, c0 + 12 - W / 2, r0 + 14 - H / 2) for n, c0, r0 in corners]
    parts = common.split_assembly(obj, layout)
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, [parts[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(root, corners, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)


if __name__ == "__main__":
    run(__file__, "assembly-newsh9-39", PIECES)
