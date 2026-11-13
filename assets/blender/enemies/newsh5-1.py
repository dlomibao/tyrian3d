"""Purple crystal arrowhead (newsh5.shp frame 1), a 3D version of its sprite.

Seen in episode 4 (HARVEST, level 4.12): drifts down the screen in numbers, pointing up. What it is,
built as such: a cut purple crystal arrowhead set in a dark red machined U mount.

- The crystal: a step-cut gem lofted down the screen in flat facets. A pointed head (rows 0-11)
  widening to the full sprite width, with a straight barb edge at row 11 whose underside is a
  swept-back facet, then a narrower shank (columns 8-16) tapering to a point at row 19. Each side
  has an outer facet and an inner facet next to the ridge (the sprite's 88 outer band and 89/90
  inner band on its lit left side; the dark right half is the same facets in shade, art rule 2), a
  small chamfer on the girdle edge and a plain keel underneath.
- The mount: a U band (the sprite's dark red 241-247 ring, palette 242 at its median) whose arms run
  up columns 6 and 18 under the barbs and whose crescent fills rows 18-22. Its section: a raised lip
  where it grips the crystal, a satin crown, a machined groove along the outer half, a rounded
  outer edge, flat bottom.
- The gold: a satin bronze bead rib along the crown of the crescent (the sprite's gold arc,
  palette 248 at its median; its 250-251 pixels are sheen) with a domed stud at the bottom centre.

    blender --background --python assets/blender/enemies/newsh5-1.py [-- --preview out.png]

Exports public/models/enemies/newsh5-1.glb (mesh + outline shell, pal_<index> materials) and
src/render/spriteModels/newsh5-1.json.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsh5-1"
P = 1 / 12  # one sprite pixel
W, H = 24, 28
AXE = 12.5  # mirror axis, a pixel edge coordinate (the middle of column 12)


def X(hw, side=1):
    """Half width in sprite px from the axis (side -1 = left) to Blender X."""
    return (AXE + side * hw - W / 2) * P


def Y(e):
    """Row edge to Blender Y (row 0 is the top of the screen, +Y)."""
    return (H / 2 - e) * P


# --- Crystal -------------------------------------------------------------------------------------

# Stations down the screen: (row edge, half width px, ridge z, keel z). Flat facets between them.
HEAD = [(0.65, 0.0, 0.015, 0.004), (1.5, 0.55, 0.06, 0.02), (5.6, 4.7, 0.29, 0.09), (6.5, 6.6, 0.34, 0.105),
        (7.1, 7.5, 0.37, 0.11), (9.5, 7.5, 0.41, 0.12), (12.0, 7.5, 0.42, 0.12)]
SHANK = [(13.0, 4.5, 0.39, 0.11), (14.6, 4.5, 0.35, 0.10), (17.0, 2.2, 0.24, 0.06), (19.3, 0.0, 0.13, 0.02)]


SHOULDER = T.pchip([0.65, 6.5, 12.0, 13.0, 19.3], [0.40, 0.42, 0.58, 0.64, 0.64])


def gem_ring(y, hw, zt, zb):
    """One closed section of the gem, counter-clockwise seen from -Y... order: left girdle round the
    top to the right girdle, then round the keel. Points in sprite px (x) and units (z)."""
    e = min(0.012, zt * 0.25)  # girdle chamfer
    fs = SHOULDER(y) * hw  # the shoulder line diverges from the ridge down the head (the lit inner facet widens)
    fb = hw - min(1.0, 0.16 * hw)  # the girdle bevel stays about a pixel wide
    top = [(-hw, e), (-fb, 0.30 * zt), (-fs, 0.82 * zt), (0.0, zt),
           (fs, 0.82 * zt), (fb, 0.30 * zt), (hw, e)]
    bot = [(hw, -e), (0.5 * hw, -0.7 * zb), (0.0, -zb), (-0.5 * hw, -0.7 * zb), (-hw, -e)]
    return [(X(x, 1) if x >= 0 else X(-x, -1), Y(y), z) for x, z in top + bot]


def loft_rings(bm, rings, mat, smooth=False, cap0=True, cap1=True):
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    faces = []
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            faces.append(f)
    if cap0:
        faces.append(bm.faces.new(list(reversed(vs[0]))))
    if cap1:
        faces.append(bm.faces.new(vs[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return vs


def build_crystal(bm, mat):
    rings = [gem_ring(y, max(hw, 0.04), zt, zb) for y, hw, zt, zb in HEAD + SHANK]
    vs = loft_rings(bm, rings, mat, cap0=False, cap1=False)
    # Points: collapse the first and last rings to pole vertices.
    for ring, (y, hw, zt, zb) in ((vs[0], HEAD[0]), (vs[-1], SHANK[-1])):
        c = Vector((X(0), Y(y), (zt - zb) * 0.3))
        for v in ring:
            v.co = c
    bmesh.ops.remove_doubles(bm, verts=vs[0] + vs[-1], dist=1e-6)


# --- Mount (the U band) --------------------------------------------------------------------------

INNER = [(4.3, 11.9), (4.3, 14.7), (3.35, 15.75), (2.35, 16.75), (1.35, 17.75), (0.45, 18.7), (0.0, 19.05)]
OUTER = [(6.5, 11.9), (6.5, 17.0), (6.25, 18.2), (5.65, 19.55), (4.75, 20.65), (3.55, 21.6), (2.25, 22.35),
         (1.05, 22.8), (0.0, 22.95)]
N_HALF = 30
Z_BOT = -0.05


def resample(pts, n):
    """n+1 points evenly spaced by arc length along the polyline."""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.dist(a, b))
    out = []
    for i in range(n + 1):
        s = d[-1] * i / n
        k = max(j for j in range(len(d) - 1) if d[j] <= s + 1e-9) if s < d[-1] else len(d) - 2
        t = (s - d[k]) / (d[k + 1] - d[k])
        out.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t))
    return out


def band_stations():
    """(inner (hw signed, y), outer (hw signed, y), crown z) from the left arm's top round to the right's."""
    li, lo = resample(INNER, N_HALF), resample(OUTER, N_HALF)
    st = [((-a[0], a[1]), (-b[0], b[1])) for a, b in zip(li, lo)]
    st += [((a[0], a[1]), (b[0], b[1])) for a, b in reversed(list(zip(li, lo))[:-1])]
    crown = T.pchip([0.0, 0.25, 0.5, 0.75, 1.0], [0.105, 0.125, 0.135, 0.125, 0.105])
    m = len(st) - 1
    return [(i_, o_, crown(k / m)) for k, (i_, o_) in enumerate(st)]


def band_profile(zc, groove=True):
    """(u across the band from the gripping lip to the outer edge, z) over the top."""
    g = 0.012 if groove else 0.0
    return [(0.0, 0.03), (0.05, zc * 0.86), (0.16, zc), (0.56, zc), (0.59, zc - g), (0.69, zc - g), (0.72, zc),
            (0.86, zc * 0.96), (0.95, zc * 0.78), (1.0, zc * 0.45)]


def pt(hw_y, z):
    hw, y = hw_y
    return (X(abs(hw), 1 if hw >= 0 else -1), Y(y), z)


def build_band(bm, mat, groove=True):
    rings = []
    for (ih, iy), (oh, oy), zc in band_stations():
        top = [pt((ih + (oh - ih) * u, iy + (oy - iy) * u), z) for u, z in band_profile(zc, groove)]
        rings.append(top + [pt((oh, oy), Z_BOT), pt((ih, iy), Z_BOT)])
    loft_rings(bm, rings, mat, smooth=True)


def band_z(st, hw, y):
    """The band's top z under a point (hw signed, y): u along the nearest inner-outer station segment."""
    best = None
    for (ih, iy), (oh, oy), zc in st:
        dx, dy = oh - ih, oy - iy
        L2 = dx * dx + dy * dy
        u = max(0.0, min(1.0, ((hw - ih) * dx + (y - iy) * dy) / L2))
        d = math.hypot(ih + dx * u - hw, iy + dy * u - y)
        if best is None or d < best[0]:
            best = (d, u, zc)
    _, u, zc = best
    prof = band_profile(zc)
    for (u0, z0), (u1, z1) in zip(prof, prof[1:]):
        if u0 <= u <= u1:
            return z0 + (z1 - z0) * (u - u0) / (u1 - u0)
    return zc


