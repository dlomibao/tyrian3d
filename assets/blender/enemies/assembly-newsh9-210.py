"""Giant eye (newsh9.shp, assembly of 3 pieces): a 3D version of its sprites.

Seen in episode 4 (levels 4.4 and 4.20). Three 2x2 enemies side by side make one 72x28 px object
(sprite.json `assemblyLayout`): the lower half of a huge blue eye in a dark grey socket. The
eyeball is a big sphere (about 15 px high at its crown) coloured pixel by pixel from the sprite
(a mosaic of a few palette shades: the iris, its streaks and glints, the black pupil and the dark
crosshair), with the bright streaks and glints standing a little proud and the crosshair cut in.
The lid is a round ridge about 7-8 px tall wrapping the eyeball's lower rim, its outer skin sloping
down to the sprite's edge; on the right a thinner tail runs up to the top right corner.

The eye is built whole in assembly coordinates, then cut into the three pieces with
common.split_assembly; `finish` gives the pieces the whole eye's normals so the cuts don't crease.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-210.py [-- --preview out.png]
(the preview is the whole eye; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b019 as lib  # noqa: E402

NAME = "assembly-newsh9-210"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-210", "newsh9-212", "newsh9-214"]
# Assembly pixel (0, 0) is screen (125, -32); the 72 x 28 px eye's centre (screen 161, -18) is
# the Blender origin.
CENTRE = (161, -18)
W, H = 72, 28
G = lib.Grid(W, H)
PX = 1 / 12

# The iris: an ellipse centred on pixel edge point (CX, CY) with radii A x B px. The eyeball is an
# ellipsoid DOME high whose equator (SEQ times the iris ellipse) is hidden under the lid; past the
# iris rim (s = 1) it falls away to z = 0 by s = S_END.
CX, CY, A, B = 35.5, 9.0, 20.5, 14.0
DOME, SEQ, S_END = 15.0 * PX, 1.12, 1.08
LID_HI, LID_LO = 7.6, 6.4  # the lid ridge's height (px): lower lid, upper corners
WHOLE = []


def ell_s(c, r):
    return math.sqrt(((c - CX) / A) ** 2 + ((r - CY) / B) ** 2)


def eye_z(c, r):
    """Height of the eyeball's surface over pixel edge point (c, r)."""
    s = ell_s(c, r)
    z1 = DOME * math.sqrt(max(0.0, 1.0 - (1.0 / SEQ) ** 2))
    if s <= 1.0:
        return DOME * math.sqrt(max(0.0, 1.0 - (s / SEQ) ** 2))
    return max(0.0, z1 * (S_END - s) / (S_END - 1.0))


def pixels():
    """The assembly's palette indices (-1 = transparent), rows of 72."""
    grid = [[-1] * W for _ in range(H)]
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            vals = row.split() if isinstance(row, str) else row
            for c, v in enumerate(vals):
                grid[r][c + 24 * i] = int(v)
    return grid


def pix(grid, c, r):
    ci, ri = int(math.floor(c)), int(math.floor(r))
    if ri < -2 or ri >= H or ci < 0 or ci >= W:
        return -1
    return grid[max(ri, 0)][ci]


def ellipse_point(t, s):
    return CX + s * A * math.cos(t), CY + s * B * math.sin(t)


# Palette shades: the sprite's indices folded onto the few shades the model uses.
IRIS_TIERS = [((1, 97, 145), 1), ((51, 52, 53), 53), ((54, 55), 54), ((56, 57, 128, 129), 129),
              ((58, 59, 130), 130), ((131, 132, 133, 134), 131), ((155, 156, 157), 156),
              ((158, 159, 62, 136, 137, 138, 139, 140, 141, 142, 143), 158)]
GREY_TIERS = [((1,), 1), ((2,), 2), ((3, 4), 3), ((5, 6), 5), ((7, 8, 10, 13), 7)]
# Relief by shade (px): only the dark crosshair lines are cut in. The near-white glints (folded
# into the light streak shade above) are the wet eyeball's shine, which the glossy material makes;
# the cornea stays smooth over the streaks.
RELIEF = {53: -0.35, 1: 0.0}


def tier_of(index):
    for idxs, pal in IRIS_TIERS + GREY_TIERS:
        if index in idxs:
            return pal
    return None


