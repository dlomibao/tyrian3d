"""Grey dome base (newshb.shp 154, 156, 158, 160), the bottom of the CAMANIS boss, D65 hard surface.

Seen in level 3.10. Four 2x2 pieces side by side make one 96 x 28 px row (sprite.json
`assemblyLayout`): the lower arc of the round grey hull whose upper part is assembly-newshb-115's
deck (the row sits directly under it, column 0 here = column 12 there). Built as what it is:
  * a flat plateau at the height of newshb-115's deck, rolling over a faired quarter-round shoulder
    (pchip-like stations, smooth shading) to the ground along the sprite's outline; the sprite's lit
    left bevel and dark right/front bands are that shoulder's lighting, one material (art rule 2);
  * a louvred side panel each side: three chamfered slats with real gaps over a dark floor, a seam;
  * two service channels (newshb-115's slatted vents run on into them): rails either side of a dark
    floor, a round pipe lying in each with saddle clamps and a bright flanged end, plugged into a
    machined lamp housing with a recessed red lens (the flickering lights) and a hot core;
  * the raised centre block with a rolled front edge and a step, the front lip in three plates.
The red lights flicker on the pieces' extra frames (newshb-156: 191/229/267, newshb-158:
193/231/269): their materials brighten two shades, then six (palette_material frames=), so one model
per piece covers every frame. Built whole in pixel-edge coordinates, left half mirrored about column
edge 47.5, cut into the four pieces by lib_b119.export_assembly (cull, weighted normals, AO/roughness
bake, outline shell from a sealed pre-cull copy; D50/D51/D65/D90/D118).

Run: blender --background --python assets/blender/enemies/assembly-newshb-154.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b119 as lib  # noqa: E402
from lib_b119 import PX, XE, YE  # noqa: E402

NAME = "assembly-newshb-154"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-154", "newshb-156", "newshb-158", "newshb-160"]
AXIS = 47.5   # column edge the row mirrors about
TOP = 0.62    # plateau height: newshb-115's deck plates
FLICKER = {191: 2, 229: 2, 267: 6, 193: 2, 231: 2, 269: 6}

# Left edge of the sprite's inner mask per row (row 0 is the cut under newshb-115).
LEFT = {0: 4, 1: 4, 2: 4, 3: 5, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 10: 11, 11: 12, 12: 13, 13: 14, 14: 15,
        15: 17, 16: 18, 17: 19, 18: 21, 19: 22, 20: 23, 21: 25, 22: 27, 23: 29, 24: 34}
BOTTOM = 25.0
# The plateau's edge (pixel edges), from the top cut round to the axis.
PLATEAU = [(22.0, 0.0), (22.0, 3.5), (21.6, 8.5), (21.6, 12.0), (23.0, 14.6), (25.4, 16.1), (28.4, 17.2),
           (31.0, 18.3), (33.5, 19.2), (36.5, 19.8), (40.5, 20.1), (AXIS, 20.2)]


def smooth(pts, passes=2):
    for _ in range(passes):
        pts = [pts[0]] + [((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4)
                          for a, b, c in zip(pts, pts[1:], pts[2:])] + [pts[-1]]
    return pts


def outer_outline():
    pts = [(float(LEFT[0]), 0.0)] + [(float(LEFT[r]), r + 0.5) for r in range(1, 25)]
    pts += [(36.0, BOTTOM), (40.5, BOTTOM), (AXIS, BOTTOM)]
    return smooth(pts, 2)


def resample(pts, n):
    """n points evenly along the polyline pts by arc length."""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out = []
    for k in range(n):
        s = d[-1] * k / (n - 1)
        i = min(max(j for j in range(len(d) - 1) if d[j] <= s + 1e-9), len(pts) - 2)
        t = min(1.0, (s - d[i]) / ((d[i + 1] - d[i]) or 1))
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    return out


TOPM, RIM, SLAT, GROOVE, DARK, PIPE, BRIGHT, FRAME, RED, HOT = range(10)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshb154", **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.55, roughness=0.45),   # TOPM plateau, centre block (6)
        pal(5, metallic=0.55, roughness=0.48),   # RIM faired shoulder (lit 7-9 left, 3-4 right: lighting)
        pal(7, metallic=0.55, roughness=0.42),   # SLAT louvre slats, lip, rails (7)
        pal(4, metallic=0.5, roughness=0.55),    # GROOVE panel floors, seams (4)
        pal(3, metallic=0.45, roughness=0.6),    # DARK channel floors (3)
        common.palette_material(sprite, 6, "nshb154-pipe", metallic=0.65, roughness=0.32),  # PIPE (6), polished
        pal(10, metallic=0.65, roughness=0.3),   # BRIGHT flanged pipe ends, rolled edge, screws (10)
        pal(8, metallic=0.55, roughness=0.4),    # FRAME lamp housings (8)
        common.palette_material(sprite, 117, "nshb154-light", metallic=1.0, roughness=0.9, emission_strength=2.6,
                                frames={f: 117 + d for f, d in FLICKER.items()}),   # RED lens (D126/D173)
        common.palette_material(sprite, 119, "nshb154-core", metallic=1.0, roughness=0.9, emission_strength=3.2,
                                frames={f: 119 + d for f, d in FLICKER.items()}),   # HOT core
    ]
    for i in (PIPE, BRIGHT):
        b = next(n for n in mats[i].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.6
    return mats


def build_body(m):
    """Left half of the plateau and its faired shoulder, closed (end wall at the top cut, bottom)."""
    n = 26
    inner = resample(PLATEAU, n)
    outer = resample(outer_outline(), n)
    ts = [0.0, 0.12, 0.3, 0.5, 0.68, 0.82, 0.92, 1.0]      # share of the way out
    zs = [1.0, 0.985, 0.93, 0.8, 0.62, 0.42, 0.22, 0.0]    # height share: a rolled shoulder
    secs = []
    for (ci, ri), (co, ro) in zip(inner, outer):
        secs.append([m.nv((XE(ci + (co - ci) * t), YE(ri + (ro - ri) * t), TOP * zf)) for t, zf in zip(ts, zs)])
    for a, b in zip(secs, secs[1:]):
        for k in range(len(ts) - 1):
            m.face((a[k], b[k], b[k + 1], a[k + 1]), RIM)
    top_axis = m.nv((XE(AXIS), YE(0.0), TOP))
    bot_axis = m.nv((XE(AXIS), YE(0.0), 0.0))
    m.face([s[0] for s in secs] + [top_axis], TOPM)
    m.face([bot_axis] + [s[-1] for s in reversed(secs)], RIM)
    m.face([top_axis, bot_axis] + list(reversed(secs[0][1:])) + [secs[0][0]], RIM)


def build_left(m):
    """Left-half details (mirrored)."""
    z = TOP
    # Louvred side panel: a dark floor, three chamfered slats with real gaps, a seam down it.
    lib.slab(m, [(22.2, 6.6), (35.8, 6.6), (35.8, 15.6), (24.0, 15.6), (22.2, 14.2)], z - 0.02, z + 0.012, GROOVE, ch=0.008)
    for r0 in (7.6, 10.6, 13.6):
        lib.chbox(m, 22.5 if r0 < 13 else 24.2, r0, 35.5, r0 + 1.8, z, z + 0.055, SLAT, ch=0.35, chz=0.02)
    lib.chbox(m, 29.0, 7.0, 29.7, 15.4, z, z + 0.035, GROOVE, ch=0.15, chz=0.01)
    # Service channel (columns 36-42): rails, a dark floor, a round pipe with a bright flanged end.
    lib.slab(m, [(36.6, 0.0), (41.4, 0.0), (41.4, 10.4), (36.6, 10.4)], z - 0.02, z + 0.01, DARK, ch=0.0)
    for c0, c1 in ((35.8, 36.7), (41.3, 42.2)):
        lib.chbox(m, c0, 0.0, c1, 10.0, z - 0.02, z + 0.07, SLAT, ch=0.2, chz=0.015)
    pz = z + 0.15
    lib.lathe_y(m, 39.0, [(0.0, 1.55, pz), (7.6, 1.55, pz), (7.75, 1.95, pz), (8.9, 1.95, pz), (9.1, 1.6, pz),
                          (9.6, 1.6, pz)], PIPE, sides=14, mats=[PIPE, BRIGHT, BRIGHT, BRIGHT, BRIGHT])
    for r in (2.5, 5.5):  # saddle clamps holding the pipe down
        lib.lathe_y(m, 39.0, [(r, 1.5, pz), (r + 0.05, 1.85, pz), (r + 0.75, 1.85, pz), (r + 0.8, 1.5, pz)],
                    SLAT, sides=14)
    # Machined lamp housing with a recessed red lens and a hot core.
    lib.chbox(m, 36.7, 9.4, 41.3, 15.5, z - 0.02, z + 0.2, FRAME, ch=0.6, chz=0.03)
    lib.chbox(m, 37.3, 10.3, 40.7, 14.6, z + 0.15, z + 0.205, GROOVE, ch=0.4, chz=0.01)
    lens = [(37.7, 11.2), (38.3, 10.7), (39.7, 10.7), (40.3, 11.2), (40.3, 14.0), (39.7, 14.3), (38.3, 14.3), (37.7, 14.0)]
    lib.dome_slab(m, lens, z + 0.17, z + 0.2, 0.05, RED, steps=3, shrink=0.5)
    lib.dome_slab(m, [(38.4, 12.2), (39.6, 12.2), (39.9, 13.0), (39.6, 13.8), (38.4, 13.8), (38.1, 13.0)],
                  z + 0.2, z + 0.24, 0.02, HOT, steps=2, shrink=0.3)
    for rr in (9.9, 15.0):  # hex screws on the housing's flange
        lib.lathe_z(m, 39.0, rr, [(z + 0.19, 0.35), (z + 0.23, 0.35), (z + 0.235, 0.2)], BRIGHT, sides=6)
    # Front lip, outer plate (the middle plate is built whole).
    lib.slab(m, [(30.4, 17.0), (46.1, 17.0), (46.1, 19.9), (33.0, 19.9), (31.2, 18.9)], z - 0.03, z + 0.035, SLAT, ch=0.015)


def build_centre(m):
    z = TOP
    # Raised block with two lid plates, a rolled front edge, a step below it.
    lib.chbox(m, 42.8, 0.0, 52.2, 5.4, z - 0.02, z + 0.11, TOPM, ch=0.5, chz=0.03)
    for c0, c1 in ((43.6, 47.3), (47.7, 51.4)):
        lib.chbox(m, c0, 0.6, c1, 4.6, z + 0.1, z + 0.14, SLAT, ch=0.35, chz=0.012)
    secs = []
    for c in (42.9, 43.2, 51.8, 52.1):
        rad = 1.0 if 43.0 < c < 52.0 else 0.75
        secs.append([m.nv((XE(c), YE(5.6) + math.cos(2 * math.pi * (k + 0.5) / 12) * rad * PX,
                           z + 0.06 + math.sin(2 * math.pi * (k + 0.5) / 12) * rad * PX)) for k in range(12)])
    lib.rings_faces(m, secs, BRIGHT)
    lib.chbox(m, 43.0, 6.6, 52.0, 9.4, z - 0.02, z + 0.05, SLAT, ch=0.4, chz=0.015)
    # Middle and right lip plates (the sprite's seams at columns 46 and 51 are the gaps), their floor.
    lib.slab(m, [(46.6, 17.0), (50.9, 17.0), (50.9, 19.9), (46.6, 19.9)], z - 0.03, z + 0.035, SLAT, ch=0.015)
    lib.slab(m, [(30.0, 16.7), (65.0, 16.7), (65.0, 20.0), (30.0, 20.0)], z - 0.04, z + 0.005, GROOVE, ch=0.0)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    m = lib.M()
    n = m.mark()
    build_body(m)
    build_left(m)
    m.mirror_since(n, AXIS)
    build_centre(m)
    return m.to_object(NAME, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    parts = lib.export_assembly(ROOT, obj, sprite, PIECES,
                                textured=[TOPM, RIM, SLAT, GROOVE, DARK, PIPE, BRIGHT, FRAME], tag="nshb154")
    if "--frames" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for name in ("newshb-156", "newshb-158"):
            data = common.load_sprite(ROOT, name)
            common.render_frame_previews([parts[name]], str(out.parent / f"{name}.png"), data, ROOT)


if __name__ == "__main__":
    main()
