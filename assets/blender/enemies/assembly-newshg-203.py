"""Jungle rocket launcher (newshg.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.2, 2.21 and 2.24). Four 2x2 enemies make one 48x56 px emplacement
(sprite.json `assemblyLayout`): the bottom two pieces are a patch of jungle floor with the mount
in its left half (a box, a post with a glowing red slit, a curved guard and an arm), and a big
grey launcher box rises from the arm diagonally up to the right, across the two top pieces, to a
chamfered red-tipped muzzle. The launcher has a dark panel along its top with a red slit, a red
light on its upper side and a bright collar at its breech.

Frames: newshg-165, newshg-203 and newshg-205 only change the colour of their glowing lights, so
one model each covers their frames. newshg-167 fires: its second and third frames add a flame
out of the muzzle, so it has three models (newshg-167, newshg-167-f2 with the short flame and
newshg-167-f3 with the long one), one per frame.

The whole emplacement is built once in assembly coordinates and cut into the four pieces with
common.split_assembly. It sits on the ground (base at z = 0).

Run: blender --background --python assets/blender/enemies/assembly-newshg-203.py [-- --preview out.png]
(the preview is the whole emplacement; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b124 as lib  # noqa: E402

NAME = "assembly-newshg-203"
ROOT = common.repo_root(__file__)
PIECES = ["newshg-165", "newshg-167", "newshg-203", "newshg-205"]
# Assembly pixel (0, 0) is the top-left corner of newshg-165; the assembly is 48 x 56 px and its
# centre is the Blender origin (screen cx 92, cy -4 in the layout's coordinates).
CX0, CY0 = 92, -4
CORNER = {"newshg-165": (0, 0), "newshg-167": (24, 0), "newshg-203": (0, 28), "newshg-205": (24, 28)}
FR = lib.Frame(48, 56)
PX = lib.PX
R2 = math.sqrt(2)

# The launcher lies on the diagonal: s = col - row runs along it (up and right), t = col + row
# across it (pixel edges). Its axis is t = 51 and it runs from s = -13 (breech) to 22 (muzzle).
AXIS_T = 51.0
S_BREECH, S_SEAM, S_MUZZLE = -13.0, 15.0, 22.5
HALF_W = 8.0 / R2  # half width in px (t from 43 to 59)
HALF_H = 0.17  # half height in units


def st(s, t):
    """Launcher coordinates (s, t) to sprite pixel edges (col, row)."""
    return (s + t) / 2, (t - s) / 2


def axis_z(s):
    """Height of the launcher's axis at s: it rises toward the muzzle."""
    return 0.34 + (s - S_BREECH) * (0.16 / (S_MUZZLE - S_BREECH))


def at(s, t, z):
    return (*FR.xy(*st(s, t)), z)


def top_z(s):
    return axis_z(s) + HALF_H


def plate_st(bm, s0, s1, t0, t1, dz, thick, mat, z_of=top_z):
    """A thin plate lying on the launcher's sloping top, over s0..s1 and t0..t1."""
    start = len(bm.faces)
    corners = [(s0, t0), (s1, t0), (s1, t1), (s0, t1)]
    top = [bm.verts.new(at(s, t, z_of(s) + dz + thick)) for s, t in corners]
    bot = [bm.verts.new(at(s, t, z_of(s) + dz)) for s, t in corners]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    lib.set_faces(bm, start, mat, False)


