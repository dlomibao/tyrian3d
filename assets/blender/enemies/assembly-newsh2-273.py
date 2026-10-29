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
BED_Z = -0.03         # rocks sit on the bed at this height
BAND_Z = 0.10         # top of the band
PANEL_Z = 0.18        # band panels
HOUSING_Z = 0.25      # upper housing between hatches (above the band panels, below the hatches)
WEDGE_Z = 0.23        # its lower, front step (the V between the hatches)
HATCH_Z = 0.33        # hatch body (the light ring sits a little below it)
RING_Z = 0.37         # the armour panel rings on the hatch
HUB_Z = 0.43          # hatch centre hub
ROCK_K = 0.75         # rock height / its smaller half-width
ROCK_MAX = 0.31       # rocks stay below the hatches

# Rocks as (x, y, rx, ry, material key) in tile pixels (pixel-edge coordinates), placed where the
# sprite draws them (the concept agrees); "edge" rocks sit on every tile boundary, both ends included.
ROCKS = {
    "all": [(6.5, 23.0, 4.4, 3.4, "rock"), (12.5, 26.0, 3.5, 2.2, "rock_d"),
            (17.5, 25.6, 4.0, 2.8, "rock"), (6.5, 27.8, 4.6, 2.5, "beige"),
            (21.5, 27.0, 3.0, 1.8, "rock_d"), (2.0, 26.0, 2.6, 2.2, "rock_d")],
    "edge": [(-2.0, 19.8, 5.2, 4.8, "rock_l")],
    "left": [(5.0, 1.6, 5.4, 2.9, "beige"), (11.6, 1.8, 1.5, 2.2, "rock"),
             (1.6, 10.0, 2.6, 5.2, "rock"), (4.5, 5.3, 3.2, 1.6, "rock_d")],
    "right": [(15.6, 1.8, 3.6, 2.5, "rock"), (21.4, 2.0, 2.6, 2.4, "rock"),
              (22.0, 8.0, 2.5, 4.2, "rock_l"), (22.4, 13.0, 1.6, 2.2, "rock_d")],
}


def pebble(bm, x, y, z, rx, ry, rz, mat, seed):
    """A smooth, round stone (the beige ones): a low-poly ellipsoid, nudged a little."""
    before = set(bm.faces)
    res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for k, v in enumerate(res["verts"]):
        j = 1.0 + 0.06 * math.sin(seed * 12.9898 + k * 78.233)
        v.co = Vector((x + v.co.x * rx * j, y + v.co.y * ry * j, max(z + v.co.z * rz * j, z - 0.05)))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def slab_rock(bm, x, y, z, rx, ry, h, mat, seed):
    """A faceted flagstone boulder, as the concept draws the grey rocks: an irregular (but convex)
    outline, steep chamfered sides and a broad flat top, hard-edged and matte."""
    n = 7 + seed % 3
    rnd = lambda k: math.sin(seed * 91.7 + k * 37.3) * 0.5 + 0.5  # noqa: E731
    angs = sorted(2 * math.pi * (k + 0.55 * (rnd(k) - 0.5)) / n for k in range(n))
    ring = lambda s, zz: [bm.verts.new((x + math.cos(a) * rx * s, y + math.sin(a) * ry * s, zz)) for a in angs]  # noqa: E731
    rings = [ring(1.0, z - 0.05), ring(0.97, z + 0.45 * h), ring(0.62, z + h)]
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(rings[-1]))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def ngon(cx, cy, r, n=8, rot=math.pi / 8, sx=1.0):
    return [(cx + math.cos(rot + 2 * math.pi * k / n) * r * sx, cy + math.sin(rot + 2 * math.pi * k / n) * r)
            for k in range(n)]


def ccw(pts):
    return pts if lib._area(pts) > 0 else list(reversed(pts))


