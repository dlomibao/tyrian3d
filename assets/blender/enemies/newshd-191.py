"""Ice lance (newshd.shp frame 191): a 3D version of its sprite.

What it is (checked in the game data and in level 1.1 at tick 2920): enemy type 463, launched
every 40 ticks by the brown caged turret newshd-275 (type 271) and the type-86 launcher, and flying
straight down the screen (yMove 4, armour 80, no explosion). So it is a shot: a long six-sided ice
crystal fired point first, its broken rear end split into three icy splinters trailing up the screen
(the longest on the left). Seen in levels 1.1, 1.2, 1.3, 2.4, 3.1 and 3.2. One frame, one model.

Reading the sprite (24 x 28, palette 5's ice ramp 58-63, no ink border: the edge stays at the
sprite's outer edge, D74 rule 2):
- body: columns 8-14 (7 px) from row 5 to row 25, then a crystal point: 5 px on row 26, 3 px on
  row 27, the tip at row 28. Bands across it are facets: col 8 / 14 the steep outer facets (58 /
  59-60: the same facet, the left in shadow), col 9 / 13 the top bevels (61), cols 10-12 the flat top
  face (63, near white, from row 13 down; the bright core).
- rear (rows 4-12): the top face splits into three ridges (cols 9, 11, 13, bright) with two dark
  cracks between them (cols 10 and 12) that close up by row 13; at the very end the body is notched
  at col 10 (rows 4-5 empty).
- splinters: col 9 up to row 0 (the longest), col 13 up to row 1, col 11 up to row 3, and a little
  shard at col 14 rows 4-7.

How it is built: hard, faceted crystal. One loft of a chamfered 14-sided section (flat bottom,
short vertical chines, steep outer facets, top bevels, flat top) along the sprite, pchip stations;
the rear top face carries two V cracks whose depth runs out (pchip) by row 13, and the rear end is a
broken face notched at col 10. A two-ring crystal termination makes the point. Splinters are
tapered diamond-section shards rooted inside the body. Colours by facet band (palette indices, so
palettes, fades and the hit flash apply). Underside: a flat closed bottom, no detail.

Run: blender --background --python assets/blender/enemies/newshd-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshd-191"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Sprite px -> Blender units: x = column edge - 12, y = row edge (down the sprite), z up.
U = 1 / 12


def V(x, y, z):
    return (x * U, (14 - y) * U, z * U)


CX = -0.5  # body centre line: columns 8-14 -> edges 8..15, centre at edge 11.5

# The body section, relative to CX, in px: (x, z). Flat bottom, short vertical chines, steep outer
# facets (col 8/14), top bevels (col 9/13), a flat top (cols 10-12) with four extra vertices where
# the rear cracks open (x = +-1.0 the crack floors, +-0.4 the middle ridge's shoulders).
PROFILE = [(-2.2, 0.35), (2.2, 0.35), (3.5, 1.7), (3.5, 2.5), (2.5, 4.1), (1.5, 4.75),
           (1.0, 4.75), (0.4, 4.95), (-0.4, 4.95), (-1.0, 4.75), (-1.5, 4.75), (-2.5, 4.1),
           (-3.5, 2.5), (-3.5, 1.7)]
CRACK_FLOOR = {6, 9}  # indices whose z drops by the crack depth
CHAMFER = 0.09  # px
ZC = 2.55  # the termination's axis height
# Band (profile edge k -> k+1) colours: bottom, lower facets, chines, outer facets, top bevels, top.
BOTTOM, LOWER, CHINE, OUTER, BEVEL, TOP = range(6)
EDGE_BAND = [BOTTOM, LOWER, CHINE, OUTER, BEVEL, TOP, TOP, TOP, TOP, TOP, BEVEL, OUTER, CHINE, LOWER]


def crack_depth():
    """Depth (px) of the two V cracks in the rear top face, by row: deep at the broken end, closed by row 13."""
    return T.pchip([4.0, 5.0, 9.0, 13.0, 30.0], [1.7, 1.6, 0.85, 0.0, 0.0])


def build_body(bm, M):
    depth = crack_depth()
    # Stations (row, scale about the termination axis). Full section to row 25.6, then the point.
    rows = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.5, 17.0, 20.0, 23.0, 25.6, 27.0]
    scale = {27.0: 0.57}
    rings = []
    for r in rows:
        s = scale.get(r, 1.0)
        d = depth(r)
        ring = []
        for k, (x, z) in enumerate(PROFILE):
            zz = z - (d if k in CRACK_FLOOR else 0.0)
            y = r
            if r == rows[0]:
                # The broken end: notched at col 10 (rows 4-5 empty there), a little ragged elsewhere.
                y = {9: 6.7, 8: 5.35, 10: 5.4, 6: 5.25, 7: 5.0}.get(k, 5.0)
                if k in (2, 3):
                    y = 4.6  # the right flank runs a bit further (col 14 row 4)
            ring.append(bm.verts.new(V(CX + x * s, y, ZC + (zz - ZC) * s)))
        rings.append(ring)
    tip = bm.verts.new(V(CX, 28.25, ZC))
    n = len(PROFILE)
    faces = []
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            faces.append((f, EDGE_BAND[k], rows[i], rows[i + 1]))
    for k in range(n):
        j = (k + 1) % n
        f = bm.faces.new((rings[-1][k], rings[-1][j], tip))
        faces.append((f, EDGE_BAND[k], 27.0, 28.25))
    cap = bm.faces.new(list(reversed(rings[0])))
    # Colours: the sprite's own index per band and region.
    for f, band, y0, y1 in faces:
        nose = y0 >= 25.5
        if band == TOP:
            if nose:
                mat = M["p61"]
            elif y0 >= 13.0:
                mat = M["p63"]
            else:
                mat = M["p62"]
        elif band == BEVEL:
            mat = M["p61"] if not nose else M["p60"]
        elif band == OUTER:
            mat = M["p59"]
        elif band == CHINE:
            mat = M["p59"]
        elif band == LOWER:
            mat = M["p58"]
        else:
            mat = M["p58"]
        f.material_index = mat
        f.smooth = False
    # Crack walls in the rear: darker (depth, cols 10 and 12 at rows 4-12).
    for f, band, y0, y1 in faces:
        if band == TOP and y1 <= 13.0:
            xs = [(v.co.x / U - CX) for v in f.verts]
            if min(abs(x) for x in xs) < 1.05 and max(abs(x) for x in xs) > 0.95:
                ax = sum(abs(x) for x in xs) / len(xs)
                if 0.45 < ax < 1.45:
                    f.material_index = M["p60"]
    cap.material_index = M["p61"]
    cap.smooth = False


def shard(bm, path, mat_top, mat_low, M):
    """A tapered diamond-section ice splinter along `path`: [(x, row, zc, half width, half height)]."""
    rings = []
    for x, r, zc, hw, hh in path:
        rings.append([bm.verts.new(V(x + dx, r, zc + dz)) for dx, dz in ((hw, 0), (0, hh), (-hw, 0), (0, -hh))])
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(4):
            j = (k + 1) % 4
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            # The first segment is the splinter's dark tip (rows 0-1 of col 9: 58, 59; row 3 of col 11: 58).
            top = M["p59"] if i == 0 else mat_top
            f.material_index = top if k in (0, 1) else mat_low
            f.smooth = False
    # The splinter's broken tip: a small chisel face; the root is closed inside the body.
    t = bm.faces.new(rings[0])
    t.material_index = M["p59"]
    b = bm.faces.new(list(reversed(rings[-1])))
    b.material_index = mat_low


def build(sprite, coll):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    order = [58, 59, 60, 61, 62, 63]
    mats = []
    for i in order:
        if i == 63:
            mats.append(pal(i, metallic=0.05, roughness=0.22, emission_strength=0.0))
        else:
            mats.append(pal(i, metallic=0.08, roughness=0.3))
    M = {f"p{i}": k for k, i in enumerate(order)}
    bm = bmesh.new()
    build_body(bm, M)
    # Splinters, tip first (row edge), rooted in the body at row 7-8.
    # Left, the longest: col 9 up to row 0 (row 0 itself is its dark tip).
    shard(bm, [(-2.5, -0.15, 3.3, 0.36, 0.3), (-2.5, 1.5, 3.55, 0.5, 0.55), (-2.5, 4.0, 3.75, 0.8, 0.95),
               (-2.45, 5.5, 3.75, 0.95, 1.1), (-2.4, 8.0, 3.6, 1.0, 1.1)], M["p62"], M["p60"], M)
    # Middle: col 11 to row 3, widening to cols 11-12 at row 4.
    shard(bm, [(-0.5, 2.85, 4.0, 0.36, 0.3), (-0.25, 4.0, 4.25, 0.75, 0.6), (-0.05, 5.4, 4.3, 0.95, 0.75),
               (0.0, 8.0, 4.1, 0.9, 0.7)], M["p60"], M["p59"], M)
    # Right: col 13 to row 1.
    shard(bm, [(1.5, 0.85, 3.4, 0.36, 0.3), (1.5, 2.5, 3.65, 0.5, 0.55), (1.55, 4.2, 3.85, 0.8, 0.9),
               (1.6, 5.5, 3.9, 0.95, 1.0), (1.6, 8.0, 3.7, 1.0, 1.0)], M["p62"], M["p60"], M)
    # A low shard on the right flank: col 14, rows 4-7.
    shard(bm, [(2.55, 3.95, 2.7, 0.4, 0.35), (2.6, 5.0, 2.9, 0.6, 0.7), (2.5, 7.5, 2.8, 0.7, 0.8)],
          M["p59"], M["p58"], M)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Chamfer every crisp crystal edge a little, so the edges catch the light (hard surface, D50).
    edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > math.radians(22)]
    bmesh.ops.bevel(bm, geom=edges, offset=CHAMFER * U, segments=1, affect="EDGES", profile=0.5,
                    clamp_overlap=True)
    for f in bm.faces:
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    out = preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