GRASS_HEIGHT = {32: 0.0, 33: 0.01, 34: 0.02, 35: 0.03, 192: 0.05, 193: 0.065, 194: 0.08, 195: 0.095,
                196: 0.11, 197: 0.125, 198: 0.14, 200: 0.15}


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nshg203"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.35, roughness=0.4),  # 0 launcher grey
        pal(5, metallic=0.35, roughness=0.5),  # 1 dark panels
        pal(9, metallic=0.6, roughness=0.3),  # 2 light rails
        pal(11, metallic=0.65, roughness=0.25),  # 3 bright collar
        pal(3, metallic=0.3, roughness=0.6),  # 4 dark seams and joints
        pal(118, emission_strength=3.0),  # 5 red lights
        pal(116, emission_strength=3.0),  # 6 red slit on the post
        pal(122, emission_strength=4.0),  # 7 orange hot spot
        pal(8, metallic=0.35, roughness=0.4),  # 8 mount grey
        pal(6, metallic=0.35, roughness=0.45),  # 9 mid-dark grey
        pal(33, metallic=0.0, roughness=1.0),  # 10 deep jungle shadow
        pal(35, metallic=0.0, roughness=1.0),  # 11 dark leaves
        pal(193, metallic=0.0, roughness=1.0),  # 12 leaves
        pal(196, metallic=0.0, roughness=1.0),  # 13 lit leaves
        pal(117, emission_strength=3.0),  # 14 red muzzle tip
    ]
    (GREY, PANEL, RAIL, COLLAR, SEAM, RED, SLIT, HOT, MOUNT, MIDGREY,
     SHADOW, DARKLEAF, LEAF, LITLEAF, TIP) = range(15)
    bm = bmesh.new()

    # ---- jungle floor (the bottom two pieces, rows 28-55) ----
    def slot_of(i):
        if i in (32, 33):
            return SHADOW
        if i in (34, 35):
            return DARKLEAF
        if i in (192, 193, 194):
            return LEAF
        if i >= 192:
            return LITLEAF
        return SHADOW  # under the launcher and mount

    def height_of(i):
        return GRASS_HEIGHT.get(i, 0.0)

    lib.ground(bm, FR, grid, 2, 0, 28, 48, 28, slot_of, height_of, base=0.02, mat_side=SHADOW)

    # ---- the launcher ----
    ss = [S_BREECH, S_BREECH + 0.6, -11.0, -6.0, 0.0, 6.0, 12.0, S_SEAM]
    lib.tube(bm, [at(s, AXIS_T, axis_z(s)) for s in ss],
             [HALF_W * 0.85 * PX, HALF_W * 0.97 * PX] + [HALF_W * PX] * (len(ss) - 2),
             sides=16, mat=GREY, flat=HALF_H / (HALF_W * PX), power=0.45)
    # Muzzle cap: narrower and chamfered on its upper-left side (s 15-22), with the red tip.
    cap = [(S_SEAM - 0.2, 51.2, 1.0), (S_SEAM + 1.0, 51.4, 0.9), (19.5, 51.8, 0.8), (21.5, 52.2, 0.62),
           (S_MUZZLE, 52.4, 0.45)]
    lib.tube(bm, [at(s, t, axis_z(s)) for s, t, _ in cap], [HALF_W * k * PX for _, _, k in cap],
             sides=16, mat=MIDGREY, flat=HALF_H * 0.95 / (HALF_W * PX), power=0.5)
    # Seam between the body and the cap.
    lib.tube(bm, [at(S_SEAM - 0.5, AXIS_T, axis_z(S_SEAM - 0.5)), at(S_SEAM + 0.3, AXIS_T, axis_z(S_SEAM + 0.3))],
             [HALF_W * 1.02 * PX] * 2, sides=16, mat=SEAM, flat=HALF_H * 1.02 / (HALF_W * 1.02 * PX), power=0.45)
    # Red tip lights on the cap's end (rows 14-16, columns 33-36).
    plate_st(bm, 18.4, 21.6, 47.5, 53.5, -0.035, 0.05, TIP,
             z_of=lambda s: axis_z(s) + HALF_H * 0.95 * (1.0 if s < 20 else 0.85))

    # Dark panel along the top, right of the axis (t 48-57), with a red slit across it.
    plate_st(bm, -9.0, 13.0, 48.5, 56.5, -0.004, 0.012, PANEL)
    plate_st(bm, 0.6, 2.6, 49.5, 54.0, 0.0, 0.02, RED)
    # Light rail along the upper-left edge and a mid rail along the lower-right edge.
    lib.tube(bm, [at(s, 44.6, top_z(s) - 0.01) for s in (-10.5, 0.0, 14.0)], [0.9 * PX] * 3, sides=6, mat=RAIL,
             flat=0.7)
    lib.tube(bm, [at(s, 57.6, top_z(s) - 0.015) for s in (-10.0, 0.0, 14.0)], [0.8 * PX] * 3, sides=6,
             mat=MOUNT, flat=0.7)
    # Red light on the upper-left side (row 23, columns 19-21).
    plate_st(bm, -4.6, -1.4, 42.2, 44.4, -0.12, 0.08, RED)

    # Bright collar round the breech (rows 28-30, columns 14-19).
    lib.tube(bm, [at(s, AXIS_T, axis_z(s)) for s in (-12.4, -11.4, -10.2)],
             [HALF_W * 1.06 * PX, HALF_W * 1.1 * PX, HALF_W * 1.06 * PX], sides=16, mat=COLLAR,
             flat=(HALF_H * 1.08) / (HALF_W * 1.1 * PX), power=0.5)
    # Dark joint under the breech where the arm meets it (row 31).
    lib.ellipsoid(bm, (*FR.xy(17.0, 32.0), 0.3), (3.2 * PX, 2.0 * PX, 0.12), mat=SEAM, segments=12, rings=6)

    # ---- the mount (bottom-left piece) ----
    # Arm from under the breech down to the post (columns 7-17, rows 31-41).
    lib.tube(bm, [(*FR.xy(18.0, 31.5), 0.3), (*FR.xy(14.5, 34.5), 0.29), (*FR.xy(11.0, 37.5), 0.27),
                  (*FR.xy(9.6, 40.5), 0.25)], [3.6 * PX, 3.8 * PX, 3.8 * PX, 3.4 * PX], sides=10, mat=MOUNT,
             flat=0.8)
    # Its light ridge (columns 9-11).
    lib.tube(bm, [(*FR.xy(13.0, 34.8), 0.37), (*FR.xy(10.6, 37.2), 0.355), (*FR.xy(9.8, 40.0), 0.33)],
             [0.0, 0.9 * PX, 0.0], sides=6, mat=COLLAR, flat=0.6)

    # The post with the glowing slit (columns 6-10, rows 41-51).
    lib.slab(bm, FR, [(5.8, 40.8), (10.8, 40.8), (10.8, 51.2), (5.8, 51.2)], 0.0, 0.3, mat=MOUNT, bevel=0.6)
    lib.slab(bm, FR, [(6.9, 41.8), (9.1, 41.8), (9.1, 50.8), (6.9, 50.8)], 0.27, 0.31, mat=SLIT)
    lib.slab(bm, FR, [(7.0, 43.6), (8.0, 43.6), (8.0, 45.0), (7.0, 45.0)], 0.3, 0.315, mat=HOT)

    # Curved guard on the far left (columns 1-8, rows 35-45) and a shorter prong inside it.
    lib.tube(bm, [(*FR.xy(8.6, 35.6), 0.24), (*FR.xy(5.8, 36.8), 0.22), (*FR.xy(3.4, 39.0), 0.18),
                  (*FR.xy(2.6, 42.0), 0.13), (*FR.xy(2.5, 45.0), 0.06)],
             [1.4 * PX, 1.6 * PX, 1.7 * PX, 1.6 * PX, 1.3 * PX], sides=8, mat=MOUNT, flat=1.0)
    lib.tube(bm, [(*FR.xy(5.2, 40.5), 0.18), (*FR.xy(4.9, 42.5), 0.13), (*FR.xy(4.8, 44.6), 0.06)],
             [1.0 * PX, 1.0 * PX, 0.8 * PX], sides=6, mat=MIDGREY)

    # The box (columns 12-22, rows 40-51): rounded top edge toward the arm, ribs down its face.
    lib.slab(bm, FR, [(13.8, 40.6), (20.6, 40.6), (22.5, 42.6), (22.5, 46.5), (19.0, 51.3), (12.2, 51.3),
                      (12.2, 42.6)], 0.0, 0.24, mat=MOUNT, bevel=1.0)
    lib.tube(bm, [(*FR.xy(13.0, 41.8), 0.22), (*FR.xy(21.8, 41.8), 0.22)], [1.3 * PX, 1.3 * PX], sides=8,
             mat=MOUNT, flat=0.8)
    for c in (13.4, 15.4):
        lib.tube(bm, [(*FR.xy(c, 43.5), 0.22), (*FR.xy(c, 50.5), 0.2)], [0.8 * PX, 0.8 * PX], sides=6,
                 mat=RAIL, flat=0.8)

    return lib.to_object(NAME, bm, mats, coll)


