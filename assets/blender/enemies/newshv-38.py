"""newshv-38: the small green gem (newshv.shp size 1, frame 38, 12 x 14 px), rebuilt as
what it is (D65, D120, D122).

WHAT IT IS: a colour-coded crystal riding on the GEM WAR gunship's centre piece (types 805/806/804;
mv 0,1, armor 0, tur 131). It spawns at its host's x, 6 px up the screen (dat5 y -6), and link ev19
moves it with the host. The same pixels with the indices shifted are newshv-57 (red, host 797) and
newshv-19 (blue, host 807): one shape, recoloured (RAMPS below). newshv-57.py and newshv-19.py
call export('red') / export('blue') from this script, each to its own model path. It is NOT a ground object: it rides
high on the host's gem-launcher drum (assembly-newshv-91 blueprint: drum rows 7-14, top z 7.3 px),
held on a short mount whose ball foot sits on the drum.

Reading the sprite (row/col = sprite pixel, edges in px, z up):
- The gem: a rhombus 10 px wide (cols 1-10) and 9 px tall (rows 3-11), centre at column edge 6.0,
  row edge 7.5, one px per row each side (row widths 2 4 6 8 10 8 6 4 2). A faceted cut stone: the
  bright cross just right of centre (47 down col 6 and along row 7) is the sheen on the crown's
  ridges and table under a light from the upper right, the dark 40 ring is the shaded girdle edge,
  so neither is paint. The whole crown takes the gem's mid-tone 44 (trimmed median of its pixels).
- The mount: a 2 px stalk under the gem's south point (cols 5-6): a dark neck 39 (row 12) and a
  lighter ball foot 42 (row 13). In 3D a short collet clasps the south point and an inclined stem
  drops 2.6 px to the ball, which sits on the host's drum.

Shape: a rhombic brilliant. Crown: girdle -> steep (~50 deg) bezel/star ring (corner and side-mid points at different
scales, so the facets alternate kite and star) -> chamfered rhombic table. Pavilion: girdle -> a
break ring -> a pointed culet (a plausible closed underside; no detail). Facet edges get a tiny
chamfer so they catch glints. Glossy dielectric, no emission (the host's gem pods are not emissive
either). Outline shell (D51/D90/D118) from a sealed copy of the whole object.

    blender --background --python assets/blender/enemies/newshv-38.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshv-38"
W, H = 12, 14
PX = 1 / 12

# One shape in three colours: (gem crown, pavilion, girdle, neck, ball foot) per colour.
RAMPS = {
    "green": ("newshv-38", 44, 42, 40, 39, 42),
    "red": ("newshv-57", 76, 74, 72, 71, 74),
    "blue": ("newshv-19", 60, 58, 56, 55, 58),
}

# --- plan (px): rhombus half-extents and centre ----------------------------------------------------
A = 5.15          # half width (x), corners at columns ~0.85 / 11.15
B = 4.62          # half height (y)
CX, CY = 6.0, 7.5  # column edge, row edge

# --- heights (px) ----------------------------------------------------------------------------------
ZG = 9.6          # girdle mid-height: high enough that the pavilion clears the host's drum
GIRDLE = 0.26     # half thickness of the girdle band
Z_STAR = ZG + GIRDLE + 3.4    # steep outer bezels (~58 deg at the corners): the rim turns from the light
Z_TABLE = ZG + GIRDLE + 4.3   # shallower upper facets (~19 deg): the bright middle
Z_BREAK = ZG - GIRDLE - 2.3
Z_CULET = ZG - GIRDLE - 4.1
# crown rings: (corner scale, side-mid scale)
STAR = (0.62, 0.78)
TABLE = (0.16, 0.20)          # a small table: the bezels, not the table, take the sun
BREAK = (0.50, 0.40)
BEVEL = 0.06      # facet-edge chamfer

# mount: a peg plugged into the pavilion's south facets, running out under the south point to a
# ball foot (the sprite's dark neck at row 12, lighter knob at row 13)
P_IN = (9.4, ZG - GIRDLE - 1.9)     # (row edge, z) where the peg's socket meets the pavilion
Y_FOOT, Z_FOOT = 13.42, ZG - 2.75   # ball foot centre
R_STEM = 0.74
R_FOOT = (1.0, 0.72, 0.8)

def bl(x, y, z):
    """Sprite px (column edge, row edge, height) to Blender units."""
    return Vector(((x - W / 2) * PX, (H / 2 - y) * PX, z * PX))


def ring(bm, scales, z, grow=0.0):
    """8 points round the rhombus: corners E,N,W,S at even indices, side mid-points between."""
    sc, sm = scales
    pts = []
    corners = [(A, 0), (0, -B), (-A, 0), (0, B)]  # E, N (up the screen = smaller row), W, S
    for k in range(4):
        (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 4]
        pts.append((x0 * sc, y0 * sc))
        pts.append(((x0 + x1) / 2 * sm, (y0 + y1) / 2 * sm))
    return [bm.verts.new(bl(CX + x * (1 + grow), CY + y * (1 + grow), z)) for x, y in pts]


def band(bm, lo, hi, mat):
    """Triangles between two 8-rings (kite/star facets) or quads when both are similar."""
    n = len(lo)
    for i in range(n):
        j = (i + 1) % n
        if i % 2 == 0:  # corner -> mid
            tris = [(lo[i], lo[j], hi[j]), (lo[i], hi[j], hi[i])]
        else:  # mid -> corner
            tris = [(lo[i], lo[j], hi[i]), (lo[j], hi[j], hi[i])]
        for t in tris:
            bm.faces.new(t).material_index = mat


def gem(mats, coll, name=NAME):
    bm = bmesh.new()
    g_up = ring(bm, (1, 1), ZG + GIRDLE)
    g_lo = ring(bm, (1, 1), ZG - GIRDLE)
    star = ring(bm, STAR, Z_STAR)
    table = ring(bm, TABLE, Z_TABLE)
    brk = ring(bm, BREAK, Z_BREAK)
    culet = bm.verts.new(bl(CX, CY, Z_CULET))
    band(bm, g_up, star, 0)
    band(bm, star, table, 0)
    bm.faces.new(table).material_index = 0
    n = 8
    for i in range(n):  # girdle band
        j = (i + 1) % n
        bm.faces.new((g_lo[i], g_lo[j], g_up[j], g_up[i])).material_index = 2
    band(bm, brk, g_lo, 1)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((brk[j], brk[i], culet)).material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Merge the coplanar girdle quads per side, then chamfer every facet edge a hair.
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts, edges=bm.edges,
                             delimit={"MATERIAL"})
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=BEVEL * PX, offset_type="OFFSET", segments=1,
                    profile=0.5, affect="EDGES", clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return common.mesh_object(f"{name}_gem", bm, mats, coll, smooth=False)


def tube(bm, p0, p1, r0, r1, mat, sides=12, cap0=True, cap1=True):
    """A round tube from p0 to p1 (Blender coords) with radii r0 -> r1 (Blender units)."""
    axis = (p1 - p0).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u)
    rings = []
    for p, r in ((p0, r0), (p1, r1)):
        rings.append([bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r)
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for k in range(sides):
        m = (k + 1) % sides
        bm.faces.new((rings[0][k], rings[0][m], rings[1][m], rings[1][k])).material_index = mat
    if cap0:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
    if cap1:
        bm.faces.new(rings[1]).material_index = mat
    return rings


def ellipsoid(bm, c, r, mat, seg=14, rings=9):
    verts = []
    for i in range(1, rings):
        th = math.pi * i / rings
        verts.append([bm.verts.new(c + Vector((r[0] * math.sin(th) * math.cos(2 * math.pi * k / seg),
                                                  r[1] * math.sin(th) * math.sin(2 * math.pi * k / seg),
                                                  r[2] * math.cos(th)))) for k in range(seg)])
    top = bm.verts.new(c + Vector((0, 0, r[2])))
    bot = bm.verts.new(c - Vector((0, 0, r[2])))
    for k in range(seg):
        m = (k + 1) % seg
        bm.faces.new((top, verts[0][k], verts[0][m])).material_index = mat
        bm.faces.new((bot, verts[-1][m], verts[-1][k])).material_index = mat
        for i in range(len(verts) - 1):
            bm.faces.new((verts[i][k], verts[i + 1][k], verts[i + 1][m], verts[i][m])).material_index = mat


def mount(mats, coll, name=NAME):
    """Socket cup on the pavilion, a peg out under the south point, a machined collar, a ball foot."""
    bm = bmesh.new()
    NECK, FOOT = 3, 4
    p0 = bl(CX, P_IN[0], P_IN[1])
    p3 = bl(CX, Y_FOOT, Z_FOOT)
    d = (p3 - p0)
    ax = d.normalized()
    # socket: a short flared cup seated on the pavilion facets
    tube(bm, p0 - ax * 0.5 * PX, p0 + ax * 0.9 * PX, 1.05 * PX, 0.95 * PX, NECK, sides=16)
    tube(bm, p0 + ax * 0.9 * PX, p0 + ax * 1.2 * PX, 0.95 * PX, R_STEM * PX, NECK, sides=16)
    # the peg, with a collar ring two-thirds of the way out
    q1 = p0 + d * 0.66
    q2 = p0 + d * 0.76
    tube(bm, p0 + ax * 1.2 * PX, q1, R_STEM * PX, R_STEM * PX, NECK, sides=16)
    tube(bm, q1, q1 + ax * 0.12 * PX, R_STEM * PX, (R_STEM + 0.2) * PX, NECK, sides=16)
    tube(bm, q1 + ax * 0.12 * PX, q2 - ax * 0.12 * PX, (R_STEM + 0.2) * PX, (R_STEM + 0.2) * PX, NECK, sides=16)
    tube(bm, q2 - ax * 0.12 * PX, q2, (R_STEM + 0.2) * PX, R_STEM * 0.88 * PX, NECK, sides=16)
    tube(bm, q2, p3, R_STEM * 0.88 * PX, R_STEM * 0.88 * PX, NECK, sides=16)
    ellipsoid(bm, p3, tuple(r * PX for r in R_FOOT), FOOT, seg=16, rings=10)
    obj = common.mesh_object(f"{name}_mount", bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(40))
    return obj


def sealed_copy(objs, coll, name=NAME):
    """One mesh holding every part (world space), for the outline shell only."""
    bm = bmesh.new()
    for o in objs:
        tmp = o.data.copy()
        tmp.transform(o.matrix_world)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(f"{name}_seal")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"{name}_seal", me)
    coll.objects.link(obj)
    return obj


def build(colour="green"):
    name, crown, pav, gird, neck, foot = RAMPS[colour]
    sprite = common.load_sprite(WT, name)
    coll = common.reset_collection(name)
    # Glossy crown (roughness ~0.06) so the game sun makes the sprite's cross-shaped sparkle on
    # the crown ridges; the pavilion a touch softer.
    crown_glass = dict(metallic=0.0, roughness=0.06)
    gem_glass = dict(metallic=0.0, roughness=0.12)
    metal = dict(metallic=0.3, roughness=0.42)
    mats = [common.palette_material(sprite, crown, name, **crown_glass),
            common.palette_material(sprite, pav, f"{name}_pav", **gem_glass),
            common.palette_material(sprite, gird, name, metallic=0.0, roughness=0.2),
            common.palette_material(sprite, neck, f"{name}_metal", **metal),
            common.palette_material(sprite, foot, f"{name}_metal", **metal)]
    parts = [gem(mats, coll, name), mount(mats, coll, name)]
    seal = sealed_copy(parts, coll, name)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.01, faces=1200, smooth=5, inside=0.003)
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(seal, do_unlink=True)
    return parts, shell


def export(colour="green"):
    """Build the gem in one colour and export it to that colour's own model (enemies/<name>):
    green newshv-38, red newshv-57, blue newshv-19 (their scripts call this)."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    name = RAMPS[colour][0]
    parts, shell = build(colour)
    sprite = common.load_sprite(WT, name)
    common.export_sprite_model(WT, parts + [shell], f"enemies/{name}", sprite["sprites"])


def main():
    export("green")


if __name__ == "__main__":
    main()
