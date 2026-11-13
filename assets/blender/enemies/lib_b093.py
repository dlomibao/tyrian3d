"""Helpers shared by the FLEET capital ship's three model scripts (build-models.sh skips lib_ modules):
assembly-newsho-79 (the blue upper hull), assembly-newsho-156 (the lower hull and its two gun arms)
and assembly-newsho-191 (the three deck hatches). They are one flying ship (all spawn on tick 5020,
same link, rigid), so they share one hard-surface kit: plan-coordinate chamfered slabs, ring lofts,
swept tubes, domes, the D90/D118 outline shell from a sealed pre-cull copy sunk under the creases
(D185) and split open per piece, and a review render.

Coordinates are sprite pixel *edges* (c, r) of an assembly: column c runs from c to c + 1, row r from
r to r + 1. A Builder turns them into Blender units about its origin (oc, orow) in the same pixel-edge
coordinates (1 px = 1/12 unit, sprite up = +Y); z is in units.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


# --------------------------------------------------------------------------------------------------
# Materials: the sprite's own palette index per region; satin metal; D176 F0 via Specular IOR Level
# --------------------------------------------------------------------------------------------------

def merged_colors(root, names):
    cols = {}
    for n in names:
        cols.update(common.load_sprite(root, n)["colors"])
    return cols


class Mats:
    """pal_<index> materials, one per (index, metallic, roughness, spec) key, in slot order."""

    def __init__(self, root, names, name, tag):
        self.sprite = {"name": name, "colors": merged_colors(root, names)}
        self.tag = tag
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.45, roughness=0.42, spec=0.6):
        key = (index, metallic, roughness, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"{self.tag}{len(self.list)}", metallic=metallic,
                                        roughness=roughness)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if spec is not None and "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Plan geometry
# --------------------------------------------------------------------------------------------------

def area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def inset(pts, d):
    """Offset a closed polygon inward by d (scalar or one value per edge i -> i+1), mitred."""
    n = len(pts)
    ds = d if isinstance(d, (list, tuple)) else [d] * n
    s = 1.0 if area(pts) > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1) or 1, math.hypot(*e2) or 1
        u1, u2 = (e1[0] / l1, e1[1] / l1), (e2[0] / l2, e2[1] / l2)
        n1 = (-u1[1] * s, u1[0] * s)
        n2 = (-u2[1] * s, u2[0] * s)
        d1, d2 = ds[i - 1], ds[i]
        a = (p1[0] + n1[0] * d1, p1[1] + n1[1] * d1)
        b = (p1[0] + n2[0] * d2, p1[1] + n2[1] * d2)
        den = u1[0] * u2[1] - u1[1] * u2[0]
        if abs(den) < 1e-6:
            out.append(a)
            continue
        t = ((b[0] - a[0]) * u2[1] - (b[1] - a[1]) * u2[0]) / den
        q = (a[0] + u1[0] * t, a[1] + u1[1] * t)
        lim = 3.0 * max(abs(d1), abs(d2), 1e-6)
        if math.hypot(q[0] - p1[0], q[1] - p1[1]) > lim:
            k = lim / math.hypot(q[0] - p1[0], q[1] - p1[1])
            q = (p1[0] + (q[0] - p1[0]) * k, p1[1] + (q[1] - p1[1]) * k)
        out.append(q)
    return out


def fillet(corners, radius, k=3):
    """Round each corner of a closed polygon (usp_talon.fillet, copied: radius may be per corner)."""
    n = len(corners)
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * n
    out = []
    for i in range(n):
        p0, p1, p2 = corners[i - 1], corners[i], corners[(i + 1) % n]
        if radii[i] <= 0:
            out.append(p1)
            continue
        d1 = (p0[0] - p1[0], p0[1] - p1[1])
        d2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*d1), math.hypot(*d2)
        d1 = (d1[0] / l1, d1[1] / l1)
        d2 = (d2[0] / l2, d2[1] / l2)
        ang = math.acos(max(-0.999, min(0.999, d1[0] * d2[0] + d1[1] * d2[1])))
        t = min(radii[i] / math.tan(ang / 2), 0.45 * l1, 0.45 * l2)
        a = (p1[0] + d1[0] * t, p1[1] + d1[1] * t)
        b = (p1[0] + d2[0] * t, p1[1] + d2[1] * t)
        for j in range(k + 1):
            u = j / k
            out.append(((1 - u) ** 2 * a[0] + 2 * u * (1 - u) * p1[0] + u * u * b[0],
                        (1 - u) ** 2 * a[1] + 2 * u * (1 - u) * p1[1] + u * u * b[1]))
    return out


def pchip(xs, ys):
    """Monotone cubic through (xs, ys) (usp_talon.pchip, copied)."""
    import bisect
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = min(bisect.bisect_right(xs, x) - 1, n - 2)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def earclip(pts):
    """Triangles (index triples, the polygon's own winding) of a simple polygon in 2D."""
    n = len(pts)
    idx = list(range(n))
    a2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1.0 if a2 > 0 else -1.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return (cross(a, b, p) * sgn >= -1e-12 and cross(b, c, p) * sgn >= -1e-12 and cross(c, a, p) * sgn >= -1e-12)

    tris, guard = [], 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        best = None
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            cr = cross(a, b, c) * sgn
            if cr <= 1e-12:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)
                   and pts[j] != a and pts[j] != b and pts[j] != c):
                continue
            best = k
            break
        if best is None:  # only degenerate ears left: drop a collinear vertex
            for k in range(m):
                i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
                if abs(cross(pts[i0], pts[i1], pts[i2])) <= 1e-9:
                    idx.pop(k)
                    break
            else:
                break
            continue
        k = best
        tris.append((idx[k - 1], idx[k], idx[(k + 1) % len(idx)]))
        idx.pop(k)
    if len(idx) == 3 and abs(cross(pts[idx[0]], pts[idx[1]], pts[idx[2]])) > 1e-12:
        tris.append(tuple(idx))
    return tris


