"""Grey drilling machine (newsh2.shp frame 267): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). Seen from above it lies along the
screen with its drill pointing down: a riveted steel capsule head at the top end with a collar
ring, a brass armour collar wrapping the drum's shoulders (lighter brass pads on the inner top
corners), a dark spine plate down the middle framing two glowing red arched light slots, faceted
steel drum plates below the armour, and a conical drill bit wrapped in thin spiral flights coming
to a point at the bottom. A flat axle bar crosses through the head to a brass yoke on each side:
an armoured link plate angling down and out to a pivot block, then twin grey piston rods lying on
the ground to a brass foot. The parts are placed where the concept
(assets/blender/features/concepts/newsh2-267.jpg, registered as textures/newsh2-267/concept.png)
draws them, so texture_bake.py's detail lands on the matching part. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-267.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "newsh2-267"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AXIS = 11.5  # the sprite is symmetric about the centre of column 11
PX = lib.PX

# Loft sections (row edge, half width px, top z), traced from the concept inside the sprite.
COLLAR = [(8.1, 5.3, 0.5), (8.7, 6.0, 0.6), (9.5, 6.8, 0.63), (10.1, 7.45, 0.64), (12.4, 7.45, 0.64),
          (12.95, 7.1, 0.57)]
COLLAR_POW = 3.0
DRUM = [(12.3, 7.2, 0.6), (17.6, 7.35, 0.6), (18.4, 7.1, 0.57)]
CONE = [(16.0, 7.2, 0.58), (18.6, 7.1, 0.57), (19.3, 6.55, 0.54), (20.4, 5.9, 0.5), (21.6, 5.2, 0.45),
        (23.0, 4.4, 0.38), (24.2, 3.45, 0.3), (25.2, 2.5, 0.22), (26.2, 1.5, 0.14), (27.3, 0.6, 0.07),
        (27.95, 0.1, 0.02)]
CONE_POW = 2.0


def surface(sections, power, u, v):
    """Height of a dloft's top surface (round/boxy superellipse) at edge point (u, v), and its
    half width there."""
    if v <= sections[0][0]:
        hw, zt = sections[0][1], sections[0][2]
    elif v >= sections[-1][0]:
        hw, zt = sections[-1][1], sections[-1][2]
    else:
        for (v0, h0, z0), (v1, h1, z1) in zip([s[:3] for s in sections], [s[:3] for s in sections[1:]]):
            if v0 <= v <= v1:
                t = (v - v0) / (v1 - v0)
                hw, zt = h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
                break
    e = 2 / power
    q = min(abs(u - AXIS) / hw, 1.0)
    c = q ** (1 / e)
    s = math.sqrt(max(0.0, 1 - c * c))
    return zt * s ** e, hw


def shape_top(bm, start, ztop):
    """Raise or lower the top of the parts added since face `start`: vertices above z = 0.5 get
    z = ztop(u, v) minus how far below 1.0 they were (keeps chamfers)."""
    bm.faces.ensure_lookup_table()
    verts = {v for f in bm.faces[start:] for v in f.verts}
    for vt in verts:
        if vt.co.z > 0.5:
            u = vt.co.x / PX + G.w / 2
            v = G.h / 2 - vt.co.y / PX
            vt.co.z = ztop(u, v) - (1.0 - vt.co.z)


def conformed_plate(bm, outline, lift, sections, power, mat, z0=0.0):
    """A hard plate over (u, v) outline whose top follows a loft's surface, `lift` above it."""
    start = len(bm.faces)
    lib.plate(bm, G, outline, z0, 1.0, mat=mat)
    shape_top(bm, start, lambda u, v: surface(sections, power, u, v)[0] + lift)