def build_gold(bm, mat):
    """The bead rib along the crown of the crescent, and the domed stud at the bottom centre."""
    st = band_stations()
    # The sprite's gold arc: up the left arm from row 17, round the crescent at row 20.5, mirrored.
    half = [(5.15, 16.9), (4.75, 18.0), (3.85, 19.25), (2.6, 20.15), (1.2, 20.6), (0.0, 20.72)]
    half = resample(half, 12)
    pts = [(-hw, y) for hw, y in half] + [(hw, y) for hw, y in reversed(half[:-1])]
    path = [(hw, y, band_z(st, hw, y)) for hw, y in pts]
    n = len(path)
    r0 = 0.68 * P
    sides = 10
    rings = []
    for k, (hw, y, zc) in enumerate(path):
        # tangent in the plane
        a = path[max(k - 1, 0)]
        b = path[min(k + 1, n - 1)]
        tx, ty = (b[0] - a[0]), -(b[1] - a[1])
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln  # in-plane normal (Blender XY)
        taper = min(1.0, k / 3.0, (n - 1 - k) / 3.0)
        r = r0 * (0.35 + 0.65 * math.sqrt(max(taper, 0.0)))
        c = Vector(pt((hw, y), zc - 0.15 * r))
        ring = []
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            ring.append(c + Vector((nx, ny, 0)) * math.cos(ang) * r + Vector((0, 0, 1)) * math.sin(ang) * r * 0.9)
        rings.append(ring)
    loft_rings(bm, rings, mat, smooth=True)
    # The stud: a low dome on a seating ring, at the bottom centre of the rib.
    c = Vector(pt((0.0, 20.72), band_z(st, 0.0, 20.72) - 0.003))
    prof = [(0.0, 0.0), (1.05, 0.0), (1.05, 0.12), (0.95, 0.22), (0.88, 0.45), (0.72, 0.72), (0.45, 0.92), (0.0, 1.0)]
    R, Hh = 1.0 * P, 0.62 * P
    seg = 20
    rr = []
    for rad, h in prof:
        if rad == 0:
            rr.append([c + Vector((0, 0, h * Hh))])
        else:
            rr.append([c + Vector((math.cos(2 * math.pi * s / seg) * rad * R, math.sin(2 * math.pi * s / seg) * rad * R,
                                   h * Hh)) for s in range(seg)])
    vs = [[bm.verts.new(p) for p in r] for r in rr]
    for a, b in zip(vs, vs[1:]):
        for s in range(seg):
            j = (s + 1) % seg
            if len(a) == 1:
                f = bm.faces.new((a[0], b[s], b[j]))
            elif len(b) == 1:
                f = bm.faces.new((a[s], a[j], b[0]))
            else:
                f = bm.faces.new((a[s], a[j], b[j], b[s]))
            f.material_index = mat
            f.smooth = True


