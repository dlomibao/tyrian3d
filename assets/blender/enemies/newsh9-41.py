"""Grey ground emplacement (newsh9.shp frame 41): a 3D version of its sprite.

Seen in level 4.4. A ground structure seen from above: a rounded grey hull whose raised,
horseshoe-shaped rim cradles a ribbed central column with a dark grey drum on each side, a
vaulted housing at the back (top of the sprite) capped by a dark knob, and a glowing red core
bulging out of the front. One frame, one model; it sits on the ground with its base at z = 0.

Run: blender --background --python assets/blender/enemies/newsh9-41.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newsh9-41"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def ex(c):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (c - 12) / 12


def ey(r):
    """Sprite row edge (0 = top edge of row 0) to Blender Y: sprite up is +Y."""
    return (14 - r) / 12


def _se(t, p):
    """Signed superellipse power: rounder than a circle for p > 2."""
    return math.copysign(abs(t) ** (2 / p), t)


def half_loft(bm, sections, sides=10, power=2.5, mat_index=0):
    """Loft half-rings (a flat bottom on z = 0) along Y: sections are (y, half_width, height, x_centre)."""
    rings = []
    for y, w, h, cx in sections:
        ring = []
        for i in range(sides + 1):
            a = math.pi * i / sides
            ring.append(bm.verts.new((cx + w * _se(math.cos(a), power), y, h * _se(math.sin(a), power))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i])).material_index = mat_index
        bm.faces.new((r0[-1], r0[0], r1[0], r1[-1])).material_index = mat_index
    bm.faces.new(rings[0]).material_index = mat_index
    bm.faces.new(list(reversed(rings[-1]))).material_index = mat_index


def outline_dome(bm, outline, centre, height, rings=5, power=2.6, mat_index=0):
    """A dome over an XY outline: rings shrink toward `centre` while rising to `height`; flat base."""
    cx, cy = centre
    layers = []
    for k in range(rings):
        t = k / rings  # 0 at the base, rising
        s = math.cos(t * math.pi / 2) ** (2 / power)
        z = height * math.sin(t * math.pi / 2) ** (2 / power)
        layers.append([bm.verts.new((cx + (x - cx) * s, cy + (y - cy) * s, z)) for x, y in outline])
    top = bm.verts.new((cx, cy, height))
    n = len(outline)
    for l0, l1 in zip(layers, layers[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat_index
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((layers[-1][i], layers[-1][j], top)).material_index = mat_index
    bm.faces.new(list(reversed(layers[0]))).material_index = mat_index


def ellipsoid(bm, centre, radii, sides=14, rings=8, mat_index=0):
    """An ellipsoid with radii (rx, ry, rz) at `centre`."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    sections = [(-ry, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        a = math.pi * i / rings
        sections.append((-ry * math.cos(a), rx * math.sin(a), rz * math.sin(a), 0.0))
    sections.append((ry, 0.0, 0.0, 0.0))
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += cx
        v.co.y += cy
        v.co.z += cz


