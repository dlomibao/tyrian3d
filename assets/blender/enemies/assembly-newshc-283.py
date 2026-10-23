"""Twin-pillar machine (newshc.shp, assembly of 12 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.19) and 3 (3.23). Twelve 2x2 ground enemies make one 96 x 112 px
machine standing on a blue tiled floor (sprite.json `assemblyLayout`): two long grey pillars
(newshc-115, -17 and -55 from top to bottom, with the pop-up ball turret newshc-77 at their head)
and between them two blue-and-grey crane turrets (newshc-245 above newshc-283): a dark ball on
the floor with blue glass, a blue rod rising from it into a grey yoke that holds a hammer-shaped
grey head, and a curved blue fin standing on a post beside it.

The pillars lie along the screen as segmented machinery: a cup with red insides round a central
shaft, a red collar, ribbed drums with red lamps on their front ends, dark necks between them,
and a last drum with a red hatch where it meets the floor.

Each piece appears twice (the two pillars and the two cranes are the same sprites, not mirror
images), so the left pillar and the left crane are built once in assembly coordinates and cut
into newshc-115, -17, -55, -245 and -283 with common.split_assembly. newshc-77 (animated) has
its own script; its frame 87 is added here only for the preview.

Run: blender --background --python assets/blender/enemies/assembly-newshc-283.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b110 as lib  # noqa: E402

NAME = "assembly-newshc-283"
ROOT = common.repo_root(__file__)
PIECES = ["newshc-115", "newshc-17", "newshc-55", "newshc-245", "newshc-283"]
ALL = PIECES + ["newshc-77"]
# Assembly pixel (0, 0) is screen (116, -32), the top-left of the left newshc-77; the machine is
# 96 x 112 px and its centre (screen 164, 24) is the Blender origin.
SX0, SY0 = 164, 24
FR = lib.Frame(96, 112)
PX = lib.PX
PI = math.pi

# Where each piece's 24x28 block starts (assembly col, row) for the left pillar and left crane.
P115, P17, P55 = (0, 28), (0, 56), (0, 84)
P245, P283 = (24, 28), (24, 56)
HEADS = [(0, 0), (72, 0)]

SLOTS = ["grey", "light", "mid", "dark", "red", "red_dark", "lamp", "floor", "tile", "tile_hi",
         "glass", "blue", "blue_dark", "blue_hi", "steel"] + ["h_" + s for s in lib.HEAD_SLOTS]
S = {n: i for i, n in enumerate(SLOTS)}


def materials(sprite):
    tag = "nshc283"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.6, roughness=0.35),  # grey drums
        pal(10, metallic=0.6, roughness=0.3),  # light grey lips and plates
        pal(6, metallic=0.55, roughness=0.4),  # mid grey shafts
        pal(3, metallic=0.3, roughness=0.6),  # dark necks and gaps
        pal(71, metallic=0.3, roughness=0.5),  # red collars and cup insides
        pal(67, metallic=0.2, roughness=0.6),  # dark red hatch
        pal(73, emission_strength=2.0),  # red lamps
        pal(98, metallic=0.1, roughness=0.8),  # floor
        pal(101, metallic=0.15, roughness=0.7),  # floor tiles
        pal(102, metallic=0.15, roughness=0.7),  # light floor tiles
        pal(133, metallic=0.5, roughness=0.15),  # blue glass
        pal(57, metallic=0.4, roughness=0.35),  # blue fin and trim
        pal(54, metallic=0.4, roughness=0.4),  # dark blue rod
        pal(158, emission_strength=1.5),  # bright blue crease
        pal(4, metallic=0.5, roughness=0.4),  # dark steel ball
    ]
    pal77 = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return mats + lib.head_materials(pal77, lib.HEAD_FRAMES[87]["eye"])


def P(piece, c, r):
    """A piece's own pixel (col, row centre) to Blender (x, y)."""
    return FR.x(piece[0] + c), FR.y(piece[1] + r)


def E(piece, c, r):
    """A piece's own pixel edge (col, row) to Blender (x, y)."""
    return FR.xe(piece[0] + c), FR.ye(piece[1] + r)


# --- the pillar ----------------------------------------------------------------------------------

