"""Blue crystal (newsh7.shp frames 53, 91, 129): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4. A rounded blue gem, egg-shaped from above,
with a steel drum cap at the top: a smooth dome about 9.5 px tall with
the sprite's pale seams riding on it as beads (the table line down the left and across the
bottom, the front edge, the right rim, the cross bar at row 12), and a dark canopy cut into its
upper centre. The gem is one glossy mid-tone blue (the sprite's patchwork is its drawn light), the
canopy a deeper blue, the cap polished steel. The frames only shimmer
the blues and the white seams: every blue is one palette step darker on frame 91 and two on 129,
and the white lines fade (143, 142, 140), so one model covers them all with per-frame colours
(common.palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh7-53.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
from lib_b007 import common, ex, ey  # noqa: E402

NAME = "newsh7-53"
PX = 1 / 12

# The gem's outline in pixel-edge coordinates (column, row), including the sprite's dark outline
# pixels, cut diagonally through the staircase corners so the egg follows the sprite.
OUTLINE = [(4.5, 7), (19.5, 7), (20.5, 8), (21.5, 9), (22, 10), (22, 19), (21.5, 20), (20.5, 21),
           (16, 25.5), (15.5, 26), (8.5, 26), (8, 25.5), (3.5, 21), (2.5, 20), (2, 19), (2, 10),
           (2.5, 9), (3.5, 8)]
CENTRE = (12.0, 15.0)  # the dome's crown, in pixel coordinates
# The dome: a smooth curve to the crown at H px (PROFILE_P < 2 rounds the crown off, no plateau).
# Round the rim (the sprite's dark outline pixels) runs the dark setting, a ledge ZR px up from
# the outline (scale 1) in to S_LEDGE; from there the gem's steep blue flank rises to S_IN, where
# the per-pixel dome begins.
ZR, H, PROFILE_P = 1.0, 9.5, 1.7
S_LEDGE, S_IN = 0.915, 0.9


def ray_scale(p):
    """How far point p (pixel coordinates) is from the crown towards the outline (0 to 1)."""
    cx, cy = CENTRE
    dx, dy = p[0] - cx, p[1] - cy
    if abs(dx) + abs(dy) < 1e-9:
        return 0.0
    best = None
    for i, a in enumerate(OUTLINE):
        b = OUTLINE[(i + 1) % len(OUTLINE)]
        ex_, ey_ = b[0] - a[0], b[1] - a[1]
        den = dx * ey_ - dy * ex_
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - cx) * ey_ - (a[1] - cy) * ex_) / den  # along the ray
        u = ((a[0] - cx) * dy - (a[1] - cy) * dx) / den    # along the edge
        if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return 1.0 / best if best else 1.0


def profile(s):
    """Dome height (px) at ray scale s (0 at the crown, 1 at the outline)."""
    s = min(max(s, 0.0), 1.0)
    return ZR + (H - ZR) * math.sqrt(max(0.0, 1 - s ** PROFILE_P))


def dome_z(p):
    """Height (px) of the dome's surface at pixel point p."""
    return profile(min(ray_scale(p), S_IN))


def inside(p):
    """Whether pixel point p is inside the outline polygon."""
    x, y = p
    hit = False
    for i, a in enumerate(OUTLINE):
        b = OUTLINE[(i + 1) % len(OUTLINE)]
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            hit = not hit
    return hit