def sym(pts):
    """(offset px from the axis, row) to (u, v)."""
    return [(AXIS + du, v) for du, v in pts]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_267", **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.4),  # 0 steel drum and drill bit
        pal(11, metallic=0.65, roughness=0.28),  # 1 shiny steel head
        pal(3, metallic=0.3, roughness=0.25),  # 2 dark glossy spine plate
        pal(119, emission_strength=3.0),  # 3 red lights
        pal(121, emission_strength=4.5),  # 4 hot centre of the lights
        pal(23, metallic=0.5, roughness=0.4),  # 5 brass yoke
        pal(9, metallic=0.6, roughness=0.35),  # 6 grey axle, piston rods
        pal(24, metallic=0.5, roughness=0.4),  # 7 brass armour collar
        pal(27, metallic=0.5, roughness=0.35),  # 8 light brass inner pads
        pal(26, metallic=0.45, roughness=0.4),  # 9 tan rib
        pal(10, metallic=0.6, roughness=0.35),  # 10 light steel plates, flights
    ]
    HULL, HEAD, SPINE, RED, HOT, YOKE, ROD, PAD, INNER, TAN, PLATE = range(11)
    bm = bmesh.new()

    # --- drill: faceted armoured drum (rows 12-18) and the conical bit to the point (row 28) ----
    lib.dloft(bm, G, AXIS, CONE, sides=16, mat=HULL, power=CONE_POW)
    lib.dloft(bm, G, AXIS, DRUM, sides=12, mat=HULL, power=2.6, smooth=False)
    # Thin spiral flights round the bit, running down to the left across its top (a helix: half a
    # turn drops about 4 rows), hard-edged blades.
    for v_right in (15.6, 17.3, 19.0, 20.7, 22.4, 24.1):
        path = []
        n = 12
        for k in range(n + 1):
            a = 0.1 * math.pi + 0.8 * math.pi * k / n
            v = v_right + 4.0 * a / math.pi
            if v > 27.3:
                break
            zt, hw = surface(CONE, CONE_POW, AXIS, v)
            ca, sa = math.cos(a), math.sin(a)
            x = hw * ca
            z = zt * abs(sa) + 0.015
            if v < 18.4:  # still under the drum
                zd, hd = surface(DRUM, 2.6, AXIS, v)
                if abs(x) < hd - 0.3:
                    continue
            path.append((AXIS + x, v, z, 0.28, 0.045))
        if len(path) >= 2:
            lib.sweep(bm, G, path, sides=4, mat=PLATE, smooth=False)

    # Light steel plates either side of the spine on the drum (concept: cols 7.5-9.4, rows 12.6-16.5).
    for s in (-1, 1):
        conformed_plate(bm, sym([(s * 2.3, 12.5), (s * 4.3, 12.5), (s * 4.3, 16.2), (s * 3.6, 16.8),
                                 (s * 2.3, 16.8)]), 0.035, DRUM, 2.6, PLATE)
    # Tan rib down the centre of the drum below the spine (the sprite's stud) and the light cross
    # ridge it starts from.
    lib.sweep(bm, G, [(AXIS, 14.2, 0.6, 0.0, 0.0), (AXIS, 14.5, 0.62, 0.55, 0.04),
                      (AXIS, 18.2, 0.59, 0.5, 0.035), (AXIS, 19.2, 0.54, 0.0, 0.0)], sides=4, mat=TAN, smooth=False)
    lib.box(bm, G, AXIS - 2.3, 14.9, AXIS + 2.3, 15.7, 0.0, 0.64, mat=PLATE, chamfer=0.03)

    # --- brass armour collar round the drum's shoulders (rows 8-13) ---------------------------
    lib.dloft(bm, G, AXIS, COLLAR, sides=12, mat=PAD, power=COLLAR_POW, smooth=False)
    for s in (-1, 1):
        # Inner upper pad (concept cols 6.2-9.4, rows 8.2-12.3), the lit brass of the sprite.
        conformed_plate(bm, sym([(s * 2.3, 8.15), (s * 5.0, 8.15), (s * 5.6, 8.9), (s * 5.6, 11.4),
                                 (s * 4.9, 12.3), (s * 2.3, 12.3)]), 0.05, COLLAR, COLLAR_POW, INNER)
        # Outer pad on the shoulder's flank (concept cols 4.2-6.6, rows 9.8-12.4).
        conformed_plate(bm, sym([(s * 5.75, 9.6), (s * 6.7, 9.6), (s * 7.5, 10.4), (s * 7.5, 12.5),
                                 (s * 5.75, 12.5)]), 0.03, COLLAR, COLLAR_POW, PAD)

    # --- dark spine plate with the two arched red light slots (rows 7-14) ---------------------
    spine = [(-1.3, 7.3), (1.3, 7.3), (2.4, 8.1), (2.4, 13.6), (1.7, 14.3), (-1.7, 14.3), (-2.4, 13.6),
             (-2.4, 8.1)]
    lib.plate(bm, G, sym(spine), 0.3, 0.665, mat=SPINE)

    def arch(v0, v1):
        """An arched slot: top edge rows v0 (centre) to v0+0.55 (ends), bottom v1-0.35 to v1+0.2."""
        return [(-2.0, v0 + 0.55), (-1.2, v0), (1.2, v0), (2.0, v0 + 0.55), (2.0, v1 + 0.2), (1.2, v1 - 0.35),
                (-1.2, v1 - 0.35), (-2.0, v1 + 0.2)]

    def top_edge(v0):
        return [(-2.0, v0 + 0.55), (-1.2, v0), (1.2, v0), (2.0, v0 + 0.55)]

    def bottom_edge(v1):
        return [(-2.0, v1 + 0.2), (-1.2, v1 - 0.35), (1.2, v1 - 0.35), (2.0, v1 + 0.2)]

    L1, L2 = (8.95, 10.15), (10.85, 12.05)
    frame = [
        [(-1.3, 7.3), (1.3, 7.3), (2.4, 8.1), (2.4, L1[0] + 0.55)] + top_edge(L1[0])[::-1] + [(-2.4, L1[0] + 0.55),
                                                                                            (-2.4, 8.1)],
        bottom_edge(L1[1]) + top_edge(L2[0])[::-1],
        [(-2.4, L2[1] + 0.2)] + bottom_edge(L2[1]) + [(2.4, L2[1] + 0.2), (2.4, 13.6), (1.7, 14.3), (-1.7, 14.3),
                                                     (-2.4, 13.6)],
        [(-2.4, L1[0] + 0.55), (-2.0, L1[0] + 0.55), (-2.0, L2[1] + 0.2), (-2.4, L2[1] + 0.2)],
        [(2.0, L1[0] + 0.55), (2.4, L1[0] + 0.55), (2.4, L2[1] + 0.2), (2.0, L2[1] + 0.2)],
    ]
    for piece in frame:
        lib.plate(bm, G, sym(piece), 0.6, 0.72, mat=SPINE)
    for v0, v1 in (L1, L2):
        lib.plate(bm, G, sym(arch(v0, v1)), 0.6, 0.685, mat=RED)
        lib.plate(bm, G, sym([(-1.0, v0 + 0.25), (1.0, v0 + 0.25), (1.0, v1 - 0.45), (-1.0, v1 - 0.45)]),
                  0.6, 0.69, mat=HOT)

    # --- head: a lying steel capsule end (rows 2-8) with a collar ring, the highest part --------
    head = [(1.95, 2.3, 0.55), (2.4, 3.1, 0.63), (3.0, 3.65, 0.69), (3.8, 3.95, 0.72), (4.5, 4.05, 0.73),
            (8.6, 4.05, 0.73)]
    lib.dloft(bm, G, AXIS, head, sides=16, mat=HEAD, power=2.2)
    lib.dloft(bm, G, AXIS, [(6.3, 4.4, 0.75), (7.3, 4.4, 0.75)], sides=16, mat=HEAD, power=2.2, smooth=False)
    # Flat axle bar across the head (row 5) out to the yoke, with clamp bolts at its ends.
    lib.box(bm, G, 4.4, 4.6, 18.6, 6.2, 0.34, 0.5, mat=ROD, chamfer=0.025)

    # --- left side of the yoke (mirrored) ----------------------------------------------------
    start = len(bm.faces)
    arm = [(4.0, 2.0), (5.9, 2.0), (5.9, 3.3), (5.6, 4.6), (4.9, 6.4), (4.5, 7.6), (3.6, 8.8), (3.0, 9.8),
           (0.15, 9.8), (0.15, 8.4), (1.1, 7.0), (2.1, 5.0), (3.0, 3.2), (4.0, 3.0)]
    arm_z = lambda u, v: 0.6 - 0.032 * (v - 2.0)  # noqa: E731
    s0 = len(bm.faces)
    lib.plate(bm, G, arm, 0.16, 1.0, mat=YOKE)
    shape_top(bm, s0, arm_z)
    # Raised inner panel along the link.
    s0 = len(bm.faces)
    lib.plate(bm, G, [(4.3, 3.4), (5.3, 3.4), (4.7, 5.5), (3.8, 7.5), (2.6, 9.2), (1.3, 9.2), (2.5, 7.1),
                      (3.4, 5.2)], 0.16, 1.0, mat=YOKE)
    shape_top(bm, s0, lambda u, v: arm_z(u, v) + 0.035)
    # Clamp bolt where the axle meets the link, and the pivot bolt on the leg block.
    lib.cylinder(bm, G, 4.7, 5.4, 0.3, 0.6, 0.65, mat=ROD, sides=8)
    lib.cylinder(bm, G, 1.4, 9.6, 0.2, 0.36, 0.6, mat=ROD, sides=8)
    # Pivot block at the top of the legs and the brass foot.
    lib.box(bm, G, 0.15, 9.0, 3.0, 10.6, 0.0, 0.32, mat=YOKE, chamfer=0.035)
    lib.box(bm, G, 0.2, 17.2, 3.0, 18.95, 0.0, 0.22, mat=YOKE, chamfer=0.035)
    # Twin grey piston rods lying on the ground between them, a thicker sleeve at the top.
    for u in (0.95, 2.1):
        lib.sweep(bm, G, [(u, 10.4, 0.12, 0.62, 0.075), (u, 12.0, 0.12, 0.62, 0.075),
                          (u, 12.05, 0.12, 0.6, 0.06), (u, 17.4, 0.12, 0.6, 0.06)], sides=8, mat=ROD)
    lib.mirror_from(bm, start, G.x(AXIS))

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