def pillar(bm):
    """The left pillar, assembly rows 28-97 (newshc-115, -17, -55), lying along Y on the floor."""
    xc = FR.x(11.5)
    ye = FR.ye

    def hh(w):
        return 0.55 * min(1.0, w / 8.0) ** 0.5 if w else 0.0

    def run(sections, mats, sides=16):
        """Sections are (assembly row edge, half width px); mats colours each band."""
        lib.loft_y(bm, xc, [(ye(r), w * PX, hh(w), 0.0) for r, w in sections], sides=sides,
                   arc=(0, PI), mats=[S[m] for m in mats], mat=S[mats[0]])

    # Cup under the turret (newshc-115 rows 0-10): a grey bowl round a central shaft, red inside.
    run([(27.6, 4.0), (28.4, 5.5), (29.6, 7.5), (31.0, 8.2), (35.8, 8.2), (36.8, 7.2), (37.8, 5.2),
         (38.8, 3.4), (39.0, 3.0)], ["light", "light", "grey", "grey", "grey", "grey", "grey", "dark"])
    for c0, c1 in ((6, 9), (14, 18)):  # red showing inside the cup either side of the shaft
        x0, x1 = FR.xe(c0), FR.xe(c1)
        inner = min(abs(x0 - xc), abs(x1 - xc)) / (8.2 * PX)
        top = hh(8.2) * math.sqrt(max(0.0, 1 - inner * inner)) + 0.02
        lib.box(bm, x0, ye(35.0), x1, ye(30.0), 0.2, top, S["red"])
    lib.loft_y(bm, FR.x(11.0), [(ye(28.6), 0.0, 0.0, 0.0), (ye(29.4), 1.6 * PX, 0.6, 0.0),
                                (ye(36.8), 1.6 * PX, 0.6, 0.0), (ye(37.6), 0.0, 0.0, 0.0)],
               sides=8, arc=(0, PI), mat=S["mid"])

    # Neck, red collar round a grey shaft, and the first drum with its lamp (rows 39-54).
    run([(38.8, 3.0), (41.0, 3.0), (41.2, 5.0), (42.0, 7.0), (43.0, 8.0), (45.0, 8.0), (45.0, 8.0),
         (51.0, 8.0), (52.0, 7.2), (53.0, 6.0), (54.0, 4.0), (54.2, 0.0)],
        ["dark", "dark", "red", "red", "red", "grey", "grey", "grey", "grey", "grey", "grey"])
    lib.loft_y(bm, FR.x(11.0), [(ye(40.5), 2.5 * PX, 0.58, 0.0), (ye(45.5), 2.5 * PX, 0.58, 0.0)],
               sides=8, arc=(0, PI), mat=S["mid"])
    lamp(bm, FR.x(11.5), ye(51.7), 0.44)

    # Dark gap, then the long shaft (newshc-115 row 26 to newshc-17 row 8).
    run([(53.8, 5.0), (55.0, 6.0), (55.2, 5.5), (64.8, 5.5), (65.0, 0.0)],
        ["dark", "dark", "mid", "mid"], sides=14)

    # Second drum with its lamp (newshc-17 rows 9-20).
    run([(64.8, 6.0), (65.6, 6.8), (66.6, 7.5), (67.0, 8.0), (73.0, 8.0), (74.0, 7.2), (75.0, 6.5),
         (76.0, 5.0), (77.2, 4.0)], ["grey", "grey", "grey", "grey", "grey", "grey", "grey", "dark"])
    lamp(bm, FR.x(11.5), ye(75.7), 0.42)

    # Last drum down to the floor (newshc-17 row 22 to newshc-55 row 13) with a red hatch.
    run([(77.0, 4.5), (78.2, 5.5), (79.0, 7.0), (80.6, 8.0), (93.0, 8.0), (94.0, 7.5), (95.0, 7.0),
         (96.0, 6.0), (97.0, 5.0), (97.8, 4.0)],
        ["grey", "grey", "grey", "grey", "grey", "grey", "dark", "dark", "dark"])
    hatch = []
    for k in range(7):
        a = PI * (0.62 + 0.3 * k / 6)
        hatch.append((math.cos(a), math.sin(a)))
    for r0, r1 in ((85.5, 91.8),):
        outer = [(xc + 8.25 * PX * cx, hh(8.0) * sy + 0.015) for cx, sy in hatch]
        inner = [(xc + 7.7 * PX * cx, hh(8.0) * sy * 0.93) for cx, sy in hatch]
        before = set(bm.faces)
        verts = []
        for y in (ye(r0), ye(r1)):
            verts.append([bm.verts.new((x, y, z)) for x, z in outer + inner[::-1]])
        n = len(verts[0])
        bm.faces.new(verts[0])
        bm.faces.new(list(reversed(verts[1])))
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((verts[0][i], verts[0][j], verts[1][j], verts[1][i]))
        lib.tag(bm, before, S["red_dark"], False)

    # Ribs (light) along the drums' right flanks, as on the sprite's right-hand rim.
    for r0, r1 in ((45.5, 51.0), (67.0, 73.0), (80.0, 93.0)):
        lib.loft_y(bm, FR.x(18.4), [(ye(r0), 0.0, 0.0, 0.0), (ye(r0 + 0.6), 0.9 * PX, 0.26, 0.0),
                                    (ye(r1 - 0.6), 0.9 * PX, 0.26, 0.0), (ye(r1), 0.0, 0.0, 0.0)],
                   sides=6, arc=(0, PI), mat=S["light"])


