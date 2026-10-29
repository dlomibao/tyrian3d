"""Rock wall with purple octagon plates, band along its top (newsh2.shp 273, 275, 277): a 3D
version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. A row of 2x2 pieces (sprite.json `assemblyLayout`):
newsh2-273 at the left end, newsh2-275 repeated in the middle and newsh2-277 at the right end.
Each piece is a block of grey and beige boulders with a raised, chamfered purple octagon hatch
(a heavy armour block with a slightly raised centre hub, as the concept draws it), and a purple
band of panels runs along the top behind the hatches. Between each pair of hatches a lighter
purple housing fills the V-shaped gap (the sprite's light 90/91 wedge), with a small ribbed vent
on its front where it drops into the dark crevice. The boulders are round, faceted and matte,
standing about half as tall as they are wide. Heights, low to high: band, housings, boulders,
hatches. The row is built whole (left, two middles, right) in assembly coordinates and cut into
the pieces with common.split_assembly; the middle piece is the same at both of its edges so it
tiles.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-273.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as lib  # noqa: E402
from lib_b048 import PX, box, bevel_plate, common  # noqa: E402

NAME = "assembly-newsh2-273"
TILES = ["newsh2-273", "newsh2-275", "newsh2-275", "newsh2-277"]
KINDS = ["left", "mid", "mid", "right"]
BAND = "top"

# Heights in units (1 sprite px = 1/12).
BED_Z = -0.03         # boulders sit half-buried in the bed at this height
BAND_Z = 0.10         # top of the band
PANEL_Z = 0.18        # band panels
HOUSING_Z = 0.30      # housings between hatches
HATCH_Z = 0.36        # hatch rim
HUB_Z = 0.40          # hatch centre hub
ROCK_K = 0.9          # boulder height / its smaller half-width


def rock(bm, x, y, z, rx, ry, rz, mat, seed):
    """A faceted boulder: a low-poly (icosphere) ellipsoid with its vertices nudged in and out a little."""
    before = set(bm.faces)
    res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for k, v in enumerate(res["verts"]):
        j = 1.0 + 0.08 * math.sin(seed * 12.9898 + k * 78.233)
        # The buried half is flattened just under the bed so it doesn't poke out below it.
        v.co = Vector((x + v.co.x * rx * j, y + v.co.y * ry * j, max(z + v.co.z * rz * j, z - 0.05)))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = False


def build_wall(sprite, name, tag, kinds, band):
    n = len(kinds)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.0, roughness=0.95),  # 0 rock bed and crevices
        pal(7, metallic=0.0, roughness=0.85),  # 1 rock (shadowed)
        pal(8, metallic=0.0, roughness=0.8),  # 2 rock
        pal(10, metallic=0.0, roughness=0.75),  # 3 rock (lit)
        pal(170, metallic=0.0, roughness=0.8),  # 4 beige stone
        pal(88, metallic=0.35, roughness=0.45),  # 5 purple plate
        pal(90, metallic=0.35, roughness=0.4),  # 6 purple lit edge / panel / housing
        pal(89, metallic=0.35, roughness=0.45),  # 7 purple mid
        pal(86, metallic=0.35, roughness=0.5),  # 8 purple shadowed edge
        pal(85, metallic=0.4, roughness=0.5),  # 9 dark vent
    ]
    BED, ROCK_D, ROCK, ROCK_L, BEIGE, PLATE, LIT, MID, SHADE, VENT = range(10)
    key = {"rock_d": ROCK_D, "rock": ROCK, "rock_l": ROCK_L, "beige": BEIGE}
    W = 24 * n
    X = lambda c: (c - W / 2) / 12  # noqa: E731
    Y = lambda r: (14 - r) / 12  # noqa: E731
    bm = bmesh.new()

    # Rock bed under the whole row.
    box(bm, X(0), Y(28), X(W), Y(0), -0.2, BED_Z, mat=BED)

    # Boulders: round, about ROCK_K times their smaller half-width tall.
    rocks = lib.WALL_ROCKS[band]
    seed = 0

    def place(x, y, rx, ry, rz, m):
        nonlocal seed
        seed += 1
        h = max(rz, ROCK_K * min(rx, ry) * PX)
        rock(bm, x, y, BED_Z, rx * PX, ry * PX, h, key[m], seed)

    for i, kind in enumerate(kinds):
        o = 24 * i
        for x, y, rx, ry, rz, m in rocks["all"] + rocks.get(kind, []):
            place(X(o + x), Y(y), rx, ry, rz, m)
    for i in range(n + 1):
        for x, y, rx, ry, rz, m in rocks["edge"]:
            place(X(24 * i + x), Y(y), rx, ry, rz, m)

    # The purple band along the top, with raised panels on it.
    def band_span(kind):
        return {"left": (13, 24), "mid": (0, 24), "right": (0, 12)}[kind]
    x0 = band_span(kinds[0])[0]
    x1 = 24 * (n - 1) + band_span(kinds[-1])[1]
    box(bm, X(x0), Y(11), X(x1), Y(0), -0.07, BAND_Z, mat=PLATE)
    pmats = (LIT, LIT, MID, SHADE)
    pmats2 = (MID, LIT, MID, SHADE)
    for i, kind in enumerate(kinds):
        o = 24 * i
        a, b = band_span(kind)
        for (pa, pb, pm) in [((5, 0), (12, 4), pmats), ((13, 0), (19, 4), pmats2)]:
            if pa[0] >= a and pb[0] <= b:
                bevel_plate(bm, [(X(o + pa[0]), Y(pb[1])), (X(o + pb[0]), Y(pb[1])),
                                 (X(o + pb[0]), Y(pa[1])), (X(o + pa[0]), Y(pa[1]))],
                            BAND_Z - 0.02, PANEL_Z, 0.6 * PX, pm)

    # Housings filling the V between neighbouring hatches (rows 4.6-11), each with a ribbed vent
    # on its front face above the crevice.
    for i in range(1, n):
        o = 24 * i
        outline = [(o - 7.4, 4.6), (o + 7.4, 4.6), (o + 3, 9), (o + 3, 11), (o - 3, 11), (o - 3, 9)]
        bevel_plate(bm, [(X(c), Y(r)) for c, r in outline], -0.07, HOUSING_Z, 0.9 * PX,
                    (LIT, LIT, MID, SHADE))
        vy0, vy1 = Y(11.6), Y(10.9)
        box(bm, X(o - 2.2), vy0, X(o + 2.2), vy1, BED_Z, HOUSING_Z - 0.09, mat=VENT)
        for k in range(3):
            z = BED_Z + 0.04 + k * 0.065
            box(bm, X(o - 2.0), Y(11.8), X(o + 2.0), vy1, z, z + 0.025, mat=MID)

    # The octagon hatch on every tile: a chamfered armour block with a low centre hub.
    for i in range(n):
        o = 24 * i
        outline = [(X(o + c), Y(r)) for c, r in lib.OCTAGON]
        bevel_plate(bm, outline, -0.05, HATCH_Z, 1.3 * PX, (PLATE, LIT, MID, SHADE))
        if lib._area(outline) < 0:
            outline = list(reversed(outline))
        hub = lib.inset(outline, 3.6 * PX)
        bevel_plate(bm, hub, HATCH_Z - 0.03, HUB_Z, 1.2 * PX, (PLATE, PLATE, PLATE, PLATE))

    obj = lib.to_object(name, bm, mats, coll)
    centres = [(24 * i + 12 - W / 2, 0) for i in range(n)]
    return obj, centres


def main(script_file):
    """lib_b048.wall_main with this script's build_wall."""
    root = common.repo_root(script_file)
    pieces = list(dict.fromkeys(TILES))
    sprite = lib.merged_sprite(root, pieces)
    obj, centres = build_wall(sprite, NAME, NAME.replace("assembly-", "a"), KINDS, BAND)
    layout, seen = [], set()
    for t, (cx, cy) in zip(TILES, centres):
        if t not in seen:
            seen.add(t)
            layout.append((t, cx, cy))
    parts = common.split_assembly(obj, layout)
    for p in pieces:
        data = common.load_sprite(root, p)
        common.export_sprite_model(root, [parts[p]], f"enemies/{p}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref, size = lib.composite_png(root, TILES, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for p in pieces:
            data = common.load_sprite(root, p)
            img = root / "reference" / "models" / p / data["frames"][0]["image"]
            common.render_preview([parts[p]], str(out.parent / f"{p}.png"), str(img), size=2)


if __name__ == "__main__":
    main(__file__)