def ring_panels(bm, outer, inner, z0, z1, gap, bevel, mats):
    """A ring of separate armour panels between two corresponding CCW octagons: one chamfered
    trapezoid per side, with a seam `gap` wide between neighbours."""
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        quad = [outer[i], outer[j], inner[j], inner[i]]
        quad = lib.inset(ccw(quad), gap / 2)
        bevel_plate(bm, quad, z0, z1, bevel, mats)


def build_wall(sprite, name, tag, kinds, band):
    n = len(kinds)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.0, roughness=0.95),  # 0 rock bed and crevices
        pal(7, metallic=0.0, roughness=0.9),  # 1 rock (shadowed)
        pal(8, metallic=0.0, roughness=0.88),  # 2 rock
        pal(10, metallic=0.0, roughness=0.85),  # 3 rock (lit)
        pal(170, metallic=0.0, roughness=0.8),  # 4 beige stone
        pal(88, metallic=0.35, roughness=0.5),  # 5 purple plate
        pal(90, metallic=0.35, roughness=0.45),  # 6 purple lit edge / panel / housing
        pal(89, metallic=0.35, roughness=0.5),  # 7 purple mid
        pal(86, metallic=0.35, roughness=0.55),  # 8 purple shadowed edge
        pal(85, metallic=0.3, roughness=0.6),  # 9 dark vent / light ring well
        pal(9, metallic=0.5, roughness=0.45),  # 10 vent ribs (grey metal)
        # 11 violet hatch lights: a soft glow in the housing's violet (91), kept dim so they stay
        # below the lit boulder tops (the sprite draws no bright marks on the hatch).
        common.palette_material(sprite, 91, tag + "_lamp", metallic=0.0, roughness=0.4, emission_strength=0.22),
        pal(91, metallic=0.3, roughness=0.45),  # 12 light purple: housing tops, hatch rim's lit edge
    ]
    BED, ROCK_D, ROCK, ROCK_L, BEIGE, PLATE, LIT, MID, SHADE, VENT, RIB, LAMP, LIGHT = range(13)
    key = {"rock_d": ROCK_D, "rock": ROCK, "rock_l": ROCK_L, "beige": BEIGE}
    W = 24 * n
    X = lambda c: (c - W / 2) / 12  # noqa: E731
    Y = lambda r: (14 - r) / 12  # noqa: E731
    bm = bmesh.new()

    # Rock bed under the whole row (the concept's dark plating between the rocks).
    box(bm, X(0), Y(28), X(W), Y(0), -0.2, BED_Z, mat=BED)

    seed = 0

    def place(x, y, rx, ry, m):
        nonlocal seed
        seed += 1
        h = min(ROCK_MAX, ROCK_K * min(rx, ry) * PX)
        if m == "beige":
            pebble(bm, x, y, BED_Z, rx * PX, ry * PX, max(h, 0.1), key[m], seed)
        else:
            slab_rock(bm, x, y, BED_Z, rx * PX, ry * PX, h, key[m], seed)

    for i, kind in enumerate(kinds):
        o = 24 * i
        for x, y, rx, ry, m in ROCKS["all"] + ROCKS.get(kind, []):
            place(X(o + x), Y(y), rx, ry, m)
    for i in range(n + 1):
        for x, y, rx, ry, m in ROCKS["edge"]:
            place(X(24 * i + x), Y(y), rx, ry, m)

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

    # The housing between each pair of hatches, as the concept draws it: a wide armoured upper
    # block along the band (cols b-5.5..b+6.5), stepping down to a narrower front wedge that fills
    # the V between the hatches (the sprite's light 90/91 wedge, rows 4.6-10.8), with a ribbed
    # grey vent recessed in its front where it drops into the dark crevice.
    for i in range(1, n):
        o = 24 * i
        upper = [(o - 4.6, 0.0), (o + 3.6, 0.0), (o + 3.6, 4.4), (o - 4.6, 4.4)]
        bevel_plate(bm, ccw([(X(c), Y(r)) for c, r in upper]), -0.07, HOUSING_Z, 0.9 * PX,
                    (LIT, LIGHT, MID, SHADE))
        wedge = [(o - 7.4, 4.0), (o + 7.4, 4.0), (o + 3.1, 9.0), (o + 3.1, 10.9), (o - 3.1, 10.9), (o - 3.1, 9.0)]
        bevel_plate(bm, ccw([(X(c), Y(r)) for c, r in wedge]), -0.07, WEDGE_Z, 0.9 * PX,
                    (LIGHT, LIGHT, MID, SHADE))
        # Vent: a small dark recess at the wedge's lower front only, with two grey ribs, so the
        # light V of the wedge's top survives.
        box(bm, X(o - 1.9), Y(10.95), X(o + 1.9), Y(9.0), WEDGE_Z - 0.10, WEDGE_Z + 0.005, mat=VENT)
        for k in range(2):
            r0 = 9.3 + k * 0.85
            z = WEDGE_Z - 0.005 - k * 0.03
            box(bm, X(o - 1.7), Y(r0 + 0.55), X(o + 1.7), Y(r0), z - 0.03, z + 0.012, mat=RIB)

    # The octagon hatch on every tile, as in the concept: a chamfered armour body; on it an outer
    # and an inner ring of separate armour panels (seams between them), a recessed ring well with
    # eight glowing violet light slits, and a raised octagonal centre hub.
    for i in range(n):
        o = 24 * i
        outline = ccw([(X(o + c), Y(r)) for c, r in lib.OCTAGON])
        bevel_plate(bm, outline, -0.05, HATCH_Z, 1.5 * PX, (PLATE, LIGHT, MID, SHADE))
        top = lib.inset(outline, 1.5 * PX)
        mid_o = lib.inset(outline, 3.4 * PX)
        mid_i = lib.inset(outline, 3.7 * PX)
        well = lib.inset(outline, 5.4 * PX)
        ring_panels(bm, lib.inset(top, 0.2 * PX), mid_o, HATCH_Z - 0.02, RING_Z, 0.25 * PX, 0.5 * PX,
                    (MID, LIGHT, MID, SHADE))
        ring_panels(bm, mid_i, well, HATCH_Z - 0.02, RING_Z - 0.01, 0.25 * PX, 0.45 * PX,
                    (MID, LIGHT, MID, SHADE))
        # The well inside the inner ring, a step below it.
        bevel_plate(bm, well, HATCH_Z - 0.02, HATCH_Z + 0.005, 0.3 * PX, (MID, MID, MID, SHADE))
        cx, cy = X(o + 12), Y(12)
        for k in range(8):
            a = 2 * math.pi * k / 8
            ux, uy = math.cos(a), math.sin(a)
            r = 3.2 * PX * (1.0 if abs(uy) > 0.5 else 1.12)
            hw, hl = 0.32 * PX, 0.9 * PX
            pts = [(cx + ux * (r - hw) - uy * hl, cy + uy * (r - hw) + ux * hl),
                   (cx + ux * (r + hw) - uy * hl, cy + uy * (r + hw) + ux * hl),
                   (cx + ux * (r + hw) + uy * hl, cy + uy * (r + hw) - ux * hl),
                   (cx + ux * (r - hw) + uy * hl, cy + uy * (r - hw) - ux * hl)]
            lib.prism(bm, pts, HATCH_Z - 0.01, HATCH_Z + 0.02, mat=LAMP)
        hub = ngon(cx, cy, 2.3 * PX, sx=1.05)
        bevel_plate(bm, hub, HATCH_Z - 0.02, HUB_Z, 0.8 * PX, (LIT, LIGHT, MID, SHADE))
        cap = ngon(cx, cy, 1.25 * PX, sx=1.05)
        bevel_plate(bm, cap, HUB_Z - 0.02, HUB_Z + 0.015, 0.3 * PX, (PLATE, LIT, MID, SHADE))

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