def eyeball(bm, grid, slot):
    """The eyeball: one quad per sprite pixel inside the iris, coloured like the sprite, on the
    ellipsoid surface, closed by a wall where the sprite's top row cuts it."""
    cells = {}
    for r in range(H):
        for c in range(W):
            if ell_s(c + 0.5, r + 0.5) < 1.04:
                pal = tier_of(grid[r][c]) or 129
                # Socket greys at the rim (under the lid) take the lid's one grey.
                cells[(c, r)] = 3 if pal in (5, 7) else pal
    # Crosshair pixels are the dark ones in its row and column; elsewhere 53/54 is the limbal ring.
    relief = {}
    for (c, r), pal in cells.items():
        v = RELIEF.get(pal, 0.0)
        if pal in (53, 1) and not (c == 36 or r in (8, 9)):
            v = 0.0
        relief[(c, r)] = v
    verts = {}

    def vert(c, r):
        if (c, r) not in verts:
            near = [relief[k] for k in ((c - 1, r - 1), (c, r - 1), (c - 1, r), (c, r)) if k in relief]
            z = eye_z(c, r) + (sum(near) / len(near) if near else 0.0) * PX * (1.0 if ell_s(c, r) < 0.97 else 0.0)
            verts[(c, r)] = bm.verts.new((G.x(c), G.y(r), z))
        return verts[(c, r)]

    for (c, r), pal in cells.items():
        f = bm.faces.new((vert(c, r), vert(c + 1, r), vert(c + 1, r + 1), vert(c, r + 1)))
        f.material_index = slot[pal]
        f.smooth = True
    # The wall along the top row (the sprite's top edge cuts the eyeball).
    top = sorted(c for (c, r) in cells if r == 0)
    for c in top:
        a, b = verts[(c, 0)], verts[(c + 1, 0)]
        a0 = bm.verts.new((a.co.x, a.co.y, 0.0))
        b0 = bm.verts.new((b.co.x, b.co.y, 0.0))
        f = bm.faces.new((a, a0, b0, b))
        f.material_index = slot[53]
        f.smooth = False


def grey_near(grid, c, r):
    """The socket grey round pixel edge point (c, r): the mean of the grey pixels within 1 px,
    folded onto the lid's shades (so the lid reads as bands of grey, not speckle)."""
    vals = []
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            g = pix(grid, c + dc, r + dr)
            if 0 < g <= 13:
                vals.append(g)
    if not vals:
        return None
    m = sum(vals) / len(vals)
    return 1 if m < 1.5 else 2 if m < 2.6 else 3 if m < 4.4 else 5 if m < 6.4 else 7


def lid_height(t):
    """The lid ridge's height (px) by angle round the iris (t = 90 deg is the bottom, y down)."""
    d = math.degrees(t) % 360
    if 25 <= d <= 155:
        return LID_HI
    if d < 25:
        return LID_LO + (LID_HI - LID_LO) * d / 25
    if d > 270:
        return LID_LO
    if d <= 200:
        return LID_HI - (LID_HI - LID_LO) * (d - 155) / 45
    return LID_LO


def tail_height(t):
    """The outer tail strand's height (px) on the right: tallest low down, thinning to the tip."""
    d = math.degrees(t)
    d = d - 360 if d > 180 else d
    if -75 <= d <= 35:
        # 3 px at 35 deg (where it meets the lower lid), 1.5 px at the tip (about -60 deg).
        f = (35 - d) / 95
        return max(0.8, 3.2 - 1.8 * min(1.0, f))
    return 0.8