def lamp(bm, x, y, z):
    lib.ellipsoid(bm, x, y, z, 2.2 * PX, 1.8 * PX, 0.14, mat=S["lamp"], segments=10, rings=6)


# --- the crane turret ----------------------------------------------------------------------------

def crane(bm, sprites):
    """The left crane: the ball on the floor (newshc-283) and its head and fin (newshc-245)."""
    # Ball on the floor (newshc-283 rows 1-18, cols 4-19): a dark steel dome, grey over its back
    # half, with blue glass either side of the rod and a blue trim round its front foot.
    xc = P(P283, 11.5, 0)[0]
    yc = E(P283, 0, 10.0)[1]
    before = set(bm.faces)
    lib.ellipsoid(bm, xc, yc, 0.0, 8.0 * PX, 9.2 * PX, 0.5, mat=S["steel"], segments=24, rings=18, zmin=0.0,
                  pole_y=True)
    bands = [(3.5, "grey"), (6.5, "glass"), (11.5, "light")]  # rows above which each colour ends
    for f in [f for f in bm.faces if f not in before]:
        y = sum(v.co.y for v in f.verts) / len(f.verts)
        for r, m in bands:
            if y > E(P283, 0, r)[1]:
                f.material_index = S[m]
                break
    path = []
    for k in range(11):
        a = PI * (1.08 + 0.84 * k / 10)
        path.append((xc + 7.8 * PX * math.cos(a), yc + 8.8 * PX * math.sin(a), 0.08, 1.0 * PX, 0.08))
    lib.tube(bm, path, sides=8, mat=S["blue"])
    # Grey block on the ball's top right (rows 1-3, cols 14-18).
    x0, y0 = E(P283, 14, 4.2)
    x1, y1 = E(P283, 19, 0.8)
    lib.box(bm, x0, y0, x1, y1, 0.15, 0.42, S["mid"])

    # Blue rod from the ball up into the yoke (newshc-283 row 8 to newshc-245 row 24).
    xr = P(P245, 11.5, 0)[0]
    lib.tube(bm, [(xr, P(P283, 0, 11.5)[1], 0.46, 1.8 * PX, 0.07), (xr, P(P283, 0, 6.0)[1], 0.53, 2.0 * PX, 0.08),
                  (xr, P(P245, 0, 22.0)[1], 0.55, 2.0 * PX, 0.08)], sides=10, mat=S["blue_dark"])
    lib.tube(bm, [(xr - 1.0 * PX, P(P283, 0, 7.0)[1], 0.52, 0.6 * PX, 0.03),
                  (xr - 1.0 * PX, P(P245, 0, 24.0)[1], 0.6, 0.6 * PX, 0.03)], sides=6, mat=S["glass"])

    # Grey yoke (rows 20-23, cols 10-15) and its two arms up to the head (cols 9-10 and 15).
    x0, y0 = E(P245, 9.6, 24.0)
    x1, y1 = E(P245, 16.0, 19.8)
    lib.box(bm, x0, y0, x1, y1, 0.42, 0.62, S["mid"])
    for (c0, r0), (c1, r1) in (((10.2, 20.5), (9.6, 15.0)), ((15.4, 21.0), (15.2, 16.0))):
        (xa, ya), (xb, yb) = P(P245, c0, r0), P(P245, c1, r1)
        lib.tube(bm, [(xa, ya, 0.56, 0.9 * PX, 0.05), (xb, yb, 0.64, 0.9 * PX, 0.05)], sides=8, mat=S["mid"])

    # The hammer-shaped head (rows 3-14): a body with a blue face, two prongs pointing left.
    def pr(outline, z0, z1, mat):
        lib.prism(bm, [E(P245, c, r) for c, r in outline], z0, z1, S[mat])

    pr([(6, 10), (13, 10), (13, 15), (6, 15)], 0.5, 0.7, "mid")  # body
    pr([(9, 8), (12, 8), (12, 15), (9, 15)], 0.5, 0.72, "glass")  # blue face
    pr([(12, 6), (17, 7), (17, 10), (12, 10.5)], 0.58, 0.7, "dark")  # dark back
    pr([(4, 7), (16, 7), (17, 8), (16, 10), (7, 10), (4, 9)], 0.62, 0.74, "light")  # lower prong
    pr([(2, 4), (14, 4), (16, 6), (16, 7), (1, 7), (1, 5)], 0.72, 0.84, "light")  # upper prong
    pr([(7, 5), (13, 5), (13, 6), (7, 6)], 0.84, 0.855, "glass")  # blue stripe on top
    pr([(1, 6.2), (15.5, 6.2), (16, 7), (1, 7)], 0.7, 0.8, "mid")  # its shaded underside

    # The blue fin on its post (rows 8-27, cols 13-21).
    pr([(18, 8), (21, 8), (22, 9), (22, 13.5), (13, 13.5), (13, 12), (15, 11.5), (15, 10), (18, 9.5)],
       0.4, 0.5, "glass")
    pr([(13, 13.5), (22, 13.5), (22, 23), (20, 23), (19, 21), (18, 19.5), (16, 17.5), (14, 15.5), (13, 14)],
       0.38, 0.48, "blue")
    pr([(19, 9.5), (20, 9.5), (20, 13.6), (19, 13.6)], 0.5, 0.515, "blue_hi")
    pr([(15, 12.8), (20, 12.8), (20, 13.6), (15, 13.6)], 0.5, 0.515, "blue_hi")
    xp = E(P245, 21, 0)[0]
    lib.tube(bm, [(xp, E(P245, 0, 21.0)[1], 0.4, 1.0 * PX, 0.06),
                  (xp, E(P245, 0, 27.9)[1], 0.12, 1.0 * PX, 0.06)], sides=8, mat=S["blue"])


