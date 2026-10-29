"""Grey two-legged pylon with a blue tube (newsh2.shp frames 123 and 125, an assembly of 2 pieces):
a 3D version of its sprites.

Seen in episodes 1 and 3 (levels 1.25, 1.3, 1.36, 3.17), just below the blue-armed gun walker
(assembly-newsh2-87). Two 2x2 enemies side by side (newsh2-123 on the left, newsh2-125 on the
right, sprite.json `assemblyLayout`) make one 48x28 px structure, mirror symmetric about the
edge between pixel columns 22 and 23. Remodelled on the concept
(assets/blender/features/concepts/assembly-newsh2-123.jpg, registered to the sprite as
assets/blender/textures/assembly-newsh2-123/concept.png): every part sits where the concept draws
it, kept inside the sprite's outline, so the concept detail texture_bake.py projects lands on the
matching part. Hard chamfered housings, round leg columns, round glowing pipes:

- a tall chamfered head housing (the tallest part) with a square blue light in a raised frame,
  over a wider lower housing with sloping shoulders;
- a glowing glass tube down the middle (rows 6-13) in a framed dark channel, capped top and bottom;
- two legs: a domed hip cap with a bright ring band and a collar, a round leg column running down
  into a low dark axe-blade foot with a glowing blue rim along its outer curve, a blue strip down
  the leg's inner edge, and a glowing blue pipe looping out from the hip, down the outside of the
  leg and back in;
- between the legs, under an arch, a recessed dark bay with a toothed gear and a crank shaft.

It stands on the ground. Built whole in assembly coordinates and cut into the two pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-123.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "assembly-newsh2-123"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-123", "newsh2-125"]
# Screen pixel at the Blender origin: between the pieces' centres (cx 161 and 185, cy 51).
CX0, CY0 = 173, 51
G = lib.Grid(48, 28)  # both pieces, newsh2-123's left edge at u = 0
AXIS = 23.0  # mirror plane: the edge between columns 22 and 23
PX = lib.PX


def cprism(bm, outline, z0, z1, mat, chamfer=0.0):
    """A hard prism over a convex outline of (u, v) pixel edges, from z0 to z1, its top edge
    chamfered by `chamfer` units (flat shaded)."""
    start = len(bm.faces)
    pts = [(G.x(u), G.y(v)) for u, v in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    n = len(pts)
    c = min(chamfer, (z1 - z0) * 0.9)
    rings = [(pts, z0)]
    if c > 0:
        normals = []
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            dx, dy = x1 - x0, y1 - y0
            ln = math.hypot(dx, dy) or 1.0
            normals.append((-dy / ln, dx / ln))  # inward for a counter-clockwise outline
        inset = []
        for i in range(n):
            a, b = normals[i - 1], normals[i]
            d = 1 + a[0] * b[0] + a[1] * b[1]
            inset.append((pts[i][0] + (a[0] + b[0]) * c / d, pts[i][1] + (a[1] + b[1]) * c / d))
        rings += [(pts, z1 - c), (inset, z1)]
    else:
        rings.append((pts, z1))
    vr = [[bm.verts.new((x, y, z)) for x, y in ring] for ring, z in rings]
    bm.faces.new(list(reversed(vr[0])))
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(vr[-1])
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = False


def gear(bm, u, v, z0, z1, r_px, teeth, mat):
    """A toothed disc standing on z0: 2 * teeth rim points alternating between r and 0.82 r."""
    start = len(bm.faces)
    cx, cy = G.x(u), G.y(v)
    m = 2 * teeth
    rim = []
    for k in range(m):
        a = 2 * math.pi * k / m
        r = r_px * PX * (1.0 if k % 2 == 0 else 0.82)
        rim.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    bot = [bm.verts.new((x, y, z0)) for x, y in rim]
    top = [bm.verts.new((x, y, z1)) for x, y in rim]
    c0, c1 = bm.verts.new((cx, cy, z0)), bm.verts.new((cx, cy, z1))
    for k in range(m):
        j = (k + 1) % m
        bm.faces.new((bot[k], bot[j], top[j], top[k]))
        bm.faces.new((c1, top[k], top[j]))
        bm.faces.new((c0, bot[j], bot[k]))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_123", **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.4, roughness=0.4),  # 0 grey head and lower housing
        pal(10, metallic=0.4, roughness=0.35),  # 1 grey hip domes and tube frame
        pal(8, metallic=0.4, roughness=0.4),  # 2 grey leg columns and arch panels
        pal(5, metallic=0.35, roughness=0.5),  # 3 dark grey feet
        pal(2, metallic=0.2, roughness=0.7),  # 4 dark channel and bay floor
        pal(155, metallic=0.0, roughness=0.08, emission_strength=0.9),  # 5 glowing glass tube
        pal(156, metallic=0.0, roughness=0.08, emission_strength=0.9),  # 6 square head light
        pal(132, metallic=0.5, roughness=0.3),  # 7 blue inner strips
        pal(132, metallic=0.0, roughness=0.15, emission_strength=0.7),  # 8 glowing pipes, foot rims
        pal(159, metallic=0.0, roughness=0.1, emission_strength=2.0),  # 9 head light's hot core
        pal(6, metallic=0.4, roughness=0.4),  # 10 dark frames: light bezel, collars, shafts
        pal(3, metallic=0.5, roughness=0.45),  # 11 dark gear in the bay
        pal(13, metallic=0.5, roughness=0.3),  # 12 bright ring bands on the hips
    ]
    CAP, HIP, LEG, FOOT, FLOOR, TUBE, LIGHT, STRIP, GLOW, CORE, FRAME, GEAR, BAND = range(13)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    start = len(bm.faces)
    # Hip (columns 14-19, rows 7-10): a domed cap on top of the leg, round across, its top end
    # rounding down (rows 6.7-8), a bright ring band (row 9) and a darker collar below it.
    lib.dloft(bm, G, 16.6, [(6.75, 1.3, 0.34), (7.1, 2.2, 0.46), (7.8, 2.62, 0.52), (10.4, 2.62, 0.52)],
              sides=10, mat=HIP, power=2.2)
    lib.dloft(bm, G, 16.6, [(8.6, 2.74, 0.545), (9.35, 2.74, 0.545)], sides=10, mat=BAND, power=2.2)
    lib.dloft(bm, G, 16.6, [(9.7, 2.7, 0.535), (10.4, 2.7, 0.535)], sides=10, mat=FRAME, power=2.2)
    # Leg column (columns 14-18, rows 10-24): round, constant width, sloping down into the foot.
    lib.dloft(bm, G, 16.2, [(10.2, 2.15, 0.45), (14.0, 2.15, 0.43), (18.5, 2.15, 0.37), (21.5, 2.0, 0.29),
                            (24.0, 1.7, 0.22)], sides=10, mat=LEG, power=2.3)
    # Arch panel down the leg's inner side (columns 18-19), framing the bay, with a blue strip
    # along the leg's inner edge (column 18, rows 14-24).
    cprism(bm, [(18.0, 10.6), (19.7, 11.6), (19.7, 19.6), (18.0, 20.6)], 0.0, 0.31, LEG, chamfer=0.04)
    lib.sweep(bm, G, [(18.25, 14.2, 0.31, 0.0, 0.0), (18.25, 14.6, 0.315, 0.38, 0.035),
                      (18.25, 19.6, 0.31, 0.38, 0.035), (18.25, 20.6, 0.24, 0.38, 0.035),
                      (18.25, 24.0, 0.2, 0.38, 0.035), (18.25, 24.4, 0.195, 0.0, 0.0)], sides=6, mat=STRIP)
    # Glowing pipe of one diameter: out of the hip collar along row 11, down column 13 to row 16,
    # and back into the leg.
    lib.sweep(bm, G, [(17.6, 11.1, 0.43, 0.55, 0.046), (14.2, 11.1, 0.4, 0.55, 0.046),
                      (13.4, 11.35, 0.37, 0.55, 0.046), (13.05, 12.0, 0.34, 0.55, 0.046),
                      (13.05, 15.6, 0.3, 0.55, 0.046), (13.4, 16.3, 0.29, 0.55, 0.046),
                      (14.1, 16.55, 0.29, 0.55, 0.046), (15.0, 16.55, 0.29, 0.55, 0.046)], sides=8, mat=GLOW)
    # Foot (columns 12-18, rows 19-27): a low dark axe-blade, its outer edge curving round to the
    # bottom, with a glowing blue rim set along the curve.
    cprism(bm, [(12.0, 19.5), (13.4, 19.0), (19.2, 19.0), (19.2, 27.9), (14.3, 27.9), (13.0, 27.0),
                (12.25, 25.7), (12.0, 24.4)], 0.0, 0.2, FOOT, chamfer=0.045)
    lib.sweep(bm, G, [(12.75, 20.0, 0.19, 0.0, 0.0), (12.75, 20.4, 0.19, 0.55, 0.04),
                      (12.8, 23.3, 0.19, 0.55, 0.04), (13.3, 24.9, 0.19, 0.55, 0.04),
                      (14.4, 26.2, 0.19, 0.55, 0.04), (16.0, 26.75, 0.19, 0.55, 0.04),
                      (18.4, 26.75, 0.19, 0.55, 0.04), (18.8, 26.75, 0.19, 0.0, 0.0)], sides=6, mat=GLOW)
    lib.mirror_from(bm, start, G.x(AXIS))

    # ---- centre parts ----
    # Head housing (columns 18-27, rows 0-5): the tallest part, chamfered, over a wider lower
    # housing whose shoulders slope out at rows 5-6 and which runs down to the bay's arch (row 13.6).
    cprism(bm, [(19.0, 0.05), (27.0, 0.05), (27.95, 1.0), (27.95, 5.3), (18.05, 5.3), (18.05, 1.0)],
           0.0, 0.62, CAP, chamfer=0.07)
    cprism(bm, [(17.4, 4.6), (28.6, 4.6), (29.5, 5.7), (29.5, 12.8), (28.6, 13.7), (17.4, 13.7),
                (16.5, 12.8), (16.5, 5.7)], 0.0, 0.38, CAP, chamfer=0.05)
    # Square light (columns 21-24, rows 1-4) in a raised dark bezel, with a hot core.
    cprism(bm, [(20.7, 0.8), (25.3, 0.8), (25.3, 5.0), (20.7, 5.0)], 0.5, 0.67, FRAME, chamfer=0.03)
    cprism(bm, [(21.2, 1.25), (24.8, 1.25), (24.8, 4.55), (21.2, 4.55)], 0.6, 0.675, LIGHT, chamfer=0.02)
    cprism(bm, [(22.2, 2.2), (23.8, 2.2), (23.8, 3.6), (22.2, 3.6)], 0.6, 0.682, CORE, chamfer=0.01)
    # Tube frame (columns 20-25, rows 5-14): two rails and two end caps round a dark channel.
    cprism(bm, [(20.0, 5.0), (21.4, 5.0), (21.4, 13.9), (20.0, 13.9)], 0.3, 0.5, HIP, chamfer=0.03)
    cprism(bm, [(24.6, 5.0), (26.0, 5.0), (26.0, 13.9), (24.6, 13.9)], 0.3, 0.5, HIP, chamfer=0.03)
    cprism(bm, [(21.4, 5.0), (24.6, 5.0), (24.6, 6.0), (21.4, 6.0)], 0.3, 0.5, HIP, chamfer=0.03)
    cprism(bm, [(20.6, 12.9), (25.4, 12.9), (25.4, 14.0), (24.6, 14.3), (21.4, 14.3), (20.6, 14.0)],
           0.0, 0.48, HIP, chamfer=0.04)
    cprism(bm, [(21.4, 6.0), (24.6, 6.0), (24.6, 12.9), (21.4, 12.9)], 0.3, 0.385, FLOOR)
    # Glowing glass tube (columns 21-24, rows 6-13): round, as tall as it is wide, rounded ends.
    lib.sweep(bm, G, [(AXIS, 6.0, 0.4, 0.0, 0.0), (AXIS, 6.3, 0.4, 0.9, 0.07), (AXIS, 6.8, 0.4, 1.25, 0.1),
                      (AXIS, 12.3, 0.4, 1.25, 0.1), (AXIS, 12.8, 0.4, 0.9, 0.07), (AXIS, 13.0, 0.4, 0.0, 0.0)],
              sides=10, mat=TUBE)
    # Machinery bay under the arch (columns 19-26, rows 13-20): a low dark floor holding a toothed
    # gear, a crank shaft across to a round boss, and a short shaft below the tube.
    cprism(bm, [(19.6, 13.4), (26.4, 13.4), (26.4, 18.6), (25.8, 19.8), (25.0, 21.0), (21.0, 21.0),
                (20.2, 19.8), (19.6, 18.6)], 0.0, 0.08, FLOOR)
    gear(bm, 21.9, 17.2, 0.08, 0.2, 1.75, 10, GEAR)
    lib.cylinder(bm, G, 21.9, 17.2, 0.2, 0.26, 0.7, mat=FRAME, sides=8)
    lib.sweep(bm, G, [(22.6, 17.1, 0.17, 0.75, 0.065), (26.2, 17.1, 0.17, 0.75, 0.065)], sides=8, mat=FRAME)
    lib.cylinder(bm, G, 24.9, 17.1, 0.08, 0.27, 1.1, mat=LEG, sides=10)
    lib.sweep(bm, G, [(AXIS, 14.0, 0.2, 0.6, 0.05), (AXIS, 15.8, 0.15, 0.6, 0.05)], sides=8, mat=FRAME)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.assembly_main(ROOT, NAME, build, PIECES, CX0, CY0, preview_tiles=2)


if __name__ == "__main__":
    main()
