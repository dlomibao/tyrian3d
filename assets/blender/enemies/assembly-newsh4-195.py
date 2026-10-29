"""Bronze boss arm (newsh4.shp, assembly of 7 pieces): a 3D version of its sprites.

Seen in levels 1.3 and 3.17. Seven 2x2 enemies in a row make one 168x28 px arm reaching out to
the right (sprite.json `assemblyLayout`): a thick bronze upper arm with a dark underside
(newsh4-153), a ball joint on a narrow neck (newsh4-155), a forearm ringed by a grey metal collar
and a bright rib (newsh4-157), a grey-brown box and a grey block on top (newsh4-159), and a
tapering horn-like claw that curves down to a point (newsh4-191, -193, -195) with two small grey
clamps on it. Every piece has one frame. Remodelled on the concept: the upper arm is a riveted
bronze canister over a dark chamfered housing with a hydraulic pipe up its slanted end, the neck is
ringed, the forearm carries steel rings, a dark collar, a junction box over a piped bay, a grey
sleeve and raised plates, and the claw's clamps are ribbed steel bands, each where the registered
concept draws it so texture_bake.py's detail lands on the matching part.

The whole arm is built once in assembly coordinates, then cut into the seven pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-195.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh4-195"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-153", "newsh4-155", "newsh4-157", "newsh4-159", "newsh4-191", "newsh4-193", "newsh4-195"]
# Assembly pixel (0, 0) is the top-left corner of newsh4-153 (screen cx 50 - 12, cy -18 - 14);
# the arm is 168 x 28 px and its centre (screen 122, -18) is the Blender origin.
CX0, CY0 = 122, -18
W, H = 168, 28
PX = 1 / 12


def XE(u):
    """Assembly pixel-edge coordinate (column c spans u in [c, c + 1]) to Blender X."""
    return (u - W / 2) / 12


def YE(v):
    """Assembly pixel-edge coordinate (row r spans v in [r, r + 1]) to Blender Y (up is +Y)."""
    return (H / 2 - v) / 12


# --- geometry helpers --------------------------------------------------------------------------

def _faces_between(bm, rings, mat, smooth, cap_start=True, cap_end=True):
    sides = max(len(r) for r in rings)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def loft_x(bm, sections, sides=12, mat=0, smooth=True, shear=None, caps=True):
    """A tube along the arm (+X). Sections are (u, v_top, v_bottom, half_height_units, z): the
    pixel-edge column and the top and bottom pixel edges it covers there. Zero width collapses
    the ring to a point. `shear(u, v)` may return a column offset per vertex (slanted ends)."""
    rings = []
    for u, vt, vb, hz, z in sections:
        vc, hw = (vt + vb) / 2, (vb - vt) / 2
        if hw <= 0 and hz <= 0:
            rings.append([bm.verts.new((XE(u), YE(vc), z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            v = vc - hw * math.cos(a)
            uu = u + (shear(u, v) if shear else 0.0)
            ring.append(bm.verts.new((XE(uu), YE(v), z + hz * math.sin(a))))
        rings.append(ring)
    return _faces_between(bm, rings, mat, smooth, caps, caps)


def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (u, v, z, half_width_px, half_height_units), rings perpendicular
    to the path in the XY plane."""
    pts = [Vector((XE(u), YE(v), z)) for u, v, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (u, v, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    return _faces_between(bm, rings, mat, smooth)


def block(bm, u0, v0, u1, v1, z0, z1, mat=0, bevel=0.0):
    """A box over pixel edges [u0, u1] x [v0, v1], from z0 up to z1 (top edges chamfered by `bevel` px)."""
    b = bevel
    outline = [(XE(u0), YE(v1)), (XE(u1), YE(v1)), (XE(u1), YE(v0)), (XE(u0), YE(v0))]
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    if b:
        top = [(XE(u0 + b), YE(v1 - b)), (XE(u1 - b), YE(v1 - b)), (XE(u1 - b), YE(v0 + b)), (XE(u0 + b), YE(v0 + b))]
        common.slab(bm, top, b * PX, z=z1 + b * PX / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = False


def ellipsoid(bm, u, v, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for vert in res["verts"]:
        vert.co = Vector((XE(u) + vert.co.x * rx_px * PX, YE(v) + vert.co.y * ry_px * PX, z + vert.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


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


# --- the sprite as one grid --------------------------------------------------------------------

def grid():
    """The assembly's pixels (palette indices, -1 transparent) as rows of W columns."""
    g = [[-1] * W for _ in range(H)]
    sprite = common.load_sprite(ROOT, PIECES[0])
    for e in sprite["assemblyLayout"]:
        frame = common.load_sprite(ROOT, e["model"])["frames"][0]
        x0, y0 = e["cx"] - CX0 + W // 2 - 12, e["cy"] - CY0 + H // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, val in enumerate(row):
                if val >= 0:
                    g[y0 + r][x0 + c] = val
    return g


def profile(g, c):
    """Top and bottom pixel edges of the sprite in column c."""
    rows = [r for r in range(H) if g[r][c] >= 0]
    return rows[0], rows[-1] + 1


# --- the arm -----------------------------------------------------------------------------------
# Remodelled on the concept (assets/blender/features/concepts/assembly-newsh4-195.jpg, registered
# to the sprite as assets/blender/textures/assembly-newsh4-195/concept.png): every part sits where
# the concept draws it, inside the sprite's outline, so the concept detail that texture_bake.py
# projects straight down lands on the matching part.

def prism(bm, pts, z0, z1, mat, chamfer=0.6):
    """A hard plate: a convex outline of pixel-edge points (u, v), from z0 up to z1, its top edge
    chamfered inwards by `chamfer` px (and down by as much)."""
    n = len(pts)
    cu = sum(p[0] for p in pts) / n
    cv = sum(p[1] for p in pts) / n
    inset = []
    for i, (u, v) in enumerate(pts):
        # Move each corner towards the centre along the bisector of its two edges.
        pu, pv = pts[i - 1]
        nu, nv = pts[(i + 1) % n]
        d1 = Vector((u - pu, v - pv)).normalized()
        d2 = Vector((nu - u, nv - v)).normalized()
        b = (d2 - d1)
        if b.length < 1e-6:
            b = Vector((cu - u, cv - v))
        b.normalize()
        if b.dot(Vector((cu - u, cv - v))) < 0:
            b = -b
        sin_half = max(0.3, math.sqrt(max(0.0, (1 - d1.dot(d2)) / 2)))
        inset.append((u + b.x * chamfer / sin_half, v + b.y * chamfer / sin_half))
    c = min(chamfer * PX, (z1 - z0) * 0.45)
    bot = [bm.verts.new((XE(u), YE(v), z0)) for u, v in pts]
    mid = [bm.verts.new((XE(u), YE(v), z1 - c)) for u, v in pts]
    top = [bm.verts.new((XE(u), YE(v), z1)) for u, v in inset]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], mid[j], mid[i])))
        faces.append(bm.faces.new((mid[i], mid[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False
    return faces


U_TIP = 166.2
FORE_HZ = 0.47  # forearm half height (units): about as tall as its 12 px width


def body_sections(g):
    """The forearm-and-claw tube, from the ball's shoulder to the claw's tip: (u, v_top, v_bottom,
    half height, z) per section, following the sprite's outline averaged over a few columns."""
    secs = []
    for u in [47, 50, 53, 56] + list(range(60, 100, 5)) + list(range(100, 164, 4)) + [163.5, 165.0]:
        c = min(int(u), W - 3)
        near = [profile(g, k) for k in range(max(c - 2, 0), min(c + 3, W - 2))]
        top = sum(p[0] for p in near) / len(near)
        bot = sum(p[1] for p in near) / len(near)
        if u < 56:
            # The ball's shoulder: the forearm's own tube, swelling into the ball.
            top, bot = 1.0, 13.0
        t = max(0.0, (u - 100) / (U_TIP - 100))
        if u <= 100:
            top = min(top, 1.6) if u < 92 else top
            bot = max(bot, 13.0) if u < 100 else bot
        hz = FORE_HZ * (1 - t) ** 1.1 + 0.012
        z = -0.12 * t * t
        secs.append((u, top - 0.1, bot + 0.1, hz, z))
    secs.append((U_TIP, 24.7, 24.7, 0.0, -0.12))
    return secs


def section_at(secs, u):
    for a, b in zip(secs, secs[1:]):
        if a[0] <= u <= b[0]:
            t = (u - a[0]) / max(b[0] - a[0], 1e-6)
            return tuple(x + (y - x) * t for x, y in zip(a, b))
    return secs[-1] if u > secs[-1][0] else secs[0]


def band(bm, secs, u0, u1, grow_px, grow_z, mat, sides=12, smooth=True):
    """A ring around the forearm or claw from column u0 to u1, standing grow_px / grow_z proud,
    with crisp ends."""
    rings = []
    for u, k in ((u0, 0.0), (u0 + 0.05, 1.0), (u1 - 0.05, 1.0), (u1, 0.0)):
        _, top, bot, hz, z = section_at(secs, u)
        g = grow_px * k - 0.3 * (1 - k)
        rings.append((u, top - g, bot + g, hz + grow_z * k - 0.02 * (1 - k), z))
    # The ends tuck under the tube's surface, so they need no caps.
    return loft_x(bm, rings, sides=sides, mat=mat, smooth=smooth, caps=False)


def build(sprite, g):
    coll = common.reset_collection(NAME)
    tag = "nsh4a"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.55, roughness=0.35),  # 0 bronze canister (upper arm)
        pal(18, metallic=0.45, roughness=0.5),  # 1 dark bronze lower section of the upper arm
        pal(21, metallic=0.55, roughness=0.35),  # 2 forearm
        pal(22, metallic=0.55, roughness=0.35),  # 3 raised bronze plates
        pal(26, metallic=0.6, roughness=0.3),  # 4 bright bronze rims and pipe
        pal(9, metallic=0.8, roughness=0.25),  # 5 polished steel rings
        pal(6, metallic=0.7, roughness=0.35),  # 6 dark steel collar, clamps
        pal(166, metallic=0.4, roughness=0.45),  # 7 grey-brown junction box
        pal(7, metallic=0.75, roughness=0.3),  # 8 grey sleeve
        pal(3, metallic=0.3, roughness=0.7),  # 9 dark recesses and machinery
        pal(164, metallic=0.4, roughness=0.5),  # 10 dark bronze neck and bay
        pal(22, metallic=0.55, roughness=0.32),  # 11 ball joint
        pal(20, metallic=0.55, roughness=0.35),  # 12 the claw, a little darker than the forearm
    ]
    (CAN, LOWER, ARM, PLATE, RIM, STEEL, COLLAR, BOX, SLEEVE, DARK, NECK, BALL, CLAW) = range(13)
    bm = bmesh.new()

    # Upper arm, top member (concept: a big riveted bronze canister, rows 1-12): a round tube,
    # cut off by the piece's left edge, with a flanged end ring and a conical end tapering into
    # the neck (cols 26-32).
    loft_x(bm, [(-1, 0.9, 12.6, 0.48, 0.0), (26.5, 0.9, 12.6, 0.48, 0.0), (28.5, 1.4, 12.2, 0.44, 0.0),
                (30.5, 2.4, 11.6, 0.37, 0.0), (32.0, 3.2, 11.2, 0.3, 0.0), (32.1, 4.5, 10.0, 0.15, 0.0)],
           sides=18, mat=CAN)
    band(bm, [(-1, 0.9, 12.6, 0.48, 0.0), (8, 0.9, 12.6, 0.48, 0.0)], -1.0, 5.6, 0.2, 0.025, CAN, sides=18)
    loft_x(bm, [(5.6, 0.7, 12.8, 0.0, 0.0), (5.7, 0.7, 12.8, 0.5, 0.0), (6.5, 0.7, 12.8, 0.5, 0.0),
                (6.6, 0.9, 12.6, 0.0, 0.0)], sides=18, mat=STEEL)

    # Upper arm, lower member (concept: dark riveted side panels, rows 12-22, ending in a slanted
    # edge rimmed by a bright hydraulic pipe): a hard chamfered housing, lower than the canister.
    prism(bm, [(-1, 12.0), (30.0, 12.0), (35.6, 13.8), (31.4, 21.6), (29.4, 22.3), (-1, 22.3)],
          -0.36, 0.14, LOWER, chamfer=0.8)
    prism(bm, [(6.5, 13.2), (23.5, 13.2), (24.8, 14.5), (24.8, 17.2), (6.5, 17.2)], 0.1, 0.19, PLATE, chamfer=0.5)
    prism(bm, [(6.5, 18.0), (12.0, 18.0), (12.0, 21.3), (6.5, 21.3)], 0.1, 0.18, PLATE, chamfer=0.4)
    # End flange of the lower member (the concept's end ring spans the whole upper arm).
    prism(bm, [(-1, 12.0), (5.6, 12.0), (5.6, 22.3), (-1, 22.3)], -0.36, 0.2, LOWER, chamfer=0.6)
    # The hydraulic pipe along the bottom and up the slanted end.
    sweep(bm, [(10.0, 19.6, 0.17, 0.9, 0.075), (26.5, 19.6, 0.17, 0.9, 0.075), (29.2, 19.8, 0.17, 0.9, 0.075),
               (31.6, 17.6, 0.17, 0.9, 0.075), (34.0, 14.6, 0.17, 0.9, 0.075)], sides=8, mat=RIM)
    # Machinery between the canister's end and the ball (concept cols 24-33, rows 9-18).
    prism(bm, [(25.0, 11.0), (31.2, 11.0), (33.2, 13.0), (31.2, 18.2), (25.0, 18.2)], -0.1, 0.3, DARK, chamfer=0.5)
    prism(bm, [(26.0, 12.0), (30.6, 12.0), (30.6, 16.0), (26.0, 16.0)], 0.2, 0.38, NECK, chamfer=0.5)

    # Neck (cols 31-37): narrower and lower than both the canister and the ball, so it pinches in.
    loft_x(bm, [(30.5, 2.0, 12.4, 0.3, 0.0), (37.5, 2.3, 12.4, 0.3, 0.0)], sides=14, mat=NECK)
    for u in (33.0, 35.2):
        loft_x(bm, [(u, 2.4, 12.0, 0.0, 0.0), (u + 0.1, 1.9, 12.6, 0.34, 0.0), (u + 1.0, 1.9, 12.6, 0.34, 0.0),
                    (u + 1.1, 2.4, 12.0, 0.0, 0.0)], sides=10, mat=DARK, caps=False)

    # Ball joint (concept: a round shell, cols 36-55, rows 2-19, with a big lobe under it).
    ellipsoid(bm, 45.2, 9.8, 0.02, 9.4, 8.5, 0.62, mat=BALL, segments=16, rings=8)
    ellipsoid(bm, 41.6, 14.0, -0.04, 7.0, 5.6, 0.46, mat=BALL, segments=12, rings=7)

    # Forearm and claw: one round tube following the sprite's outline, tapering to the tip.
    secs = body_sections(g)
    claw_x = XE(101)
    for f in loft_x(bm, secs, sides=14, mat=ARM):
        if f.calc_center_median().x > claw_x:
            f.material_index = CLAW

    # Rings and sleeves along the forearm, where the concept draws them.
    band(bm, secs, 56.6, 58.6, 0.5, 0.045, STEEL)   # polished ring
    band(bm, secs, 58.6, 65.8, 0.25, 0.025, COLLAR)  # dark steel collar
    band(bm, secs, 65.8, 67.6, 0.5, 0.045, STEEL)   # polished ring
    band(bm, secs, 75.8, 77.2, 0.4, 0.035, STEEL)   # thin ring before the machinery bay
    band(bm, secs, 84.0, 89.6, 0.3, 0.03, SLEEVE)   # grey sleeve
    band(bm, secs, 89.6, 90.4, 0.4, 0.035, RIM)
    # Machinery bay (cols 77-84): a darker recessed band with pipes over it and a junction box on top.
    band(bm, secs, 77.2, 84.0, 0.1, 0.008, NECK)
    for v in (8.3, 10.6):
        sweep(bm, [(76.6, v, 0.0, 0.6, 0.38), (84.4, v, 0.0, 0.6, 0.38)], sides=8, mat=RIM)
    prism(bm, [(76.6, 1.2), (82.8, 1.2), (82.8, 6.6), (76.6, 6.6)], 0.0, 0.58, BOX, chamfer=0.6)
    prism(bm, [(79.6, 6.2), (82.6, 6.2), (82.6, 12.8), (79.6, 12.8)], -0.2, 0.36, BOX, chamfer=0.5)
    # Grey block on the sleeve and its vent slot.
    prism(bm, [(84.6, 1.8), (89.4, 1.8), (89.4, 7.0), (84.6, 7.0)], 0.0, 0.56, SLEEVE, chamfer=0.6)
    prism(bm, [(85.2, 7.8), (88.8, 7.8), (88.8, 10.2), (85.2, 10.2)], 0.0, 0.47, DARK, chamfer=0.3)
    # Riveted plate on the forearm (cols 67-75) and the plate and dark device on cols 90-105.
    prism(bm, [(68.2, 1.6), (75.0, 1.6), (75.0, 8.6), (68.2, 8.6)], 0.0, 0.53, PLATE, chamfer=0.6)
    prism(bm, [(91.0, 2.6), (104.6, 3.2), (104.6, 7.2), (91.0, 7.2)], 0.0, 0.51, PLATE, chamfer=0.6)
    prism(bm, [(95.6, 7.6), (104.8, 7.6), (104.8, 12.4), (95.6, 12.4)], 0.0, 0.47, PLATE, chamfer=0.5)
    sweep(bm, [(91.4, 9.6, 0.4, 1.0, 0.07), (99.2, 9.6, 0.4, 1.0, 0.07)], sides=8, mat=DARK)

    # Claw: two dark steel clamps (cols 106-112 and 124-130), each a ribbed band wrapped round the claw.
    for u0, u1 in ((106.0, 112.0), (123.8, 130.0)):
        band(bm, secs, u0, u1, 0.3, 0.045, COLLAR)
        for uu in (u0 + 0.9, u1 - 0.9):
            band(bm, secs, uu - 0.4, uu + 0.4, 0.5, 0.07, STEEL, sides=12)
    band(bm, secs, 112.2, 113.2, 0.3, 0.035, RIM)
    band(bm, secs, 130.2, 131.2, 0.3, 0.03, RIM)
    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh4-195's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh4-195")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(g, colors, out):
    """The whole arm's sprite as one image, padded to the 24:28 shape that render_preview expects
    for size 14 (168 x 196 px, the arm in the middle)."""
    import numpy as np
    img = np.zeros((196, 168, 4), dtype=np.float32)
    y0 = (196 - H) // 2
    for r in range(H):
        for c in range(W):
            if g[r][c] >= 0:
                img[y0 + r, c] = [*(ch / 255 for ch in colors[str(g[r][c])]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 168, 196, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    g = grid()
    obj = build(sprite, g)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    print(f"whole arm: {len(obj.data.polygons)} faces")
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(g, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=14, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