def mirror_full(left, ax):
    """A symmetric closed outline from its left half (top centre -> west -> bottom centre)."""
    right = [(2 * ax - c, r) for c, r in reversed(left)]
    if abs(left[-1][0] - ax) < 1e-6:
        right = right[1:]
    if abs(left[0][0] - ax) < 1e-6:
        right = right[:-1]
    return left + right


class Builder:
    """bmesh builder in plan pixel coordinates about the origin (oc, orow); `mir` mirrors about column
    edge `ax` (winding is fixed at the end by recalc_face_normals, every part being a closed solid)."""

    def __init__(self, oc, orow, ax):
        self.bm = bmesh.new()
        self.mir = False
        self.oc, self.orow, self.ax = oc, orow, ax

    def xy(self, c, r):
        if self.mir:
            c = 2 * self.ax - c
        return ((c - self.oc) * PX, (self.orow - r) * PX)

    def v(self, c, r, z):
        x, y = self.xy(c, r)
        return self.bm.verts.new((x, y, z))

    def face(self, vs, mat, smooth=False):
        f = self.bm.faces.new(vs)
        f.material_index = mat
        f.smooth = smooth
        return f

    def cap(self, vs, mat, smooth=False, plan=False):
        """A cap face; plan caps (horizontal-ish, possibly concave) are ear-clipped in XY here, since
        bmesh's ear clip bridged the deck's notches."""
        if len(vs) <= 4 or not plan:
            f = self.face(vs, mat, smooth)
            if len(vs) > 4:
                bmesh.ops.triangulate(self.bm, faces=[f], quad_method="BEAUTY", ngon_method="EAR_CLIP")
            return
        for tri in earclip([(v.co.x, v.co.y) for v in vs]):
            self.face([vs[i] for i in tri], mat, smooth)

    def rings(self, rings, side, top=None, bottom=None, smooth=False):
        """A closed solid through rings of (c, r, z) with the same count, bottom to top. side is a
        material index or fn(ring_segment, edge) -> index."""
        loops = [[self.v(*p) for p in ring] for ring in rings]
        n = len(loops[0])
        for k, (l0, l1) in enumerate(zip(loops, loops[1:])):
            for i in range(n):
                j = (i + 1) % n
                m = side(k, i) if callable(side) else side
                self.face((l0[i], l0[j], l1[j], l1[i]), m, smooth)
        self.cap(loops[-1], top if top is not None else (side(0, 0) if callable(side) else side), smooth, plan=True)
        self.cap(list(reversed(loops[0])), bottom if bottom is not None else (side(0, 0) if callable(side) else side),
                 smooth, plan=True)

    def slab(self, poly, z0, z1, top, side, ch=0.7, chz=0.05, bevel=None, zf=None, top_poly=None):
        """A prism from z0 to z1 with a chamfered top edge (inset ch px over chz units). zf(c, r) -> top z
        tilts the top (planar when linear). top_poly overrides the inset top ring (same count)."""
        zt = (lambda c, r: z1) if zf is None else zf
        tp = top_poly or inset(poly, ch)
        rings = [[(c, r, z0) for c, r in poly],
                 [(c, r, zt(c, r) - chz) for c, r in poly],
                 [(c, r, zt(c, r)) for c, r in tp]]
        bm = bevel if bevel is not None else side
        self.rings(rings, lambda k, i: side if k == 0 else bm, top=top)

    def box(self, c0, r0, c1, r1, z0, z1, top, side, ch=0.5, chz=0.04):
        self.slab([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, top, side, ch=ch, chz=chz)

    def sweep(self, path, sides=10, mat=0, power=1.0, cap0=True, cap1=True, smooth=True, up=None):
        """A tube along (c, r, z, half_width_px, half_height_units); zero size = a point end. The path
        runs in plan; `up` = True makes it a vertical path instead (rings flat, half_width in px both
        ways), for posts and drums."""
        pos = [self.xy(c, r) for c, r, *_ in path]
        rings = []
        for i, (c, r, z, hw, hh) in enumerate(path):
            x, y = pos[i]
            if hw == 0 and hh == 0:
                rings.append([self.bm.verts.new((x, y, z))])
                continue
            ring = []
            if up:
                for k in range(sides):
                    a = 2 * math.pi * (k + 0.5) / sides
                    ring.append(self.bm.verts.new((x + hw * PX * math.cos(a), y + hw * PX * math.sin(a), z)))
                rings.append(ring)
                continue
            (x0, y0), (x1, y1) = pos[max(i - 1, 0)], pos[min(i + 1, len(pos) - 1)]
            dx, dy = x1 - x0, y1 - y0
            d = math.hypot(dx, dy) or 1
            nx, ny = -dy / d, dx / d
            for k in range(sides):
                a = 2 * math.pi * (k + 0.5) / sides
                cu, su = math.cos(a), math.sin(a)
                u = math.copysign(abs(cu) ** power, cu)
                w = math.copysign(abs(su) ** power, su)
                ring.append(self.bm.verts.new((x + nx * hw * PX * u, y + ny * hw * PX * u, z + hh * w)))
            rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(sides):
                j = (k + 1) % sides
                if len(r0) == 1:
                    self.face((r0[0], r1[j], r1[k]), mat, smooth)
                elif len(r1) == 1:
                    self.face((r0[k], r0[j], r1[0]), mat, smooth)
                else:
                    self.face((r0[k], r0[j], r1[j], r1[k]), mat, smooth)
        if cap0 and len(rings[0]) > 1:
            self.cap(list(reversed(rings[0])), mat, False)
        if cap1 and len(rings[-1]) > 1:
            self.cap(rings[-1], mat, False)

    def ellipsoid(self, c, r, z, rx, ry, rz, mat, seg=16, rings=8, upper=True, smooth=True):
        """An ellipsoid (rx, ry px; rz units); upper: the top half on a flat base at z."""
        lo = 0 if upper else -rings // 2 + 1
        loops = []
        for k in range(lo, rings // 2):
            t = (math.pi / 2) * k / (rings // 2)
            loops.append([self.v(c + rx * math.cos(t) * math.cos(a), r - ry * math.cos(t) * math.sin(a),
                                 z + rz * math.sin(t))
                          for a in (2 * math.pi * i / seg for i in range(seg))])
        tip = self.v(c, r, z + rz)
        for l0, l1 in zip(loops, loops[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                self.face((l0[i], l0[j], l1[j], l1[i]), mat, smooth)
        for i in range(seg):
            self.face((loops[-1][i], loops[-1][(i + 1) % seg], tip), mat, smooth)
        if upper:
            self.cap(list(reversed(loops[0])), mat)
        else:
            bot = self.v(c, r, z - rz)
            for i in range(seg):
                self.face((loops[0][(i + 1) % seg], loops[0][i], bot), mat, smooth)

    def to_object(self, name, mats, coll):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        return obj


# --------------------------------------------------------------------------------------------------
# Pieces, shell
# --------------------------------------------------------------------------------------------------

def layout(root, pieces, cx0, cy0):
    """The pieces' centres from the first piece's sprite.json assemblyLayout, relative to (cx0, cy0)."""
    lay = common.load_sprite(root, pieces[0])["assemblyLayout"]
    return [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in lay if e["model"] in pieces]


def split_open(obj, lay, coll, suffix):
    """split_assembly without capping the cuts (for the outline shell: no ink along the seams)."""
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        for m in obj.data.materials:
            me.materials.append(m)
        o["tyrian_outline"] = True
        out[name] = o
    return out


def sink_shell(shell, model, margin, reach):
    """D185 (newshv-10.py's sink_shell, copied): drop every shell vertex to `margin` under the lowest
    model top within `reach` seen from above, so the smoothed shell can't stand over the creases (ink
    on the silhouette only). x, y untouched: the silhouette and its ink stay."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    moved = 0
    for v in shell.data.vertices:
        w = shell.matrix_world @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = shell.matrix_world.inverted() @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def flatten_cut_faces(piece):
    """The faces split_assembly fills along a piece's box edges shade flat (no crease at the seams)."""
    hx, hy, eps = 1.0, 14 / 12, 1e-4
    me = piece.data
    for p in me.polygons:
        cos = [me.vertices[i].co for i in p.vertices]
        on_x = all(abs(abs(c.x) - hx) < eps for c in cos)
        on_y = all(abs(abs(c.y) - hy) < eps for c in cos)
        if on_x or on_y:
            p.use_smooth = False


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def shell_and_split(obj, lay, coll, voxel=0.02, faces=3500, inside=0.006, margin=0.012, reach=0.06):
    """D90/D118: one outline shell for the whole object from a sealed copy, sunk under the creases
    (D185), split open per piece (no ink along the seams); and the pieces themselves
    (common.split_assembly, cut faces flat). Returns (pieces, shells) as {name: object}."""
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=voxel, faces=faces, inside=inside)
    bpy.data.objects.remove(sealed, do_unlink=True)
    sink_shell(shell, obj, margin, reach)
    shells = split_open(shell, lay, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for s in shells.values():
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.data.shade_smooth()
    shell.hide_render = True
    pieces = common.split_assembly(obj, lay, coll)
    for p in pieces.values():
        flatten_cut_faces(p)
    return pieces, shells


def place(pieces, shells, lay):
    """Put the exported pieces back at their assembly offsets (for scratch renders)."""
    for name, dx, dy in lay:
        for o in (pieces[name], shells.get(name)):
            if o is not None:
                o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------------------------------
# Review renders (scratch only): top mask / lit at k px per sprite px, game-camera tilts, 3/4s
# --------------------------------------------------------------------------------------------------

def review(shells, out, w_px, h_px, quick=False, zc=0.2, dist=19.0, k=8, stats=None, centre=(0.0, 0.0)):
    """Renders of whatever is visible (hide the rest first). The top views are w_px x h_px sprite px
    at k image px each, centred on `centre` (Blender XY)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if stats is not None:
        (out / "stats.json").write_text(json.dumps(stats))
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    sh = scene.display.shading
    eng = None
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng = e
            break
        except TypeError:
            pass
    if "rev_sun" not in bpy.data.objects:  # once per run (review may be called per frame)
        sun_d = bpy.data.lights.new("rev_sun", "SUN")
        sun_d.energy = 3.2
        sun = bpy.data.objects.new("rev_sun", sun_d)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    bgn = next(n for n in nt.nodes if n.type == "BACKGROUND")
    # A sky gradient (bright above, dark below) so glossy surfaces show their sheen as in game.
    for n in [n for n in nt.nodes if n.type in ("TEX_COORD", "SEPXYZ", "SEPARATE_XYZ", "VALTORGB")]:
        nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs[2], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[0].color = (0.015, 0.015, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.80
    ramp.color_ramp.elements[1].color = (0.13, 0.14, 0.16, 1)
    nt.links.new(ramp.outputs[0], bgn.inputs[0])
    bgn.inputs[1].default_value = 3.0
    cx, cy = centre

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600, rot=None):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot if rot else (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False, show_shell=False):
        for s in shells:
            s.hide_render = not show_shell
        if not flat and eng:
            scene.render.engine = eng
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh.light = "FLAT"
            sh.color_type = "MATERIAL"
            sh.show_cavity = False
            sh.show_object_outline = False
            sh.show_specular_highlight = False
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    big = max(w_px, h_px * 1.5) / 12
    cam("top", (cx, cy, 40), (cx, cy, 0), ortho=max(w_px, h_px) / 12, rx=w_px * k, ry=h_px * k, rot=(0, 0, 0))
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_lit.png")
    if quick:
        return
    shot(out / "top_shell.png", show_shell=True)
    for nm, loc, orth, rx, ry in (("side_w", (cx - 60, cy, zc), big * 0.55, 1100, 420),
                                  ("front_s", (cx, cy - 60, zc), big * 1.05, 1400, 400),
                                  ("rear_n", (cx, cy + 60, zc), big * 1.05, 1400, 400)):
        cam(nm, loc, (cx, cy, zc), ortho=orth, rx=rx, ry=ry)
        shot(out / f"{nm}.png")
    ctr = Vector((cx, cy, zc))
    for nm, az, el in (("q_sw", -40, 30), ("q_ne", 150, 30), ("q_high", 20, 55)):
        a, e = math.radians(az), math.radians(el)
        cam(nm, ctr + Vector((dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a), dist * math.sin(e))),
            ctr, lens=50, rx=1200, ry=800)
        shot(out / f"{nm}.png", show_shell=True)
    for nm, tdeg in (("game", 28), ("game15", 15)):
        t = math.radians(tdeg)
        cam(nm, ctr + Vector((0, -dist * 1.1 * math.sin(t), dist * 1.1 * math.cos(t))), ctr, lens=50, rx=1200, ry=700)
        shot(out / f"{nm}.png", show_shell=True)
    t = math.radians(28)
    cam("game_small", ctr + Vector((0, -dist * 2.6 * math.sin(t), dist * 2.6 * math.cos(t))), ctr, lens=50, rx=420,
        ry=240)
    shot(out / "game_small.png", show_shell=True)
    cam("under", (cx, cy, -40), (cx, cy, 0), ortho=max(w_px, h_px) / 12 * 1.05, rx=w_px * 5, ry=h_px * 6,
        rot=(math.pi, 0, 0))
    shot(out / "under.png")