def world(p, z_px):
    return (ex(p[0]), ey(p[1]), z_px * PX)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    pixels = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in sprite["frames"][0]["pixels"]]

    def shimmer(i, tag="shimmer", **kw):
        """A gem blue that steps one palette index darker on each later frame."""
        return common.palette_material(sprite, i, f"{NAME}-{tag}", frames={91: i - 1, 129: i - 2}, **kw)

    def at(c, r):
        c, r = int(math.floor(c)), int(math.floor(r))
        return pixels[r][c] if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]) else -1

    # The gem's materials: the sprite's own colours, a few neighbouring blues merged. Each pixel of
    # the dome takes the colour the sprite shows there, so the top view is the sprite's.
    gem_mats = [
        pal(1, metallic=0.4, roughness=0.4),                                          # 0 dark setting
        common.palette_material(sprite, 140, f"{NAME}-gem", frames={91: 159, 129: 158}, metallic=0.0,
                                roughness=0.1, emission_strength=0.5),                # 1 pale seam
        common.palette_material(sprite, 143, f"{NAME}-gem", frames={91: 142, 129: 140}, metallic=0.0,
                                roughness=0.1, emission_strength=0.5),                # 2 white seam
    ]
    GROUPS = {148: (144, 145, 146, 147, 148, 149), 150: (150, 151), 152: (152,), 153: (153,),
              155: (154, 155), 157: (156, 157), 159: (158, 159)}
    mat_of = {1: 0, 48: 0, 49: 0, 140: 1, 142: 2, 143: 2}
    for idx, members in GROUPS.items():
        for m in members:
            mat_of[m] = len(gem_mats)
        gem_mats.append(shimmer(idx, tag="gem", metallic=0.05, roughness=0.12))
    # The gem is glass-like: one mid-tone blue for the whole body (the sprite's lighter and darker
    # blue patches and the white glints between its seams are its drawn shading and sheen; the
    # game's light and the glossy material make those), the cut-in canopy a deeper blue. The pale
    # seams are the beads below, not paint, and the sprite's black outline ring is not painted on
    # either: the game draws the outline.
    BODY, DEEP = mat_of[155], mat_of[150]
    WALL = DEEP

    # The dome: a heightfield with one quad per sprite pixel inside the dark outline (rows 7-25;
    # the cap covers rows 2-6). Its border vertices are slid onto the outline polygon scaled to
    # S_IN, so its edge is a clean egg, not a staircase; the flank, the setting's ledge, a 1 px
    # vertical lip and a shallow pavilion run round it.
    cells = [(c, r) for r in range(7, 26) for c in range(1, 23)
             if inside((c + 0.5, r + 0.5)) and at(c, r) != 1]
    cellset = set(cells)
    # The canopy: the dark band in the upper centre (rows 8-11, columns 7-15), cut 1.75 px into the
    # dome between the table line on the left and the cross bar below.
    canopy = {(c, r) for c in range(7, 16) for r in range(8, 12)}
    CUT = 1.75
    edge_use = {}
    for c, r in cells:
        for e in (((c, r), (c + 1, r)), ((c + 1, r), (c + 1, r + 1)),
                  ((c + 1, r + 1), (c, r + 1)), ((c, r + 1), (c, r))):
            k = tuple(sorted(e))
            edge_use[k] = edge_use.get(k, 0) + 1
    border = {v for k, n in edge_use.items() if n == 1 for v in k}

    def on_ring(v, k):
        """Point v slid along its ray from the crown onto the outline scaled by k."""
        s = ray_scale(v)
        return (CENTRE[0] + (v[0] - CENTRE[0]) * k / s, CENTRE[1] + (v[1] - CENTRE[1]) * k / s)

    def pos2d(v):
        return on_ring(v, S_IN) if v in border else v

    bm = bmesh.new()
    verts = {}

    def vert(v, low=False):
        key = (v, low)
        if key not in verts:
            p2 = pos2d(v)
            z = dome_z(p2)
            verts[key] = bm.verts.new(world(p2, z - (CUT if low else 0.0)))
        return verts[key]

    part = []  # each face's part, in creation order: crisp edges go between parts

    def add(vs, mat, kind):
        bm.faces.new(vs).material_index = mat
        part.append(kind)

    for c, r in cells:
        low = (c, r) in canopy
        corners = [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]
        add([vert(v, low) for v in corners], DEEP if low else BODY, "floor" if low else "dome")
    # The canopy's walls, where a cut pixel meets an uncut one.
    for c, r in canopy:
        for (dc, dr), (a, b) in (((0, -1), ((c, r), (c + 1, r))), ((1, 0), ((c + 1, r), (c + 1, r + 1))),
                                 ((0, 1), ((c + 1, r + 1), (c, r + 1))), ((-1, 0), ((c, r + 1), (c, r)))):
            if (c + dc, r + dr) in cellset and (c + dc, r + dr) not in canopy:
                add([vert(b), vert(a), vert(a, True), vert(b, True)], WALL, "wall")
    # The flank, the ledge, the lip and the pavilion, in the border's order round the outline.
    nxt = {}
    for c, r in cells:
        corners = [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            if edge_use[tuple(sorted((a, b)))] == 1:
                nxt[a] = b
    start = next(iter(nxt))
    loop = [start]
    while nxt[loop[-1]] != start:
        loop.append(nxt[loop[-1]])
    top = [vert(v) for v in loop]
    ledge = [bm.verts.new(world(on_ring(v, S_LEDGE), ZR + 0.2)) for v in loop]
    rim = [bm.verts.new(world(on_ring(v, 1.0), ZR)) for v in loop]
    foot = [bm.verts.new(world(on_ring(v, 1.0), 0.0)) for v in loop]

    keel = bm.verts.new(world((CENTRE[0], CENTRE[1] + 1.5), -2.5))
    for i in range(len(loop)):
        j = (i + 1) % len(loop)
        add([top[j], top[i], ledge[i], ledge[j]], BODY, "flank")
        add([ledge[j], ledge[i], rim[i], rim[j]], BODY, "ledge")
        add([rim[j], rim[i], foot[i], foot[j]], BODY, "lip")
        add([foot[j], foot[i], keel], BODY, "keel")
    gem = common.mesh_object(NAME, bm, gem_mats, coll, smooth=True)
    bm = bmesh.new()
    bm.from_mesh(gem.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.tag = False
    smooth_as = {"flank": "dome"}  # the flank rolls smoothly into the dome
    grp = [smooth_as.get(k, k) for k in part]
    crisp = [e for e in bm.edges if len(e.link_faces) == 2
             and grp[e.link_faces[0].index] != grp[e.link_faces[1].index]]
    bmesh.ops.split_edges(bm, edges=crisp)
    bm.to_mesh(gem.data)
    bm.free()

    # Pale seams as beads riding on the dome (pixel-centre coordinates of the sprite's white lines).
    line_mats = [
        common.palette_material(sprite, 143, f"{NAME}-shimmer", emission_strength=2.5, metallic=0.0,
                                roughness=0.1, frames={91: 142, 129: 140}),  # white seams, fading
        shimmer(159, metallic=0.0, roughness=0.1),  # the cross bar's pale-blue middle
    ]
    seams = [
        ([(5.5, 7.4), (5.5, 15.5), (9.5, 19.6), (10.2, 20.5), (15.5, 20.5), (15.5, 25.2)], 0),  # table, front edge
        ([(15.5, 20.5), (17.5, 17.5), (17.5, 12.5)], 0),                                       # right table line
        ([(20.6, 8.9), (20.6, 18.6)], 0),                           # right rim
        ([(20.6, 17.5), (17.5, 17.5)], 0),
        ([(3.1, 12.5), (5.5, 12.5)], 0),                                                        # cross bar ends
        ([(17.5, 12.5), (20.9, 12.5)], 0),
        ([(5.5, 12.5), (17.5, 12.5)], 1),                                                       # its pale middle
    ]
    r = 0.55 * PX

    def follow(points, step=3.2):
        """The polyline split into short pieces, each point lifted onto the dome."""
        pts = []
        for a, b in zip(points, points[1:]):
            k = max(1, math.ceil(math.dist(a, b) / step))
            pts += [(a[0] + (b[0] - a[0]) * t / k, a[1] + (b[1] - a[1]) * t / k) for t in range(k)]
        pts.append(points[-1])
        return [world(p, dome_z(p) + 0.25) for p in pts]

    bm = bmesh.new()
    for points, m in seams:
        lib.polyline_tube(bm, follow(points), r, sides=4, mat_index=m)
    lines = common.mesh_object(f"{NAME}_lines", bm, line_mats, coll, smooth=True)

    # The steel drum cap at the top (rows 2-7): a round drum along the gem's axis, as tall as the
    # sprite's highlight band implies. It is polished blue steel: one mid-tone (the sprite's pale
    # band on the upper left is the sheen, its near-black right side and front row the drawn
    # shading and outline), metallic and smooth so the game's light makes the shine.
    cap_mats = [pal(59, metallic=0.7, roughness=0.3)]
    bm = bmesh.new()
    zc = 2.8 * PX
    # One section per sprite row; it ends at row 7, where the dome's rim begins, closed against it.
    common.loft(bm, [(ey(7.0), 6.9 * PX, 3.1 * PX, zc), (ey(6.0), 6.7 * PX, 3.1 * PX, zc),
                     (ey(5.0), 6.2 * PX, 3.0 * PX, zc), (ey(4.0), 5.6 * PX, 2.8 * PX, zc),
                     (ey(3.0), 4.6 * PX, 2.4 * PX, zc), (ey(2.3), 3.6 * PX, 1.9 * PX, zc),
                     (ey(2.05), 2.8 * PX, 1.5 * PX, zc)],
                sides=16, mat_index=0, cap_start=True, cap_end=False)
    common.loft(bm, [(ey(2.05), 2.8 * PX, 1.5 * PX, zc), (ey(1.95), 0.0, 0.0, zc)], sides=16, mat_index=0,
                cap_start=False, cap_end=False)
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)

    return [(NAME, [gem, lines, cap], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
