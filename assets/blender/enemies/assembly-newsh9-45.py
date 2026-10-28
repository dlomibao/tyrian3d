"""Grey robot arm (newsh9.shp, assembly of 3 pieces: newsh9-5, newsh9-7, newsh9-45): a 3D version of its sprites.

Seen in episode 4 (level 4.20). The right-hand arm: the left one (assembly-newsh9-39) mirrored and shifted
one pixel, as its sprites are (the right arm's pixel column c is the left arm's column 48 - c). Three 2x2
enemies in an L make one 48x56 px arm: a rounded shoulder housing with two knuckles at the top, a jaw
block under it, a big grey upper arm with a socket ring round a dark opening, and a forearm ending in a
looped claw holding a glowing blue gem. Each piece is one frame, so one model per piece.

Built whole in assembly coordinates (laid out as the left arm, then mirrored), then cut into the
pieces with common.split_assembly. The geometry helpers come from lib_b028 (shared with the left arm);
the arm itself is built here, at the heights the sprite's shading implies: the housing a tall drum, the
plates 5-6 px thick with rounded edges, the forearm, claw pipes and gem round, and the socket and the
claw's gap cut in.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-45.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b028  # noqa: E402
from lib_b028 import PX, W, H, X, Y, sweep, ellipsoid, plate, to_object  # noqa: E402

common = lib_b028.common

PIECES = ["newsh9-5", "newsh9-7", "newsh9-45"]


def rplate(bm, outline, z0, z1, mat=0, r=1.5, steps=3, tilt=None):
    """A prism from z0 up to z1 over an outline of (col, row) pixel edges whose top edge is rounded
    over a radius of `r` px (in `steps` facets), so the plate's rim catches the light like a
    pressed or cast part. `tilt` (dz_per_col, dz_per_row, col0, row0) slopes the top."""
    pts = [(X(c), Y(r_)) for c, r_ in outline]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        pts = list(reversed(pts))

    def dz(x, y):
        if not tilt:
            return 0.0
        c, rr = x * 12 + W / 2, H / 2 - y * 12
        return tilt[0] * (c - tilt[2]) + tilt[1] * (rr - tilt[3])

    rz = min(r * PX, (z1 - z0) * 0.6)
    layers = [[bm.verts.new((x, y, z0)) for x, y in pts]]
    for k in range(steps + 1):
        a = 0.5 * math.pi * k / steps
        d = r * PX * (1 - math.cos(a))
        ring = lib_b028._inset(pts, d) if d > 1e-6 else pts
        z = z1 - rz + rz * math.sin(a)
        layers.append([bm.verts.new((x, y, z + dz(x, y))) for x, y in ring])
    n = len(pts)
    faces = [bm.faces.new(list(reversed(layers[0]))), bm.faces.new(layers[-1])]
    for lo, hi in zip(layers, layers[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((lo[i], lo[j], hi[j], hi[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def build_arm(name, sprite, coll):
    """The right arm in its assembly grid: built in the left arm's layout and mirrored at the end."""
    tag = name
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.3, roughness=0.4),  # 0 lit grey faces
        pal(5, metallic=0.3, roughness=0.45),  # 1 shaded grey faces
        pal(2, metallic=0.2, roughness=0.6),  # 2 dark undersides
        pal(3, metallic=0.2, roughness=0.7),  # 3 dark hollows
        pal(7, metallic=0.35, roughness=0.35),  # 4 mid grey housings
        pal(10, metallic=0.4, roughness=0.3),  # 5 bright rims
        pal(12, metallic=0.4, roughness=0.25),  # 6 highlights
        pal(4, metallic=0.3, roughness=0.5),  # 7 dark grey
        pal(6, metallic=0.3, roughness=0.4),  # 8 grey neck
        pal(153, emission_strength=4.0),  # 9 blue gem
        pal(158, emission_strength=5.0),  # 10 gem highlight
        pal(8, metallic=0.35, roughness=0.3),  # 11 light-mid grey
        pal(1, metallic=0.2, roughness=0.7),  # 12 black hole
    ]
    LIT, SHADE, UNDER, HOLLOW, MID, RIM, HI, DARK, NECK, GEM, GEMHI, LMID, BLACK = range(13)
    bm = bmesh.new()

    # Shoulder housing at the top (rows 2-11, 22 px across): a tall rounded drum lying across the
    # screen, about as tall as it is deep, with two knuckles standing on top of it.
    sweep(bm, [(23.6, 8.0, 0.12, 0.0, 0.0), (24.6, 7.9, 0.15, 1.6, 0.2), (27.0, 7.3, 0.18, 3.0, 0.3),
               (30.0, 7.0, 0.2, 3.4, 0.37), (34.0, 6.6, 0.21, 4.4, 0.41), (39.0, 6.8, 0.21, 4.3, 0.41),
               (43.0, 7.0, 0.2, 3.9, 0.38), (45.6, 7.3, 0.18, 3.0, 0.3), (46.8, 7.6, 0.15, 1.5, 0.16),
               (47.1, 7.8, 0.13, 0.0, 0.0)], sides=14, mat=MID)
    ellipsoid(bm, 37.6, 6.2, 0.56, 2.1, 2.6, 0.2, mat=RIM)
    ellipsoid(bm, 42.2, 6.8, 0.52, 1.8, 2.4, 0.18, mat=RIM)
    ellipsoid(bm, 37.9, 6.0, 0.74, 0.9, 1.2, 0.04, mat=HI, segments=10, rings=5)
    ellipsoid(bm, 42.4, 6.6, 0.68, 0.7, 1.0, 0.035, mat=HI, segments=10, rings=5)

    # Neck between the housing and the upper arm (rows 8-13).
    # (Its outer edge reaches the sprite's dark outline pixels down the right arm's right side.)
    rplate(bm, [(15.2, 13.5), (20.2, 8), (26, 8), (34, 8.5), (37, 11), (36, 13.5), (26, 13.5)],
           -0.17, 0.25, mat=NECK, r=1.2)
    # Mouth: the dark gap between the housing and the jaw (rows 11-13, columns 36-45), cut in.
    plate(bm, [(35, 11), (45.5, 10.5), (45.5, 14), (35, 14)], -0.17, -0.04, mat=HOLLOW)

    # Jaw block under the housing (rows 13-21, columns 35-45) and its dark underside (rows 21-27)
    # falling away from it.
    rplate(bm, [(35.5, 14), (45, 13.8), (45, 21), (43, 22), (37.5, 21.5), (35, 18.5)],
           -0.17, 0.3, mat=LIT, r=1.5)
    plate(bm, [(35.5, 21), (45, 20.5), (44.6, 23), (41.5, 26.5), (39.5, 27.6), (36, 27.6)],
          -0.2, 0.16, mat=DARK, tilt=(0.0, -0.03, 0, 21))

    # Upper arm: the lit face (columns 17-26, rows 11-30) on a rounded shaded cowl to its lower
    # left (columns 9-18, rows 13-25) whose underside (rows 24-30) falls away in shadow.
    rplate(bm, [(17, 12.5), (20.5, 10.5), (26.5, 11), (27, 14), (26.5, 26), (22.5, 30.2), (17, 30.2), (17, 18)],
           -0.2, 0.34, mat=LIT, r=1.6)
    rplate(bm, [(15.2, 13), (21, 13), (21, 25), (8, 24.3), (9.2, 22), (10, 21), (12.5, 19), (13.2, 18),
                (14.2, 17), (15, 16.6)],
           -0.2, 0.29, mat=SHADE, r=2.0, steps=4, tilt=(0.005, 0.0, 21, 0))
    plate(bm, [(8, 24.3), (17.8, 24.5), (17.8, 30.5), (8, 30.5)],
          -0.2, 0.17, mat=UNDER, tilt=(0.0, -0.03, 0, 24.3))
    # Highlight ridge on the edge between the lit face and the cowl, and the pin on it.
    sweep(bm, [(20.8, 19.6, 0.34, 0.0, 0.0), (20.4, 20.4, 0.34, 0.9, 0.05), (19.2, 22.6, 0.33, 0.8, 0.045),
               (18.3, 25.5, 0.32, 0.7, 0.04), (17.9, 27.2, 0.31, 0.0, 0.0)], sides=6, mat=RIM)
    ellipsoid(bm, 20.6, 20.5, 0.38, 0.9, 0.8, 0.05, mat=HI, segments=8, rings=4)

    # Socket: a round pipe arching over a dark opening cut about 4 px into the arm (columns 26-38,
    # rows 12-27), its darkest part deeper still.
    plate(bm, [(26, 14), (30, 13.5), (34, 14.5), (37, 19), (35.5, 22.5), (33, 26), (29, 24), (26.5, 22)],
          -0.2, -0.04, mat=HOLLOW)
    plate(bm, [(28.5, 18), (31.5, 17), (34, 20), (33, 23), (30, 22)], -0.2, -0.1, mat=UNDER)
    sweep(bm, [(25.6, 15.0, 0.36, 1.5, 0.13), (27.4, 13.4, 0.38, 1.7, 0.15), (30.5, 13.0, 0.4, 1.9, 0.16),
               (33.6, 14.0, 0.4, 1.9, 0.16), (35.4, 16.0, 0.38, 1.8, 0.15), (37.0, 18.4, 0.34, 1.6, 0.14),
               (38.6, 20.0, 0.3, 1.2, 0.11)], sides=10, mat=RIM)
    sweep(bm, [(28.0, 21.0, 0.08, 0.0, 0.0), (28.8, 21.8, 0.12, 1.4, 0.12), (30.3, 24.0, 0.14, 1.7, 0.14),
               (32.6, 25.4, 0.14, 1.7, 0.14), (34.6, 26.6, 0.12, 1.4, 0.12), (35.6, 27.3, 0.1, 0.0, 0.0)],
          sides=8, mat=LMID)

    # Forearm drum hanging under the upper arm (columns 15-22, rows 29-39): a round capsule, as
    # tall as it is wide.
    sweep(bm, [(19.0, 29.2, 0.1, 0.0, 0.0), (19.0, 29.6, 0.1, 2.6, 0.22), (19.0, 30.6, 0.1, 3.6, 0.3),
               (19.0, 36.8, 0.1, 3.6, 0.3), (18.8, 38.2, 0.1, 2.8, 0.23), (18.6, 39.2, 0.1, 0.0, 0.0)],
          sides=14, mat=MID)

    # Looped claw (columns 5-15, rows 31-47): round pipes (a dark outer finger, an arch over the
    # top and a bright inner finger) closing round a dark gap cut in between them, meeting over
    # the gem.
    plate(bm, [(6, 38), (13.5, 38.5), (13.5, 40.5), (11.5, 44.5), (9.5, 47), (5, 47), (5, 44)],
          -0.17, -0.06, mat=BLACK)  # the dark gap between the fingers
    plate(bm, [(8.5, 34.5), (12.5, 34.5), (12.5, 39), (8.5, 39)], -0.17, -0.08, mat=UNDER)
    sweep(bm, [(7.6, 45.5, 0.15, 2.3, 0.19), (7.4, 41.0, 0.17, 2.4, 0.21), (7.6, 37.0, 0.18, 2.2, 0.2)],
          sides=12, mat=DARK)
    sweep(bm, [(7.0, 38.0, 0.18, 0.0, 0.0), (7.0, 37.0, 0.18, 1.8, 0.16), (7.4, 35.0, 0.19, 2.2, 0.19),
               (8.6, 33.3, 0.2, 2.4, 0.2), (10.6, 32.8, 0.2, 2.4, 0.2), (12.4, 33.6, 0.2, 1.9, 0.17),
               (13.2, 34.8, 0.2, 0.0, 0.0)], sides=12, mat=SHADE)
    sweep(bm, [(12.4, 32.4, 0.22, 0.0, 0.0), (12.8, 33.4, 0.22, 1.5, 0.13), (13.4, 37.0, 0.22, 1.7, 0.15),
               (13.4, 39.6, 0.21, 1.7, 0.15), (12.4, 42.0, 0.19, 1.7, 0.15), (11.0, 44.4, 0.17, 1.6, 0.14),
               (9.6, 46.6, 0.15, 0.0, 0.0)], sides=10, mat=RIM)
    # The claw's dark rim: a low black flange under the whole claw and the forearm's lower end,
    # traced from the right arm's sprite outline (rows 30-51; R() takes right-arm pixel edges), so
    # the sprite's black edge pixels round the claw are covered.
    R = lambda pts: [(49 - c, r) for c, r in pts]  # noqa: E731  right-arm edge column -> left
    plate(bm, R([(34, 31), (36, 30), (42, 30), (42, 31), (43, 31), (43, 32), (44, 32), (44, 44), (45, 44),
                 (45, 46), (46, 46), (46, 50), (45, 50), (45, 51), (44, 51), (44, 52), (39.2, 52),
                 (37.9, 50.8), (32.5, 40), (29, 40), (29, 39), (28, 38.2)]),
          -0.2, -0.1, mat=BLACK)
    # Collar over the gem (rows 44-47) and the gem: the sprite's blue is a flat diagonal facet across
    # the claw's end (right-arm columns 40-44, rows 47-50), so it is a low bevelled plate set in the
    # end of the claw with its highlight at the upper left, not a ball.
    ellipsoid(bm, 7.0, 45.6, 0.16, 2.6, 1.5, 0.18, mat=DARK, segments=12, rings=6)
    ellipsoid(bm, 8.6, 46.2, 0.3, 1.0, 0.7, 0.05, mat=HI, segments=8, rings=4)
    rplate(bm, R([(42, 47), (45, 47), (45, 49), (44, 50), (42, 51), (40, 51), (40, 49), (41, 48)]),
           -0.2, 0.17, mat=GEM, r=1.0, steps=2, tilt=(0.012, -0.012, 7, 47))
    ellipsoid(bm, 49 - 41.9, 48.4, 0.17 + 0.01, 1.0, 0.6, 0.025, mat=GEMHI, segments=8, rings=4)

    # Stand the arm on the ground: its lowest faces (the plates' and drums' undersides) at z = 0,
    # so nothing hangs below the base plane and every part keeps its height above it.
    LIFT = 0.2
    for v in bm.verts:
        v.co.z += LIFT

    # Mirror into the right arm: left-arm pixel column c becomes column 48 - c.
    for v in bm.verts:
        v.co.x = -v.co.x + PX
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return to_object(name, bm, mats, coll)


def run(script_file, name, pieces):
    """Build the arm, split it into its pieces, export each, and render previews if asked
    (lib_b028.run_assembly with this script's own arm)."""
    root = common.repo_root(script_file)
    sprite = lib_b028.merged_sprite(root, pieces)
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
        ref = lib_b028.composite_png(root, corners, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)


if __name__ == "__main__":
    run(__file__, "assembly-newsh9-45", PIECES)
