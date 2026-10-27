"""Helpers shared by batch b067's model scripts (newshp.shp ground structures and the brown turret).

Coordinates: a Grid maps sprite pixel edges to Blender units for a block of w x h px whose centre
is the origin: g.x(c) is the left edge of column c (g.x(c + 0.5) its centre), g.y(r) the top edge
of row r. Fractions are allowed. Sprite up is +Y, one pixel is 1/12 unit, ground objects stand on
z = 0.

Several b067 sprites (newshp-237, newshp-53 and the bottom of the newshp-191 stone block) sit on
the same baked-in ground: rubble stones, a lit ledge and a louvred apron falling away to a dark
trench. `terrain` builds that ground for one 24 x 28 tile pattern at any offset.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Grid:
    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        return (c - self.w / 2) / 12

    def y(self, r):
        return (self.h / 2 - r) / 12


class Mats:
    """Palette materials by index, added to the slot list on first use: m[9] is the slot of
    palette index 9 (stone defaults); m.add(i, ...) sets non-default properties first."""

    def __init__(self, sprite, tag, metallic=0.1, roughness=0.75):
        self.sprite, self.tag = sprite, tag
        self.list, self.slot = [], {}
        self.defaults = dict(metallic=metallic, roughness=roughness)

    def add(self, index, key=None, **kw):
        key = key or index
        if key not in self.slot:
            args = dict(self.defaults)
            args.update(kw)
            tag = self.tag if key == index else f"{self.tag}_{key}"
            self.list.append(common.palette_material(self.sprite, index, tag, **args))
            self.slot[key] = len(self.list) - 1
        return self.slot[key]

    def __getitem__(self, index):
        return self.add(index)


def _faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def set_smooth(bm, n, smooth=True):
    for f in _faces_since(bm, n):
        f.smooth = smooth


def frustum(bm, g, c0, r0, c1, r1, z0, z1, top, sides=None, inset=0.35, bottom=None):
    """A box over pixel edges [c0, c1) x [r0, r1) from z0 to z1 whose top is inset by `inset` px
    (a chunky stone or plate with bevelled sides). `sides` is (north, west, south, east)
    material slots (default: the top's), so lit and shaded faces can take the sprite's lit and
    shaded edge colours."""
    n_, w_, s_, e_ = sides or (top, top, top, top)
    i = inset
    xb0, xb1, yb0, yb1 = g.x(c0), g.x(c1), g.y(r1), g.y(r0)
    xt0, xt1, yt0, yt1 = g.x(c0 + i), g.x(c1 - i), g.y(r1 - i), g.y(r0 + i)
    b = [bm.verts.new(p) for p in ((xb0, yb0, z0), (xb1, yb0, z0), (xb1, yb1, z0), (xb0, yb1, z0))]
    t = [bm.verts.new(p) for p in ((xt0, yt0, z1), (xt1, yt0, z1), (xt1, yt1, z1), (xt0, yt1, z1))]
    bm.faces.new(t).material_index = top
    bm.faces.new(list(reversed(b))).material_index = top if bottom is None else bottom
    bm.faces.new((b[0], b[1], t[1], t[0])).material_index = s_  # south (-Y)
    bm.faces.new((b[1], b[2], t[2], t[1])).material_index = e_  # east (+X)
    bm.faces.new((b[2], b[3], t[3], t[2])).material_index = n_  # north (+Y)
    bm.faces.new((b[3], b[0], t[0], t[3])).material_index = w_  # west (-X)


def rounded_rect(g, c0, r0, c1, r1, radius, corners="nw ne se sw", segs=3):
    """Outline (counter-clockwise seen from above) of the pixel-edge rectangle [c0, c1) x [r0, r1)
    with the named corners rounded by `radius` px."""
    pts = []
    # corner centres in pixel coords and the angle range each sweeps (CCW in Blender = CW in rows)
    spec = [("sw", c0 + radius, r1 - radius, 180, 270, (c0, r1)),
            ("se", c1 - radius, r1 - radius, 270, 360, (c1, r1)),
            ("ne", c1 - radius, r0 + radius, 0, 90, (c1, r0)),
            ("nw", c0 + radius, r0 + radius, 90, 180, (c0, r0))]
    for name, cc, cr, a0, a1, sharp in spec:
        if name in corners.split() and radius > 0:
            for k in range(segs + 1):
                a = math.radians(a0 + (a1 - a0) * k / segs)
                pts.append((g.x(cc + radius * math.cos(a)), g.y(cr - radius * math.sin(a))))
        else:
            pts.append((g.x(sharp[0]), g.y(sharp[1])))
    return pts


def prism(bm, outline, z0, z1, mat, top=None):
    """Extrude a CCW outline from z0 to z1 (common.slab), with an optional different top."""
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    if top is not None:
        for f in _faces_since(bm, n):
            if f.normal.z > 0.9 or all(abs(v.co.z - z1) < 1e-6 for v in f.verts):
                f.material_index = top


def dome(bm, x, y, z0, rx, ry, rz, mat, segs=12, rings=4):
    """A half ellipsoid standing on z0 (radii in units), smooth shaded."""
    n = len(bm.faces)
    ring_verts = []
    for k in range(rings):
        phi = (math.pi / 2) * k / rings
        ring_verts.append([bm.verts.new((x + rx * math.cos(phi) * math.cos(2 * math.pi * j / segs),
                                         y + ry * math.cos(phi) * math.sin(2 * math.pi * j / segs),
                                         z0 + rz * math.sin(phi))) for j in range(segs)])
    apex = bm.verts.new((x, y, z0 + rz))
    for r0, r1 in zip(ring_verts, ring_verts[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
    for j in range(segs):
        bm.faces.new((ring_verts[-1][j], ring_verts[-1][(j + 1) % segs], apex))
    bm.faces.new(list(reversed(ring_verts[0])))
    for f in _faces_since(bm, n):
        f.material_index = mat
        f.smooth = True


def ring_loft(bm, rings, mat, cap_start=True, cap_end=True):
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = mat
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = mat
    return verts


def tube(bm, p0, p1, radius, sides=8, mat=0, caps=True, radius1=None):
    """A round bar between two 3D points (radius1 tapers it)."""
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for c, r in ((a, radius), (b, radius if radius1 is None else radius1)):
        rings.append([tuple(c + r * (math.cos(2 * math.pi * (i + 0.5) / sides) * u
                                     + math.sin(2 * math.pi * (i + 0.5) / sides) * v)) for i in range(sides)])
    n = len(bm.faces)
    ring_loft(bm, rings, mat, cap_start=caps, cap_end=caps)
    set_smooth(bm, n)


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth / flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# --- the shared ground ---------------------------------------------------------------------------

# Rubble stones of the 24 x 28 ground tile, from newshp-237 (whose rows 14-27 newshp-53 repeats and
# the stone block's bottom row continues): (c0, r0, c1, r1, height, top index, lit index, shade index),
# pixel edges, end exclusive.
LEFT_RUBBLE = [
    (0, 0, 3, 3, 0.07, 7, 8, 5), (0, 5, 4, 8, 0.07, 7, 8, 5), (0, 10, 3, 13, 0.08, 8, 10, 5),
    (0, 19, 4, 23, 0.06, 6, 8, 4), (0, 24, 3, 27, 0.08, 7, 10, 4), (4, 24, 7, 28, 0.08, 7, 10, 5),
]
RIGHT_RUBBLE = [  # columns relative to the tile's right part (237 columns 19-23 -> 0-4)
    (2, 0, 5, 3, 0.06, 6, 9, 4), (3, 5, 5, 8, 0.05, 5, 8, 3), (3, 14, 5, 18, 0.05, 5, 6, 3),
    (1, 19, 5, 23, 0.05, 5, 6, 3), (1, 24, 4, 27, 0.07, 7, 8, 3),
]
BOTTOM_RUBBLE = [  # columns relative to 237 column 8
    (0, 24, 3, 27, 0.05, 6, 7, 4), (4, 24, 7, 27, 0.05, 6, 8, 4), (8, 24, 11, 28, 0.06, 6, 8, 4),
]
LEDGE_STONE = (0, 14, 5, 17, 0.09, 8, 10, 5)  # the lit stone under the ledge's left end


def rubble(bm, g, m, stones, dc=0, dr=0):
    for c0, r0, c1, r1, h, top, lit, shade in stones:
        frustum(bm, g, c0 + dc, r0 + dr, c1 + dc, r1 + dr, 0.02, 0.02 + h, m[top],
                sides=(m[lit], m[lit], m[shade], m[shade]), inset=0.4)


def ground(bm, g, m, c0, r0, c1, r1):
    """The dark ground plate everything stands on."""
    frustum(bm, g, c0, r0, c1, r1, 0.0, 0.02, m[5], inset=0.0)


def trench(bm, g, m, c0, r0, c1, r1):
    """A strip of deep shadow on the ground (the dark trench beside the housing and apron)."""
    frustum(bm, g, c0, r0, c1, r1, 0.0, 0.023, m[2], inset=0.0)


def apron(bm, g, m, c0, c1, r0, ribs, wide_ribs=()):
    """The lit ledge along row r0 and the louvred apron below it (rows r0+1 .. r0+8), sloping from
    the ledge down to the ground, with raised slats: `ribs` are 1 px slat columns, `wide_ribs`
    (c, width, top index) wider ones."""
    # Ledge: a lit bar along the row.
    frustum(bm, g, c0, r0, c1, r0 + 1, 0.0, 0.11, m[8], sides=(m[10], m[9], m[6], m[6]), inset=0.15)
    # The apron: a wedge from z 0.1 at the ledge to the ground at r0 + 9.
    ytop, ybot = g.y(r0 + 1), g.y(r0 + 9)
    xa, xb = g.x(c0), g.x(c1)
    v = [bm.verts.new(p) for p in ((xa, ytop, 0.0), (xb, ytop, 0.0), (xb, ybot, 0.0), (xa, ybot, 0.0),
                                   (xa, ytop, 0.1), (xb, ytop, 0.1), (xb, ybot, 0.02), (xa, ybot, 0.02))]
    for f in ((v[4], v[7], v[6], v[5]), (v[0], v[1], v[2], v[3]), (v[0], v[4], v[5], v[1]),
              (v[3], v[2], v[6], v[7]), (v[0], v[3], v[7], v[4]), (v[1], v[5], v[6], v[2])):
        bm.faces.new(f).material_index = m[3]

    def slat(c, w, top):
        z = lambda r: 0.1 - 0.08 * (r - r0 - 1) / 8  # noqa: E731
        ya, yb = g.y(r0 + 1), g.y(r0 + 8.5)
        xl, xr = g.x(c), g.x(c + w)
        h = 0.035
        s = [bm.verts.new(p) for p in ((xl, ya, z(r0 + 1) - 0.01), (xr, ya, z(r0 + 1) - 0.01),
                                       (xr, yb, z(r0 + 8.5) - 0.01), (xl, yb, z(r0 + 8.5) - 0.01),
                                       (xl + 0.2 * PX, ya, z(r0 + 1) + h), (xr - 0.2 * PX, ya, z(r0 + 1) + h),
                                       (xr - 0.2 * PX, yb, z(r0 + 8.5) + h), (xl + 0.2 * PX, yb, z(r0 + 8.5) + h))]
        for f, mat in (((s[4], s[7], s[6], s[5]), top), ((s[0], s[1], s[2], s[3]), top),
                       ((s[0], s[4], s[5], s[1]), top), ((s[3], s[2], s[6], s[7]), top),
                       ((s[0], s[3], s[7], s[4]), m[7]), ((s[1], s[5], s[6], s[2]), m[2])):
            bm.faces.new(f).material_index = mat

    for c in ribs:
        slat(c, 1, m[4])
    for c, w, top in wide_ribs:
        slat(c, w, m[top])


def terrain(bm, g, m, dc=0, dr=0, extra=0, upper=True):
    """The ground of one 24 x 28 tile pattern (newshp-237's) with its top-left at pixel (dc, dr):
    the ground plate, the rubble down both sides and along the bottom, the lit ledge along row 14
    and the louvred apron under it. `extra` inserts that many more 4 px louvre periods (the tile
    gets 4 * extra px wider; the right part moves along). upper=False leaves out rows 0-13."""
    w = 24 + 4 * extra
    ground(bm, g, m, dc, dr + (0 if upper else 14), dc + w, dr + 28)
    keep = (lambda s: True) if upper else (lambda s: s[1] >= 14)  # noqa: E731
    rubble(bm, g, m, [s for s in LEFT_RUBBLE + [LEDGE_STONE] if keep(s)], dc, dr)
    rubble(bm, g, m, [s for s in RIGHT_RUBBLE if keep(s)], dc + 19 + 4 * extra, dr)
    for k in range(0, w, 24):  # the bottom rubble repeats every 24 px
        rubble(bm, g, m, BOTTOM_RUBBLE, dc + 8 + k, dr)
    r = dr + (2 if upper else 14)
    trench(bm, g, m, dc + 19.5 + 4 * extra, r, dc + 21 + 4 * extra, dr + 14)
    trench(bm, g, m, dc + 17 + 4 * extra, dr + 14, dc + 21 + 4 * extra, dr + 24)
    apron(bm, g, m, dc + 0, dc + 17 + 4 * extra, dr + 14, [dc + 16 + 4 * k for k in range(extra + 1)],
          wide_ribs=[(dc + 5, 4, 5), (dc + 10, 3, 4)])


def plate_with_hole(bm, outer, inner, z0, z1, top, wall, inner_wall, lit=None, shade=None, bevel=0.0):
    """A plate between an outer and an inner outline (both counter-clockwise, in units), from z0 up
    to z1: the top filled between them, walls round both. With `bevel` (units) the top's outer
    edge is chamfered down by that much, the chamfer lit (`lit`) on its north and west faces and
    shaded (`shade`) on the others."""
    def ring(pts, z):
        return [bm.verts.new((x, y, z)) for x, y in pts]

    def walls(lo, hi, mat_fn):
        n = len(lo)
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
            f.material_index = mat_fn(f)

    def by_dir(f):
        f.normal_update()
        nx, ny = f.normal.x, f.normal.y
        return lit if (ny - nx) > 0.2 else shade

    if bevel:
        cx = sum(x for x, _ in outer) / len(outer)
        cy = sum(y for _, y in outer) / len(outer)
        top_outer = [(x - math.copysign(bevel, x - cx), y - math.copysign(bevel, y - cy)) for x, y in outer]
    else:
        top_outer = outer
    ob = ring(outer, z0)
    if bevel:
        om = ring(outer, z1 - bevel)
        ot = ring(top_outer, z1)
        walls(ob, om, lambda f: wall)
        walls(om, ot, by_dir if lit is not None else (lambda f: wall))
    else:
        ot = ring(outer, z1)
        walls(ob, ot, lambda f: wall)
    ib = ring(inner, z0)
    it = ring(inner, z1)
    walls(it, ib, lambda f: inner_wall)
    edges = []
    for loop in (ot, it):
        for i in range(len(loop)):
            edges.append(bm.edges.get((loop[i], loop[(i + 1) % len(loop)])) or
                         bm.edges.new((loop[i], loop[(i + 1) % len(loop)])))
    res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=True, edges=edges)
    for f in res["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.material_index = top


def housing(bm, g, m, dc=0, dr=0, z1=0.3):
    """newshp-237's (and newshp-53's) rounded stone housing: columns 3-18, rows 0-13 of the tile,
    a thick rim round a square well (columns 7-16, rows 2-11) whose floor is dark. Its top is
    lit along the left and top edges like the sprite's. The well's contents are up to the caller."""
    outer = rounded_rect(g, dc + 3, dr + 0, dc + 19, dr + 14, 2.2, segs=3)
    inner = [(g.x(dc + 7), g.y(dr + 12)), (g.x(dc + 17), g.y(dr + 12)), (g.x(dc + 17), g.y(dr + 2)),
             (g.x(dc + 7), g.y(dr + 2))]
    plate_with_hole(bm, outer, inner, 0.0, z1, m[9], m[7], m[5], lit=m[12], shade=m[6], bevel=0.05)
    frustum(bm, g, dc + 7, dr + 2, dc + 17, dr + 12, 0.0, 0.12, m[3], inset=0.0)  # well floor


# --- running -------------------------------------------------------------------------------------

def frame_image(root, name, sprite, sprites):
    """The reference image of the first frame a model covers."""
    want = (sprites[0]["sheet"], sprites[0]["frames"][0])
    for f in sprite["frames"]:
        if (f["sheet"], f["index"]) == want:
            return root / "reference" / "models" / name / f["image"]
    return None


def subset(sprite, keep):
    """sprite['sprites'] cut down to the frames in `keep` (a set of (sheet, index))."""
    out = []
    for s in sprite["sprites"]:
        frames = [f for f in s["frames"] if (s["sheet"], f) in keep]
        if frames:
            out.append({**s, "frames": frames})
    return out


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview each: the first to <png>,
    the others to <model>.png beside it; -- --frames <png> renders every frame of each the same
    way (common.render_frame_previews). `build(sprite)` returns [(model, objects, sprites)]."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        size = sprite["frames"][0]["size"]
        for i, (model, objects, sprites) in enumerate(models):
            path = out if i == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(path), frame_image(root, name, sprite, sprites), size=size)
    if "--frames" in sys.argv:
        # Every frame of each animated model, one row per frame: <png>, then <model>-frames.png.
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for i, (model, objects, sprites) in enumerate(models):
            keep = {(s["sheet"], f) for s in sprites for f in s["frames"]}
            frames = [f for f in sprite["frames"] if (f["sheet"], f["index"]) in keep]
            path = out if i == 0 else out.parent / f"{model}-frames.png"
            common.render_frame_previews(objects, str(path), {**sprite, "frames": frames}, root)
    return sprite
