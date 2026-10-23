"""Helpers shared by batch b003's enemy models (newshv.shp, level 2.15 and friends).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b003 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    """Sprite column (pixel centre) to Blender X, for a sprite `w` px wide."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre) to Blender Y (sprite up is +Y), for a sprite `h` px tall."""
    return (h / 2 - (r + 0.5)) / 12


def ex(e, w=24):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (h / 2 - e) / 12


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def rotate_z(bm, start, angle, cx=0.0, cy=0.0):
    """Rotate every vertex added since `start` by `angle` radians about the vertical through (cx, cy)."""
    bm.verts.ensure_lookup_table()
    c, s = math.cos(angle), math.sin(angle)
    for v in bm.verts[start:]:
        x, y = v.co.x - cx, v.co.y - cy
        v.co.x, v.co.y = cx + x * c - y * s, cy + x * s + y * c


def loft_x(bm, sections, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along +X instead of +Y: sections are (x, half_depth_y, half_height, z)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x, v.co.y = v.co.y, v.co.x


def ellipsoid(bm, centre, radii, sides=16, rings=8, mat_index=0):
    """An ellipsoid (radii rx, ry, rz) at `centre`, lofted along Y."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    sections = [(-ry, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        a = math.pi * i / rings
        t = -math.cos(a)
        f = math.sin(a)
        sections.append((ry * t, rx * f, rz * f, 0.0))
    sections.append((ry, 0.0, 0.0, 0.0))
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index)
    move(bm, start, cx, cy, cz)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an XY outline from z0 up to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box."""
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat_index)


def rings_solid(bm, centre, rings, sides=4, angle=0.0, mat_bottom=0):
    """Concentric rings joined into a stepped, pyramid-like solid.

    `rings` go from the outside in: (radius, z, mat_index). Ring i and ring i+1 are joined by a band
    with ring i+1's material; a last ring of radius 0 is an apex. With sides=4 and angle=0 the rings
    are diamonds with corners on the X and Y axes. The outermost ring is closed underneath."""
    cx, cy = centre
    verts = []
    for r, z, _ in rings:
        if r == 0:
            verts.append([bm.verts.new((cx, cy, z))])
            continue
        ring = []
        for i in range(sides):
            a = angle + 2 * math.pi * i / sides
            ring.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)))
        verts.append(ring)
    bm.faces.new(list(reversed(verts[0]))).material_index = mat_bottom
    for k in range(len(verts) - 1):
        r0, r1 = verts[k], verts[k + 1]
        m = rings[k + 1][2]
        for i in range(sides):
            j = (i + 1) % sides
            if len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(f).material_index = m
    if len(verts[-1]) > 1:
        bm.faces.new(verts[-1]).material_index = rings[-1][2]


def mirror_x(bm, start, end=None):
    """Duplicate the geometry built between vertex index `start` and `end` (default: now) mirrored in
    X, keeping each face's material. Faces are copied whole, so only use this on geometry whose faces
    all lie within that vertex range."""
    bm.verts.ensure_lookup_table()
    end = len(bm.verts) if end is None else end
    src = set(bm.verts[start:end])
    copies = {}
    for v in list(src):
        copies[v] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
    for f in [f for f in bm.faces if all(v in src for v in f.verts)]:
        nf = bm.faces.new([copies[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth


def preview(objects, root, name, sprite):
    """Render the preview if the script was run with `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objects, out, ref, size=sprite["frames"][0]["size"])


# --- The faceted disc (newshv-153 blue, newshv-123 red) ------------------------------------------

def gem_disc(sprite, name, offset):
    """A round domed disc with a stepped diamond on top: an outer bright diamond ridge, a dark groove
    and a bright pyramid in the middle (newshv.shp 153/155/157 in blues 48-63; 123/125/127 are the
    same in reds, `offset` 16). The frames only dim the whole thing, so one model covers them."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i + offset, name, **kw)  # noqa: E731
    mats = [
        pal(58, metallic=0.4, roughness=0.35),  # 0 disc body
        pal(60, metallic=0.5, roughness=0.3),  # 1 bright diamond ridge
        pal(54, metallic=0.4, roughness=0.5),  # 2 dark groove
        pal(61, metallic=0.45, roughness=0.25),  # 3 bright centre pyramid
        pal(63, emission_strength=2.0),  # 4 glowing tip
        pal(55, metallic=0.4, roughness=0.45),  # 5 darker underside rim
    ]
    BODY, RIDGE, GROOVE, CENTRE, TIP, RIM = range(6)
    import bmesh

    # The disc: columns 4-19, rows 6-21 inside the outline, centred on the origin. Smooth shaded.
    bm = bmesh.new()
    r = 8.3 / 12
    ellipsoid(bm, (0.0, 0.0, 0.0), (r, r, 0.15), sides=28, rings=12, mat_index=BODY)
    disc = common.mesh_object(name, bm, mats, coll, smooth=True)

    # The stepped diamond, faceted (L1 radii in px measured from the sprite: ridge 7, groove 5.3,
    # centre 4).
    bm = bmesh.new()
    u = 1 / 12
    rings_solid(bm, (0.0, 0.0), [
        (7.6 * u, 0.06, RIDGE),
        (6.9 * u, 0.165, RIDGE),
        (6.1 * u, 0.165, RIDGE),
        (5.4 * u, 0.135, GROOVE),
        (4.6 * u, 0.135, GROOVE),
        (3.9 * u, 0.175, CENTRE),
        (1.2 * u, 0.27, CENTRE),
        (0.0, 0.29, TIP),
    ], sides=4, mat_bottom=RIDGE)
    diamond = common.mesh_object(f"{name}_diamond", bm, mats, coll, smooth=False)
    return [disc, diamond]
