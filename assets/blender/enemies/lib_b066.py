"""Helpers shared by batch b066 (the two horns of the level 2.12 dragon, newsh0-7 and newsh0-9).

Each horn is a curved, tapering spike traced row by row from its sprite: every row's filled
extent (outline pixels left out) becomes one ring of a loft whose centre follows the curve, and
the darker groove running down the lower half becomes a sunken strip along the top.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

OUTLINE = 1


def loft_x(bm, sections, sides=10, mat_index=0, cap_start=True, cap_end=True):
    """Like common.loft, but each section is (y, x_centre, half_width, half_height, z_centre), so
    the loft can follow a curve in X. A zero-size section is a point (a tip)."""
    rings = []
    for y, x, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ring.append(bm.verts.new((x + w * math.cos(a), y, z + h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def row_extents(pixels):
    """{row: (left edge, right edge)} in sprite pixel units of each row's filled, non-outline pixels."""
    out = {}
    for r, line in enumerate(pixels):
        cols = [c for c, v in enumerate(line) if v not in (-1, OUTLINE)]
        if cols:
            out[r] = (min(cols), max(cols) + 1)
    return out


def smooth(values, passes=1):
    v = list(values)
    for _ in range(passes):
        v = [v[0]] + [(v[i - 1] + 2 * v[i] + v[i + 1]) / 4 for i in range(1, len(v) - 1)] + [v[-1]]
    return v


def build_horn(name, sprite, groove_col, groove_from):
    """One horn as a mesh object. groove_col: the sprite column of the dark groove, which runs from
    row groove_from to the bottom of the tile."""
    import bmesh

    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(56, metallic=0.35, roughness=0.4),  # 0 horn blue
        pal(53, metallic=0.3, roughness=0.55),  # 1 dark groove
    ]
    HORN, GROOVE = range(2)
    pixels = sprite["frames"][0]["pixels"]
    h_px, w_px = len(pixels), len(pixels[0])
    X = lambda c: (c - w_px / 2) / 12  # noqa: E731  (c is a pixel edge)
    Y = lambda r: (h_px / 2 - r) / 12  # noqa: E731  (r is a pixel edge)

    ext = row_extents(pixels)
    rows = sorted(ext)
    lefts = smooth([ext[r][0] for r in rows], passes=4)
    rights = smooth([ext[r][1] for r in rows], passes=4)
    first, last = rows[0], rows[-1]

    def z_centre(r):
        # The tip curls up a little out of the screen.
        t = (last + 1 - r) / (last + 1 - first)
        return 0.06 * t * t

    sections = []
    # The tip: half a pixel above the first filled row, leaning into the outline's point.
    sections.append((Y(first - 0.4), X((lefts[0] + rights[0]) / 2 + 0.3), 0.0, 0.0, z_centre(first - 0.4)))
    profile = []
    for r, lft, rgt in zip(rows, lefts, rights):
        yc = r + 0.5 if r != last else last + 1.0  # the base runs to the tile's edge, into the body below
        w = (rgt - lft) / 2
        # Round near the tip, a little flattened at the wide base.
        h = min(w * 0.85, 2.3)
        cx = (lft + rgt) / 2
        sections.append((Y(yc), X(cx), w / 12, h / 12, z_centre(yc)))
        profile.append((r, cx, w, h, z_centre(yc)))
    bm = bmesh.new()
    loft_x(bm, sections, sides=10, mat_index=HORN, cap_end=True)

    # The groove: a dark strip sunk into the top surface along groove_col.
    gx = groove_col + 0.5
    groove = []
    for r, cx, w, h, zc in profile:
        if r < groove_from:
            continue
        d = min(abs(gx - cx) / w, 0.95) if w else 0.95
        ztop = zc / 1.0 + h / 12 * math.sqrt(1 - d * d)
        yc = r + 0.5 if r != last else last + 1.0
        groove.append((Y(yc), X(gx), 0.6 / 12, 0.4 / 12, ztop - 0.12 / 12))
    if groove:
        y0, x0, _, _, z0 = groove[0]
        groove.insert(0, (y0 + 0.6 / 12, x0, 0.0, 0.0, z0 - 0.15 / 12))
        loft_x(bm, groove, sides=6, mat_index=GROOVE)

    return common.mesh_object(name, bm, mats, coll, smooth=True)


def run(name, script_file, groove_col, groove_from):
    root = common.repo_root(script_file)
    sprite = common.load_sprite(root, name)
    obj = build_horn(name, sprite, groove_col, groove_from)
    common.export_sprite_model(root, [obj], f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = root / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