def floor55(bm, sprites):
    lib.floor_tiles(bm, FR, sprites["newshc-55"]["frames"][0]["pixels"], S["floor"],
                    {101: S["tile"], 102: S["tile_hi"]}, col0=P55[0], row0=P55[1])


def floor283(bm, sprites):
    lib.floor_tiles(bm, FR, sprites["newshc-283"]["frames"][0]["pixels"], S["floor"],
                    {101: S["tile"], 102: S["tile_hi"]}, col0=P283[0], row0=P283[1])


def merged_sprite():
    data = common.load_sprite(ROOT, "newshc-283")
    for name in ALL:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build(sprite, sprites):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = bmesh.new()
    pillar(bm)
    crane(bm, sprites)
    floor55(bm, sprites)
    floor283(bm, sprites)
    return lib.to_object(NAME, bm, mats, coll), mats, coll


def whole(mats, coll, sprites):
    """The whole machine for the preview: both pillars and cranes, and the turrets (frame 87)."""
    bm = bmesh.new()
    for part, dx in ((pillar, 0), (pillar, 72), (crane, 0), (crane, 24), (floor55, 0), (floor55, 72),
                     (floor283, 0), (floor283, 24)):
        start = len(bm.verts)
        if part is pillar:
            part(bm)
        else:
            part(bm, sprites)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[start:]:
            v.co.x += dx * PX
    for c0, r0 in HEADS:
        lib.build_head(bm, FR, c0, r0, 87, base=S["h_sphere"])
    return lib.to_object(NAME + "_whole", bm, mats, coll)


def main():
    sprites = {n: common.load_sprite(ROOT, n) for n in ALL}
    sprite = merged_sprite()
    obj, mats, coll = build(sprite, sprites)
    layout = [(e["model"], e["cx"] - SX0, e["cy"] - SY0) for e in sprite["assemblyLayout"]]
    chosen = {}
    for name, cx, cy in layout:  # the left pillar and the left crane
        if name in PIECES and name not in chosen and cx < 0:
            chosen[name] = (name, cx, cy)
    pieces = common.split_assembly(obj, list(chosen.values()))
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites[name]["sprites"])
    out = lib.preview_arg()
    if out:
        import tempfile
        out = Path(out)
        full = whole(mats, coll, sprites)
        place = [(sprites[e["model"]], [f["index"] for f in sprites[e["model"]]["frames"]].index(int(e["frame"].split("|")[2])),
                  e["cx"] - SX0 + 36, e["cy"] - SY0 + 42) for e in sprite["assemblyLayout"]]
        ref = lib.composite_png(ROOT, place, 96, 112, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([full], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"),
                                  lib.sprite_png(ROOT, name, sprites[name]), size=2)
        print("faces:", {n: lib.faces_of([pieces[n]]) for n in PIECES})


if __name__ == "__main__":
    main()