def path_tube(bm, points, half_w, half_h, sides=8, mat_index=0):
    """A tube along a horizontal-ish path of (x, y, z) points, an ellipse (half_w across, half_h up)."""
    rings = []
    n = len(points)
    for i, (x, y, z) in enumerate(points):
        x0, y0, _ = points[max(i - 1, 0)]
        x1, y1, _ = points[min(i + 1, n - 1)]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            c, s = math.cos(a) * half_w, math.sin(a) * half_h
            ring.append(bm.verts.new((x + nx * c, y + ny * c, z + s)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat_index
    bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    bm.faces.new(rings[-1]).material_index = mat_index


def mirrored(half):
    """A left-half outline (top to bottom, edge coords) closed by its mirror image about column 12."""
    return half + [(24 - c, r) for c, r in reversed(half)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(105, metallic=0.45, roughness=0.45),  # 0 hull
        pal(108, metallic=0.5, roughness=0.35),  # 1 rim crest
        pal(106, metallic=0.45, roughness=0.4),  # 2 housing and column
        pal(6, metallic=0.6, roughness=0.25),  # 3 dark drums and knob
        pal(245, metallic=0.2, roughness=0.3, emission_strength=2.5),  # 4 red core
        pal(251, emission_strength=4.0),  # 5 core hot spot
        pal(102, metallic=0.4, roughness=0.5),  # 6 grooves
    ]
    HULL, RIM, HOUSE, DRUM, CORE, HOT, GROOVE = range(7)
    bm = bmesh.new()

    # Hull: the rounded body from row 8 down to row 24, columns 2-21, low and broad.
    half = [(12, 8.0), (5.2, 8.0), (3.6, 8.9), (2.2, 10.3), (2.0, 12.5), (2.0, 18.0), (2.1, 21.0),
            (2.8, 22.6), (4.0, 23.7), (6.5, 24.4), (9.5, 24.6)]
    half = half[1:]  # the mirror closes the polygon through the centreline
    pts = mirrored(half)
    outline = [(ex(c), ey(r)) for c, r in reversed(pts)]
    common_centre = (0.0, ey(15.5))
    outline_dome(bm, outline, common_centre, 0.19, rings=5, mat_index=HULL)

    # Horseshoe rim: the bright crest that runs down the left flank, round above the core and up
    # the right flank (the 108-111 highlight arc, rows 10-17).
    left = [(2.9, 10.0, 0.08), (3.3, 12.3, 0.15), (4.3, 14.3, 0.19), (5.8, 15.8, 0.21),
            (8.0, 16.9, 0.22), (10.2, 17.4, 0.22)]
    path = left + [(24 - c, r, z) for c, r, z in reversed(left)]
    path = [(ex(c), ey(r), z) for c, r, z in path]
    path_tube(bm, path, 1.5 / 12, 0.07, sides=8, mat_index=RIM)
    # A broad lip under the crest so the flank reads as one raised wall, columns 2-6.
    lip = [(3.6, 10.6, 0.06), (4.2, 12.6, 0.11), (5.3, 14.3, 0.14), (6.8, 15.4, 0.15)]
    for flip in (False, True):
        p = [((24 - c) if flip else c, r, z) for c, r, z in lip]
        path_tube(bm, [(ex(c), ey(r), z) for c, r, z in p], 1.7 / 12, 0.08, sides=8, mat_index=HULL)

    # Vaulted housing at the back: columns 6-18, rows 3-8, lit on its left, ridge down the middle.
    vault = [(2.9, 5.6, 0.22), (3.5, 6.3, 0.29), (5.5, 6.4, 0.34), (7.3, 6.1, 0.33), (8.6, 5.0, 0.24)]
    half_loft(bm, [(ey(r), w / 12, h, 0.0) for r, w, h in vault], sides=10, power=3.0, mat_index=HOUSE)
    # The dark groove along its front edge (row 7).
    path_tube(bm, [(ex(7.2), ey(7.6), 0.25), (ex(12), ey(8.0), 0.29), (ex(16.8), ey(7.6), 0.25)],
              0.5 / 12, 0.03, sides=6, mat_index=GROOVE)

    # Dark knob in the notch at the back (rows 2-5, columns 9-14).
    ellipsoid(bm, (0.0, ey(3.4), 0.27), (2.7 / 12, 1.7 / 12, 0.1), sides=14, rings=7, mat_index=DRUM)

    # Central column (columns 9-14, rows 8-17): a rounded spine with a groove at row 12.
    col = [(7.8, 2.6, 0.27), (8.4, 3.0, 0.33), (11.4, 3.0, 0.32), (12.0, 2.5, 0.29), (12.7, 2.5, 0.29),
           (13.3, 3.0, 0.31), (16.0, 2.9, 0.27), (17.4, 2.2, 0.2)]
    half_loft(bm, [(ey(r), w / 12, h, 0.0) for r, w, h in col], sides=10, power=2.6, mat_index=HOUSE)
    path_tube(bm, [(ex(9.3), ey(12.4), 0.27), (ex(12), ey(12.4), 0.3), (ex(14.7), ey(12.4), 0.27)],
              0.5 / 12, 0.03, sides=6, mat_index=GROOVE)

    # Dark drums either side of the column (rows 8-13, columns 4-7 and 16-19).
    for side in (-1, 1):
        ellipsoid(bm, (side * (12 - 6.0) / 12, ey(10.6), 0.2), (2.3 / 12, 2.7 / 12, 0.14),
                  sides=14, rings=8, mat_index=DRUM)

    # Glowing red core bulging out of the front (rows 18-26, columns 8-15).
    ellipsoid(bm, (0.0, ey(22.1), 0.07), (4.1 / 12, 4.3 / 12, 0.2), sides=16, rings=9, mat_index=CORE)
    # Its hot centre, up and left like the sprite's yellow highlight (rows 20-22, columns 10-13).
    ellipsoid(bm, (ex(11.3), ey(21.0), 0.2), (1.6 / 12, 1.5 / 12, 0.075), sides=10, rings=5, mat_index=HOT)

    # Nothing below the ground.
    for v in bm.verts:
        v.co.z = max(v.co.z, 0.0)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
