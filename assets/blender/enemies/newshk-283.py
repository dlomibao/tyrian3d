"""Grey twin-pronged heater (newshk.shp frame 283): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A grey housing with a sloped roof at the back (top of the
sprite), a dark sunken window framed in light grey and two ribbed strips with rivets down its
sides, a dark lip under it, and two thick prongs hanging down the screen. Each prong's inner
side is a dark slot with red-hot elements glowing in it (a bright spot low on the left one), and
each ends in a pale tip. One frame.

Run: blender --background --python assets/blender/enemies/newshk-283.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b010 as lib  # noqa: E402
from lib_b010 import ex, ey, gx, gy  # noqa: E402

NAME = "newshk-283"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel


def loft(bm, rings, mat, smooth=False, flat=(), flat_segs=None):
    """Faces between consecutive rings of (x, y, z) points (all the same length), capped at both
    ends. Faces from profile edge i are flat-shaded when i is in `flat` (in the first `flat_segs`
    segments only, when given)."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for k, (a, b) in enumerate(zip(vs, vs[1:])):
        sharp = flat if flat_segs is None or k < flat_segs else ()
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index, f.smooth = mat, smooth and i not in sharp
            if smooth and i in sharp:  # keep the smooth faces beside it from shading into it
                for e in f.edges:
                    e.smooth = False
    for cap in (list(reversed(vs[0])), vs[-1]):
        f = bm.faces.new(cap)
        f.material_index, f.smooth = mat, False


def ring(y, profile):
    return [(x, y, z) for x, z in profile]


def pod_profile(groove, n=16):
    """A unit circle (u, v) with a groove 1/3 deep and 1/3 wide cut in its top, centred at u =
    groove. Returns the points and the indices of the groove's edges (flat-shaded)."""
    ta, tb = math.acos(groove + 1 / 6), math.acos(groove - 1 / 6)
    floor = min(math.sin(ta), math.sin(tb)) - 1 / 3
    pts = [(2 * math.pi * k / n, (math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)))
           for k in range(n)]
    pts = [p for p in pts if not (ta - 0.05 < p[0] < tb + 0.05)]
    pts += [(ta, (math.cos(ta), math.sin(ta))), (ta + 1e-4, (math.cos(ta), floor)),
            (tb - 1e-4, (math.cos(tb), floor)), (tb, (math.cos(tb), math.sin(tb)))]
    pts.sort()
    i = [k for k, (t, _) in enumerate(pts) if t == ta][0]
    return [uv for _, uv in pts], (i, i + 1, i + 2), floor