def flame(sprite, length, name):
    """The muzzle flame for newshg-167's firing frames: nested emissive cones along the launcher's
    axis from the muzzle, `length` px (in s) long."""
    coll = common.reset_collection(name)
    tag = "nshg203"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [pal(118, emission_strength=3.0), pal(122, emission_strength=4.0), pal(126, emission_strength=5.0)]
    bm = bmesh.new()
    s0 = S_MUZZLE - 1.0
    t = 49.6
    z0 = axis_z(S_MUZZLE) + 0.02
    rise = 0.004  # the flame keeps the launcher's slope, gently

    def pts(fracs):
        return [at(s0 + f * length, t - 0.6 * f, z0 + rise * f * length) for f in fracs]

    # Red outside, a yellow layer and a white-hot core, each taller than the one round it so it
    # shows through on top, as the sprite's bright middle does.
    for mat, (w, frac, flat) in enumerate(((3.8, 1.0, 0.3), (3.0, 0.8, 0.6), (1.8, 0.55, 1.1))):
        fr = [0.0, 0.08, 0.3 * frac, 0.6 * frac, frac]
        rad = [w * 0.55 * PX, w * PX, w * 0.95 * PX, w * 0.6 * PX, 0.0]
        lib.tube(bm, pts(fr), rad, sides=10, mat=mat, flat=flat)
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    # The jungle floor's palette indices, from each piece's first frame, in assembly pixels.
    grid = [[-1] * 48 for _ in range(56)]
    for name, (c0, r0) in CORNER.items():
        for r, row in enumerate(common.load_sprite(ROOT, name)["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r0 + r][c0 + c] = v
    obj = build(sprite, grid)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for piece in pieces.values():
        lib.drop_slivers(piece)

    exported = {}
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        sprites = data["sprites"]
        if name == "newshg-167":
            # One model per frame: no flame, short flame, long flame.
            frames = sprites[0]["frames"]
            one = lambda k: [dict(sprites[0], frames=[frames[k]])]  # noqa: E731
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", one(0))
            exported[name] = [pieces[name]]
            for k, length in ((1, 12.0), (2, 24.0)):
                fl = flame(sprite, length, f"{name}-flame{k + 1}")
                part = common.split_assembly(fl, [(name, *next((x, y) for n, x, y in layout if n == name))])[name]
                lib.drop_slivers(part)
                part.name = f"{name}-f{k + 1}-flame"
                common.export_sprite_model(ROOT, [pieces[name], part], f"enemies/{name}-f{k + 1}", one(k))
                exported[f"{name}-f{k + 1}"] = [pieces[name], part]
        else:
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites)
            exported[name] = [pieces[name]]

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        # The whole emplacement in a 48x56 (size 4) block.
        ref = lib.composite_png(ROOT, [(n, c, r) for n, (c, r) in CORNER.items()], 48, 56, tmp / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for key, objs in exported.items():
            base = key.split("-f")[0] if "-f" in key else key
            data = common.load_sprite(ROOT, base)
            k = int(key.rsplit("-f", 1)[1]) - 1 if "-f" in key else 0
            img = ROOT / "reference" / "models" / base / data["frames"][k]["image"]
            common.render_preview(objs, str(out.parent / f"{key}.png"), img, size=2)


if __name__ == "__main__":
    main()
