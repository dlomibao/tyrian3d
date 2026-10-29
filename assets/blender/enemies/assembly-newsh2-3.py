"""Long pipe (newsh2.shp frames 1, 3 and 5): a 3D version of its sprites.

Seen in levels 1.3 and 3.17. Nine 2x2 enemies in a row make one 216 x 28 px pipe lying on the
ground (sprite.json `assemblyLayout`): newsh2-1 is its left end (a rounded grey cap, a red
coupling, a grey can and a big red end flange), newsh2-3 is the repeating section (seven of them:
a grey can, a red flange, a grey can, a thin red coupling, a grey can, a thin red coupling) and
newsh2-5 is the right end, a grey cone that tapers to a point. The thin red couplings rest on
dark saddles on the ground.

The pipe is built whole in assembly coordinates and cut into its pieces with
common.split_assembly; every newsh2-3 is the same, so the section is periodic and only one of
them is exported. The grey cans and red flanges take the sprite's colour under each upward
facet (lit on top, dark on the shadowed side); facets underneath stay dark.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-3.py [-- --preview out.png]
(the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b120 as lib  # noqa: E402

NAME = "assembly-newsh2-3"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-1", "newsh2-3", "newsh2-5"]
W, H = 216, 28  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12
AXIS = 13.0  # pixel-edge row of the pipe's axis
ZA = 6.0 / 12  # height of the pipe's axis: the cans (radius 6 px) rest on the ground


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


# Palette slots, one mid-tone per part (the sprite's dark lower halves and lit tops are its
# lighting, left to the game's light): grey cans, cap and cone; red clamp collars and the copper
# rod; the dark red of the clamps' split; the near-black brown of the hangers.
GREY = 7
RED = 72
ROD = 73
SLOT = 66
BROWN = 16
ROD_ROW = 11.8  # the rod is drawn a little above the cans' axis (rows 9-13)


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a3"
    mats = [
        common.palette_material(sprite, GREY, tag, metallic=0.45, roughness=0.38),
        common.palette_material(sprite, RED, tag, metallic=0.3, roughness=0.42),
        common.palette_material(sprite, ROD, tag, metallic=0.35, roughness=0.35),
        common.palette_material(sprite, SLOT, tag, metallic=0.1, roughness=0.8),
        common.palette_material(sprite, BROWN, tag, metallic=0.2, roughness=0.8),
    ]
    M_GREY, M_RED, M_ROD, M_SLOT, M_HANGER = range(5)

    bm = bmesh.new()

    def lathe(stations, mat, sides=20, slot=None, slot_mat=None, hard=()):
        """A solid of revolution along +X. stations: (column edge, radius px[, axis row]); a radius
        of 0 closes the end in a point. `slot` = (a0, a1, depth px): a groove cut along the whole
        length between those angles (0 = top, positive towards the screen bottom), walls straight
        down. Rings at the indices in `hard` get crisp (sharp) edges."""
        angles = [2 * math.pi * k / sides for k in range(sides)]
        if slot:
            a0, a1, _ = slot
            angles = sorted([a for a in angles if not (a0 - 0.05 < a < a1 + 0.05)]
                            + [a0, a0 + 1e-3, a1 - 1e-3, a1])
        n = len(angles)

        def scale(i):
            if slot and slot[0] < angles[i] < slot[1]:
                return slot[2]
            return 0.0

        first = len(bm.faces)
        rings = []
        for st in stations:
            e, r = st[0], st[1]
            row = st[2] if len(st) > 2 else AXIS
            x, yc = XE(e), YE(row)
            if r <= 0:
                rings.append([bm.verts.new((x, yc, ZA))])
                continue
            ring = []
            for i, a in enumerate(angles):
                rr = max(r - scale(i), 0.3) * PX
                ring.append(bm.verts.new((x, yc - rr * math.sin(a), ZA + rr * math.cos(a))))
            rings.append(ring)
        for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
            for i in range(n):
                j = (i + 1) % n
                if len(r0) == 1:
                    f = bm.faces.new((r0[0], r1[j], r1[i]))
                elif len(r1) == 1:
                    f = bm.faces.new((r0[i], r0[j], r1[0]))
                else:
                    f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
                f.material_index = mat
                if slot and slot[0] <= angles[i] and angles[j] <= slot[1] + 1e-6 and j != 0:
                    f.material_index = slot_mat
        for ring in (rings[0], rings[-1]):
            if len(ring) > 1:
                f = bm.faces.new(ring)
                f.material_index = mat
        bm.faces.ensure_lookup_table()
        for f in bm.faces[first:]:
            f.smooth = True
        # Crisp edges: the end rims, the slot's walls and the given rings.
        for k in set(hard) | {0, len(rings) - 1}:
            ring = rings[k]
            if len(ring) == 1:
                continue
            for a, b in zip(ring, ring[1:] + ring[:1]):
                e = bm.edges.get((a, b))
                if e:
                    e.smooth = False
        if slot:  # the slot's wall edges run along X between rings
            for r0, r1 in zip(rings, rings[1:]):
                if len(r0) == 1 or len(r1) == 1:
                    continue
                for i in range(n):
                    if abs(angles[i] - slot[0]) < 2e-3 or abs(angles[i] - slot[1]) < 2e-3:
                        e = bm.edges.get((r0[i], r1[i]))
                        if e:
                            e.smooth = False

    def can(e0, e1, r=6.0):
        """A grey ring-can: flat sides, rounded tyre-like rims, as tall as it is wide."""
        lathe([(e0, r * 0.62), (e0 + 0.15, r * 0.82), (e0 + 0.45, r * 0.95), (e0 + 0.9, r),
               (e1 - 0.9, r), (e1 - 0.45, r * 0.95), (e1 - 0.15, r * 0.82), (e1, r * 0.62)], M_GREY)

    # The clamp's split: a groove on the screen-bottom side of each collar (sprite rows 15-17).
    SPLIT = (math.radians(20), math.radians(46), 1.3)

    def collar(e0, e1, r):
        """A red clamp collar: a flat-sided band with chamfered edges, split on its lower side."""
        lathe([(e0, r - 0.6), (e0 + 0.3, r), (e1 - 0.3, r), (e1, r - 0.6)], M_RED, sides=24,
              slot=SPLIT, slot_mat=M_SLOT, hard=(1, 2))

    def hanger(e0, e1):
        """A dark saddle the rod rests on, from the ground up to the rod's underside."""
        lib.box(bm, XE(e0), YE(17.0), XE(e1), YE(14.4), 0.0, ZA - 1.6 * PX, mat=M_HANGER)
        lib.box(bm, XE(e0 + 0.5), YE(14.4), XE(e1 - 0.5), YE(13.6), ZA - 3.0 * PX, ZA - 1.6 * PX,
                mat=M_HANGER)

    # The copper rod runs through the whole pipe (the cans and collars are threaded on it).
    lathe([(10.0, 2.5, ROD_ROW), (193.0, 2.5, ROD_ROW)], M_ROD, sides=12)

    # Left end (newsh2-1, columns 0-23): domed cap, rod, can, the big end clamp over a can.
    lathe([(0.6, 0.0), (0.9, 2.6), (1.5, 4.1), (2.4, 5.2), (3.6, 5.85), (5.0, 6.0), (10.4, 6.0),
           (10.8, 5.4), (11.0, 3.8)], M_GREY, hard=(6,))
    hanger(11.2, 13.8)
    can(14.0, 19.2)
    can(18.6, 24.4)
    collar(18.8, 23.4, 8.0)

    # Seven repeating sections (newsh2-3): can under a red clamp, rod, ring-can, rod.
    for t in range(1, 8):
        o = 24 * t
        # The first can runs across the section's left edge (from the previous section's column
        # 23), so every section is cut alike; the first one starts inside the end clamp.
        can(o - 1.0, o + 11.8)
        collar(o + 2.7, o + 7.1, 7.0)
        hanger(o + 12.3, o + 14.9)
        can(o + 15.0, o + 19.8)
        hanger(o + 20.3, o + 22.7)

    # Right end (newsh2-5, columns 192-215): a cone tapering to a point, its tip a little high.
    o = 192
    lathe([(o - 1.0, 4.4), (o - 0.75, 5.7), (o - 0.3, 6.0), (o + 4, 4.9, 12.85), (o + 8, 3.75, 12.7),
           (o + 12, 2.55, 12.55), (o + 16, 1.4, 12.45), (o + 20.8, 0.0, 12.4)], M_GREY, hard=(2,))

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-3")
    sprite = common.load_sprite(ROOT, "newsh2-3")
    sprite["colors"] = colors
    obj = build(sprite, grid)
    seen = set()
    pieces_layout = []
    for e in layout:  # newsh2-3 repeats; its first copy (left of the row) is the one exported
        if e["model"] in seen:
            continue
        if e["model"] == "newsh2-3" and e["cx"] != min(f["cx"] for f in layout if f["model"] == "newsh2-3"):
            continue
        seen.add(e["model"])
        pieces_layout.append((e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2))
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_assembly(ROOT, obj, pieces_layout, out, grid, colors, None)


if __name__ == "__main__":
    main()