def ellipsoid(bm, cx, cy, cz, rx, ry, rz, mat, sides=12, rings=6):
    secs = [(cy + ry, 0.0, 0.0, cz)]
    for k in range(1, rings):
        t = math.pi * k / rings
        secs.append((cy + ry * math.cos(t), rx * math.sin(t), rz * math.sin(t), cz))
    secs.append((cy - ry, 0.0, 0.0, cz))
    lib.rod_y(bm, cx, secs, sides=sides, mat=mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.5, roughness=0.4),  # 0 grey housing and pods
        pal(8, metallic=0.5, roughness=0.45),  # 1 darker grey rounded sides
        pal(11, metallic=0.25, roughness=0.35),  # 2 light grey window frame and front edge
        pal(5, metallic=0.4, roughness=0.5),  # 3 dark grey lip, grooves, lower pane
        pal(3, metallic=0.3, roughness=0.6),  # 4 dark upper pane, top of the slots
        pal(13, metallic=0.3, roughness=0.25),  # 5 pale caps and rivets
        pal(117, emission_strength=6.0),  # 6 red-hot elements
        pal(123, emission_strength=6.0),  # 7 hot spot (left)
        pal(10, metallic=0.25, roughness=0.35),  # 8 light grey rails
        pal(113, emission_strength=3.0),  # 9 dim glow on the slot floor
        pal(1, metallic=0.2, roughness=0.8),  # 10 black slot floor
        pal(6, metallic=0.4, roughness=0.5),  # 11 cross groove on the rails
        pal(121, emission_strength=6.0),  # 12 hot spot (right)
    ]
    GREY, SIDE, LIGHT, LIP, DARK, PALE, HOT, SPOT, STRIP, EMBER, BLACK, NOTCH, SPOT2 = range(13)
    bm = bmesh.new()
    H = 9 * P  # housing top: about 3 px above the pods, its row 13 shadow band an overhang

    # Housing (rows 4-13): a block 9 px tall over columns 2-22 with a 2 px deep window cut in it
    # (columns 8-16, rows 7-10), and rounded darker sides (columns 0-2 and 22-24).
    full = [(ex(2), 0), (ex(22), 0), (ex(22), H), (ex(2), H)]
    notch = [(ex(2), 0), (ex(22), 0), (ex(22), H), (ex(16), H), (ex(16), H - 2 * P),
             (ex(8), H - 2 * P), (ex(8), H), (ex(2), H)]
    for r0, r1, prof in ((4.5, 7, full), (7, 10, notch), (10, 13, full)):
        loft(bm, [ring(ey(r0), prof), ring(ey(r1), prof)], GREY)
    for side in (-1, 1):
        o = ex(12)
        def mx(c):
            return o + side * (ex(c) - o)
        prof = [(mx(2), 0), (mx(2), H), (mx(1), H - 0.6 * P), (mx(0), H - 2.2 * P), (mx(0), 0)]
        if side < 0:
            prof = prof[::-1]
        loft(bm, [ring(ey(4.5), prof), ring(ey(13), prof)], SIDE)
    # Lit front edge (row 4) chamfered down towards the nose.
    lib.prism(bm, [(ex(0.6), ey(3.4), H - 2 * P), (ex(23.4), ey(3.4), H - 2 * P), (ex(23.6), ey(4.6), H),
                   (ex(0.4), ey(4.6), H)], 0.0, mat=LIGHT)
    # Row 13: the dark underside of the overhang, falling from the housing top to the pods.
    def lip(top):
        return [(ex(0), 0), (ex(24), 0), (ex(24), top - 2.2 * P), (ex(23), top - 0.6 * P), (ex(22), top),
                (ex(2), top), (ex(1), top - 0.6 * P), (ex(0), top - 2.2 * P)]
    loft(bm, [ring(ey(13), lip(H)), ring(ey(14), lip(5.5 * P))], LIP)

    # Window: dark pane at the bottom of the cut, light frame (columns 7 and 16, row 10) proud.
    lib.box(bm, 8, 7, 16, 8, H - 2.05 * P, H - 1.95 * P, mat=DARK)
    lib.box(bm, 8, 8, 16, 10, H - 2.05 * P, H - 1.95 * P, mat=LIP)
    lib.box(bm, 7, 7, 8, 11, H - 0.1 * P, H + 0.5 * P, mat=LIGHT)
    lib.box(bm, 16, 7, 17, 11, H - 0.1 * P, H + 0.5 * P, mat=LIGHT)
    lib.box(bm, 8, 10, 16, 11, H - 0.1 * P, H + 0.5 * P, mat=LIGHT)

    # Raised rails (columns 2 and 4, 19 and 21), broken by a dark cross groove at row 8, with
    # rivets at rows 4 and 9.
    for c in (2, 4, 19, 21):
        lib.box(bm, c + 0.05, 4.5, c + 0.95, 8, H - 0.1 * P, H + 0.6 * P, mat=STRIP)
        lib.box(bm, c + 0.05, 9, c + 0.95, 13, H - 0.1 * P, H + 0.6 * P, mat=STRIP)
    for c0, c1 in ((2, 5), (19, 22)):
        lib.box(bm, c0, 8, c1, 9, H - 0.1 * P, H + 0.05 * P, mat=NOTCH)
    for c in (4, 19):
        for y in (ey(4.9), gy(9)):
            lib.stud(bm, gx(c), y, H + 0.6 * P, 0.6 * P, 0.6 * P, mat=PALE)

    # Nose cowl (rows 0-3): tapering from 14 px wide at the housing to 4 px at the front and
    # sloping from the housing top down to 4 px, with bevelled top edges.
    def cowl(hw, top):
        x0 = ex(12)
        return [(x0 - hw, 0), (x0 + hw, 0), (x0 + hw, top - 1.5 * P), (x0 + hw - P, top),
                (x0 - hw + P, top), (x0 - hw, top - 1.5 * P)]
    loft(bm, [ring(ey(4.6), cowl(7 * P, H - 0.2 * P)), ring(ey(3), cowl(6.3 * P, 7.4 * P)),
              ring(ey(2), cowl(4.7 * P, 6.2 * P)), ring(ey(1), cowl(3.2 * P, 5 * P)),
              ring(ey(-0.05), cowl(2.2 * P, 4 * P))], GREY)

    # Pods (rows 14-27): round, 6 px across and 6 px tall, a groove cut down column 3 / 19,
    # rounded off at the tail.
    R = 3 * P
    # The right pod also covers column 23 (the sprite's outline there; the left one is cut off).
    for cx, rx, groove_c in ((ex(3), R, 3), (ex(20.5), 3.5 * P, 19)):
        g = (ex(groove_c) + P / 2 - cx) / rx
        prof, flat, floor = pod_profile(g, n=14)
        rings = []
        lo, hi = flat[0], flat[2] + 1  # the groove's top corners; between them, its floor
        for r, s, fill in ((11, 1.0, 0), (14, 1.0, 0), (23.5, 1.0, 0), (25.5, 0.97, 0.6), (26.8, 0.86, 0.9),
                           (27.6, 0.62, 0.9), (28.0, 0.25, 0.9)):
            zc = R * s
            pts = list(prof)
            for k in (lo + 1, hi - 1):  # the groove closes up round the tail
                pts[k] = (pts[k][0], pts[k][1] + fill * (math.sqrt(1 - pts[k][0] ** 2) - pts[k][1]))
            rings.append([(cx + u * rx * s, ey(r), zc + v * R * s) for u, v in pts])
        loft(bm, rings, GREY, smooth=True, flat=flat, flat_segs=2)
        zf = R + floor * R
        lib.box(bm, groove_c + 0.02, 14, groove_c + 0.98, 23.5, zf - 0.2 * P, zf + 0.05 * P, mat=LIP)

    # Pale rounded caps at the pods' inner tails (columns 4-7 and 15-18, rows 25-27).
    for cx in (ex(6.2), ex(16.8)):
        ellipsoid(bm, cx, ey(26.2), 2.3 * P, 2.4 * P, 2.0 * P, 2.2 * P, PALE, sides=12)

    # Slots between the pods: a black floor 1.5 px up, dark under the overhang, with round red-hot
    # elements on it (columns 7 and 9, 13 and 15) and a dim glow between each pair.
    bed = 1.5 * P
    for c0, c1, r1 in ((6, 11, 25), (13, 17, 25.5)):
        lib.box(bm, c0, 13.5, c1, r1, 0.0, bed, mat=BLACK)
    lib.box(bm, 6, 13.6, 9, 16, bed, bed + 0.1 * P, mat=DARK)
    lib.box(bm, 14, 13.6, 17, 16, bed, bed + 0.1 * P, mat=DARK)
    lib.box(bm, 8.1, 17, 8.9, 20, bed, bed + 0.15 * P, mat=EMBER)
    lib.box(bm, 14.1, 18, 14.9, 23, bed, bed + 0.15 * P, mat=EMBER)
    rz = 0.6 * P
    for c, r0, r1 in ((7, 16, 25), (9, 14, 24), (13, 14, 24), (15, 16, 25)):
        z = bed + rz
        lib.rod_y(bm, gx(c), [(ey(r0), 0.25 * P, 0.25 * P, z), (ey(r0) - 0.3 * P, 0.6 * P, rz, z),
                              (ey(r1) + 0.3 * P, 0.6 * P, rz, z), (ey(r1), 0.25 * P, 0.25 * P, z)],
                  sides=8, mat=HOT)
    lib.stud(bm, gx(9), gy(21), bed + 1.6 * rz, 0.65 * P, 0.5 * P, mat=SPOT)
    lib.stud(bm, gx(13), gy(21), bed + 1.6 * rz, 0.6 * P, 0.45 * P, mat=SPOT2)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