def lid(bm, grid, slot):
    """The lid: a closed ring round the iris. Each section runs from inside the eyeball up over a
    round ridge (about 7-8 px tall, up to 8 px wide), down a low skin to the sprite's outer edge and
    back along z = 0. Faces take the sprite's grey under them."""
    n = 64
    reach = []
    for k in range(n):
        t = 2 * math.pi * k / n
        s = 1.0
        while s < 4.0 and pix(grid, *ellipse_point(t, s + 0.02)) >= 0:
            s += 0.02
        step = math.hypot(A * math.cos(t), B * math.sin(t))
        reach.append(max(1.1, s - PULL / step))
    reach = [(reach[k - 1] + 2 * reach[k] + reach[(k + 1) % n]) / 4 for k in range(n)]
    rings = []
    for k in range(n):
        t = 2 * math.pi * k / n
        step = math.hypot(A * math.cos(t), B * math.sin(t))
        s_out = reach[k]
        s_lip, s_in = 0.985, 0.94
        s_r = min(s_out - 0.03, 1.0 + 8.0 / step)
        s_c, hw = (s_lip + s_r) / 2, (s_r - s_lip) / 2
        h = lid_height(t)
        d = s_out - s_r
        pts = [(s_in, 1.5)]
        for deg in (180, 150, 120, 90, 60, 30, 0):
            p = math.radians(deg)
            z = h * math.sin(p) ** 0.8
            if deg == 180:
                z = 0.25 * h
            elif deg == 0:
                z = max(0.9, 0.15 * h)
            pts.append((s_c + hw * math.cos(p), z))
        tb = tail_height(t)
        pts += [(s_r + 0.45 * d, max(0.7, tb * 0.55)), (s_r + 0.8 * d, tb), (s_out, 0.35), (s_out, 0.0), (s_in, 0.0)]
        ring = []
        for ss, z in pts:
            c, r = ellipse_point(t, ss)
            ring.append(bm.verts.new((G.x(c), G.y(r), z * PX)))
        rings.append((t, pts, ring))
    m = len(rings[0][2])
    for k in range(n):
        t0, pts, r0 = rings[k]
        t1, _, r1 = rings[(k + 1) % n]
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
            # The grey under the face's middle (inside faces and the base keep the dark grey).
            tm = (t0 + (t1 if t1 > t0 else t1 + 2 * math.pi)) / 2
            sm = (pts[i][0] + pts[j][0]) / 2
            # One mid-tone grey for the whole lid: the sprite's dark outer ring and lit ridge band
            # are its drawn lighting (the game lights the ridge and draws the outline).
            pal = 2 if (i >= m - 3 or i == 0) else 3
            f.material_index = slot[pal]
            f.smooth = i < m - 3


PULL = -0.2  # how far the outer edge is pulled in from the sprite's last pixel (px)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9e"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    spec = [
        # The eyeball is wet and glossy (pupil included); the lid is skin: matte.
        (1, dict(metallic=0.0, roughness=0.15)),  # pupil
        (2, dict(metallic=0.0, roughness=0.8)),  # lid underside, inner rim
        (3, dict(metallic=0.0, roughness=0.7)),  # lid
        (53, dict(metallic=0.0, roughness=0.1)),  # crosshair, limbal ring
        (54, dict(metallic=0.0, roughness=0.1, emission_strength=0.3)),
        (129, dict(metallic=0.0, roughness=0.1, emission_strength=0.5)),  # iris
        (130, dict(metallic=0.0, roughness=0.1, emission_strength=0.5)),
        (131, dict(metallic=0.0, roughness=0.1, emission_strength=0.6)),
        (156, dict(metallic=0.0, roughness=0.1, emission_strength=1.0)),  # streaks
        (158, dict(metallic=0.0, roughness=0.1, emission_strength=1.1)),
    ]
    mats = [pal(i, **kw) for i, kw in spec]
    slot = {i: k for k, (i, _) in enumerate(spec)}
    grid = pixels()
    bm = bmesh.new()
    eyeball(bm, grid, slot)
    lid(bm, grid, slot)
    obj = lib.to_object(NAME, bm, mats, coll)
    WHOLE[:] = [obj]
    return obj


def keep_normals(piece, whole, offset):
    """Mark the faces split_assembly filled along the cuts flat, and give every smooth corner the
    uncut eye's normal (interpolated from the face under it), so the shading runs on across the
    cuts instead of creasing there."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or \
                any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh)):
            poly.use_smooth = False
    src = whole.data
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(p.vertices) for p in src.polygons])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp = src.polygons[fi]
            w = poly_3d_calc([src.vertices[v].co for v in sp.vertices], hit)
            nrm = Vector()
            for wk, lk in zip(w, sp.loop_indices):
                nrm += wk * corner[lk].vector
            normals.append(nrm.normalized() if nrm.length > 1e-6 else poly.normal.copy())
    mesh.normals_split_custom_set(normals)


def finish(parts, sprite):
    for name, obj in parts.items():
        e = next(e for e in sprite["assemblyLayout"] if e["model"] == name)
        keep_normals(obj, WHOLE[0], ((e["cx"] - CENTRE[0]) / 12, -(e["cy"] - CENTRE[1]) / 12))


def main():
    lib.run_assembly(ROOT, NAME, PIECES, CENTRE, build, size=6, grid_w=W, grid_h=H, finish=finish)


if __name__ == "__main__":
    main()
