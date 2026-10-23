"""Helpers shared by batch b110's model scripts (newshc.shp ground machines on level 1.19 / 3.23).

build-models.sh skips lib_ files; the model scripts import this one.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


class Frame:
    """Pixel-to-unit mapping for a block of w x h sprite pixels whose centre is the origin."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        """Column (pixel centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) * PX

    def y(self, r):
        """Row (pixel centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) * PX

    def xe(self, c):
        """Pixel edge (left edge of column c) to Blender X."""
        return (c - self.w / 2) * PX

    def ye(self, r):
        """Pixel edge (top edge of row r) to Blender Y."""
        return (self.h / 2 - r) * PX


def _faces_since(bm, before):
    return [f for f in bm.faces if f not in before]


def tag(bm, before, mat, smooth):
    for f in _faces_since(bm, before):
        f.material_index = mat
        f.smooth = smooth


def tube(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, arc=None):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand perpendicular
    to the path in the XY plane (width across the path, height along Z). A ring of zero size is a
    point. `arc` = (a0, a1) in radians builds only that part of each ring (e.g. (0, pi) for the top
    half) and closes it with a flat bottom."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        if arc:
            a0, a1 = arc
            angles = [a0 + (a1 - a0) * k / sides for k in range(sides + 1)]
        else:
            angles = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
        for a in angles:
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    n = sides + 1 if arc else sides
    closed = not arc
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(n if closed else n - 1):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
        if arc and len(r0) > 1 and len(r1) > 1:  # flat bottom between the arc ends
            f = bm.faces.new((r0[-1], r0[0], r1[0], r1[-1]))
            f.smooth = False
            f.material_index = mat
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def loft_y(bm, x, sections, sides=12, mat=0, smooth=True, arc=None, mats=None, **kw):
    """A loft down the sprite (along -Y) centred on X = x: sections are (y, half_width, half_height, z)
    in units. `mats`, one per gap between sections, colours each band separately."""
    faces = tube(bm, [(x, y, z, w, h) for y, w, h, z in sections], sides=sides, mat=mat, smooth=smooth,
                 arc=arc, **kw)
    if mats:
        for f in faces:
            yc = sum(v.co.y for v in f.verts) / len(f.verts)
            for (y0, *_), (y1, *_), m in zip(sections, sections[1:], mats):
                if min(y0, y1) - 1e-6 <= yc <= max(y0, y1) + 1e-6:
                    f.material_index = m
                    break
    return faces


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=16, rings=8, zmin=None, smooth=True, pole_y=False):
    """An ellipsoid (units). With zmin, vertices below it are flattened onto it (a dome). With
    pole_y its rings stand across Y (so colour bands down the screen follow its edges)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        vx, vy, vz = (v.co.x, v.co.z, v.co.y) if pole_y else (v.co.x, v.co.y, v.co.z)
        v.co = Vector((x + vx * rx, y + vy * ry, z + vz * rz))
        if zmin is not None and v.co.z < zmin:
            v.co.z = zmin
    tag(bm, before, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    before = set(bm.faces)
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2)
    tag(bm, before, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an outline of (x, y) unit points from z0 to z1."""
    before = set(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2)
    tag(bm, before, mat, smooth)


def floor_tiles(bm, fr, pixels, base_mat, raised, col0=0, row0=0, z_base=0.03, z_raised=0.055,
                indices=range(96, 103)):
    """The floor a ground sprite is drawn on: a thin plate over the whole block plus raised tiles
    where the floor pixels are light. `raised` maps a palette index to the material slot of a raised
    tile (indices not in it stay at the base level). Pixels are merged greedily into rectangles.
    col0/row0 offset the sprite inside the frame `fr` (for assemblies)."""
    h, w = len(pixels), len(pixels[0])
    e = 0.0015  # stay just inside the block so a neighbouring piece's cut doesn't keep a sliver
    box(bm, fr.xe(col0) + e, fr.ye(row0 + h) + e, fr.xe(col0 + w) - e, fr.ye(row0) - e, 0.0, z_base, base_mat)
    used = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = pixels[r][c]
            if used[r][c] or v not in raised:
                continue
            slot = raised[v]
            c1 = c
            while c1 + 1 < w and not used[r][c1 + 1] and raised.get(pixels[r][c1 + 1]) == slot:
                c1 += 1
            r1 = r
            while r1 + 1 < h and all(not used[r1 + 1][k] and raised.get(pixels[r1 + 1][k]) == slot
                                     for k in range(c, c1 + 1)):
                r1 += 1
            for rr in range(r, r1 + 1):
                for k in range(c, c1 + 1):
                    used[rr][k] = True
            box(bm, fr.xe(col0 + c) + e, fr.ye(row0 + r1 + 1) + e, fr.xe(col0 + c1 + 1) - e, fr.ye(row0 + r) - e,
                z_base, z_raised, slot)


def paint(bm, faces, fr, pixels, slot_of, col0=0, row0=0, up_only=True):
    """Colour `faces` from the sprite seen from above: each face takes the slot (slot_of[index]) of
    the pixel under its centre; faces over unmapped pixels keep their material. With up_only,
    steep (sideways) faces are left alone."""
    h, w = len(pixels), len(pixels[0])
    for f in faces:
        if up_only:
            f.normal_update()
            if abs(f.normal.z) < 0.3:  # winding isn't settled yet, so either sign counts as up
                continue
        cx = sum(v.co.x for v in f.verts) / len(f.verts)
        cy = sum(v.co.y for v in f.verts) / len(f.verts)
        c = int(math.floor(cx / PX + fr.w / 2)) - col0
        r = int(math.floor(fr.h / 2 - cy / PX)) - row0
        if 0 <= r < h and 0 <= c < w:
            slot = slot_of.get(pixels[r][c])
            if slot is not None:
                f.material_index = slot


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def faces_of(objs):
    return sum(len(o.data.polygons) for o in objs)


def preview_arg():
    if "--preview" in sys.argv:
        return sys.argv[sys.argv.index("--preview") + 1]
    return None


def sprite_png(root, name, sprite, frame=0):
    return root / "reference" / "models" / name / sprite["frames"][frame]["image"]


def composite_png(root, placements, w, h, out):
    """Several sprites as one image (w x h px, padded to render_preview's 24:28 shape by the
    caller's choice of w and h). placements: (sprite dict, frame index, left col, top row)."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for data, fi, x0, y0 in placements:
        frame = data["frames"][fi]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# --- the pop-up ball turret on top of the pillars (newshc-77, 7 frames) --------------------------

# Per frame of newshc-77: how many rows the turret sits above its rest position (it rises out of
# the pillar and shows its stem), the half width of the red collar's lower part (it opens out
# sideways), the width of the dark slot down the collar's front, and the eye's glow index
# (None = an empty dark socket).
HEAD_FRAMES = {
    77: dict(dy=-6, collar=8, slot=1, eye=None),
    79: dict(dy=-3, collar=8, slot=1, eye=112),
    81: dict(dy=-1, collar=8, slot=1, eye=114),
    83: dict(dy=0, collar=8, slot=1, eye=118),
    85: dict(dy=0, collar=9, slot=3, eye=118),
    87: dict(dy=0, collar=10, slot=5, eye=114),
    89: dict(dy=0, collar=11, slot=7, eye=None),
}

HEAD_SLOTS = ["sphere", "stripe", "collar", "collar_light", "slot_rim", "slot", "stem", "socket", "eye"]


def head_materials(pal, eye_index):
    """Materials for a head, in HEAD_SLOTS order (pal(index, **kw) makes a palette material)."""
    return [
        pal(9, metallic=0.6, roughness=0.3),  # grey ball
        pal(73, metallic=0.3, roughness=0.45),  # red stripe over the ball
        pal(71, metallic=0.3, roughness=0.5),  # red collar
        pal(73, metallic=0.3, roughness=0.45),  # collar's lit rim
        pal(66, metallic=0.2, roughness=0.6),  # dark red round the slot
        pal(16, metallic=0.1, roughness=0.8),  # the slot
        pal(6, metallic=0.6, roughness=0.35),  # grey stem
        pal(2, metallic=0.1, roughness=0.8),  # empty eye socket
        pal(eye_index, emission_strength=4.0) if eye_index else pal(2, metallic=0.1, roughness=0.8),  # eye
    ]


def build_head(bm, fr, col0, row0, frame, base=0):
    """One frame's shape of the ball turret, its 24x28 block's top-left at (col0, row0) of `fr`.
    Material slots are base + HEAD_SLOTS order."""
    S = {n: base + i for i, n in enumerate(HEAD_SLOTS)}
    p = HEAD_FRAMES[frame]
    dy, W, slot_w = p["dy"], p["collar"], p["slot"]
    lift = -dy * 0.035
    X = lambda c: fr.x(col0 + c)  # noqa: E731
    Y = lambda r: fr.y(row0 + r + dy)  # noqa: E731
    xc = X(11.5)

    # Red collar: a rounded hood from just behind the ball's middle down to the front (rows 12-27).
    hh = 0.4
    sec = [(11.6, 0.0), (12.0, 6.0), (13.5, 8.0), (20.5, 8.0), (21.2, W), (24.5, W), (25.5, W - 1),
           (26.5, W - 2), (27.5, W - 4)]
    loft_y(bm, xc, [(Y(r - 0.5), w * PX, hh if w else 0.0, lift) for r, w in sec], sides=14,
           arc=(0, math.pi), mat=S["collar"])
    if W > 9:  # side flaps swung out beside the ball (rows 14-20)
        for s in (-1, 1):
            xo = xc + s * (W - 0.6) * PX
            before = set(bm.faces)
            common.slab(bm, [(xo - 0.6 * PX, Y(20.3)), (xo + 0.6 * PX, Y(20.3)), (xo + 0.6 * PX, Y(14.0 - (W - 10))),
                             (xo - 0.6 * PX, Y(14.0 - (W - 10)))], 0.2, z=lift + 0.12)
            tag(bm, before, S["collar_light"], False)
    elif W > 8:
        for s in (-1, 1):
            box(bm, xc + s * 7.5 * PX, Y(20.5), xc + s * 9 * PX, Y(15.5), lift, lift + 0.18, S["collar"])
    # Lit rim of the hood round the front of the ball.
    path = []
    for k in range(9):
        a = math.pi * (1.1 + 0.8 * k / 8)
        path.append((xc + 8.1 * PX * math.cos(a), Y(13.0) + 3.5 * PX * math.sin(a), lift + 0.3, 1.0 * PX, 0.06))
    tube(bm, path, sides=6, mat=S["collar_light"])

    # The dark slot down the front of the hood (rows 21-27), wider as the hood opens.
    xs = X(11.0)
    half = slot_w / 2 * PX
    box(bm, xs - half - 0.5 * PX, Y(27.4), xs + half + 0.5 * PX, Y(20.6), lift + 0.25, lift + hh + 0.012,
        S["slot_rim"])
    box(bm, xs - half, Y(23.6), xs + half, Y(21.5), lift + 0.3, lift + hh + 0.02, S["slot"])

    # The grey ball (rows 7-20) with a red stripe over it and the eye on top.
    zc, rz = lift + 0.42, 0.36
    ellipsoid(bm, xc, Y(13.4), zc, 8.0 * PX, 6.6 * PX, rz, mat=S["sphere"], segments=20, rings=10)
    ellipsoid(bm, xc, Y(13.4), zc, 1.3 * PX, 6.85 * PX, rz + 0.04, mat=S["stripe"], segments=8, rings=12)
    ellipsoid(bm, X(11.2), Y(10.6), zc + 0.322, 2.8 * PX, 2.3 * PX, 0.035, mat=S["socket"], segments=12, rings=6)
    ellipsoid(bm, X(11.2), Y(10.6), zc + 0.33, 2.1 * PX, 1.6 * PX, 0.035, mat=S["eye"], segments=12, rings=6)

    # The stem it rises on, showing below the hood while it's up.
    if dy < 0:
        ye = lambda r: fr.ye(row0 + r)  # noqa: E731  (absolute edges, not moved with the turret)
        top = 28.0 + dy - 1.5
        loft_y(bm, xc, [(ye(top), 3.5 * PX, 0.25, 0.0), (ye(max(top + 1.0, 25.0)), 5.0 * PX, 0.3, 0.0),
                        (ye(28.0), 6.5 * PX, 0.32, 0.0)], sides=12, arc=(0, math.pi), mat=S["stem"])