def build(sprite, coll, proxy=False):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.5, roughness=0.24),  # 0 purple crystal (glossy cut faces)
        pal(242, metallic=0.55, roughness=0.42),  # 1 dark red satin mount (sprite region median 242)
        pal(248, metallic=0.75, roughness=0.38),  # 2 satin bronze bead and stud (region median 248)
    ]
    CRYSTAL, MOUNT, GOLD = range(3)
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.7 if m is mats[0] else 0.5
    bm = bmesh.new()
    build_crystal(bm, CRYSTAL)
    build_band(bm, MOUNT, groove=not proxy)
    if not proxy:
        build_gold(bm, GOLD)
    return common.mesh_object(NAME, bm, mats, coll, smooth=None)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    proxy = build(sprite, coll, proxy=True)
    proxy.name = "proxy"
    shell = common.outline_shell(proxy, coll, voxel=0.006, faces=2500, smooth=2, inside=0.003, islands="outer")
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    obj = build(sprite, coll)
    assert obj.name == NAME and shell.name == f"{NAME}_outline", (obj.name, shell.name)
    assert len(shell.data.polygons) > 0
    for o in (obj, shell):
        o["design_model"] = NAME
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"tris {tris} shell faces {len(shell.data.polygons)}")
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = WT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj, shell], out, ref, size=sprite["frames"][0]["size"], frame=sprite["frames"][0]["index"])


if __name__ == "__main__":
    main()
