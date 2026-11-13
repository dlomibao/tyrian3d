"""Red spiked mine (newsh5.shp frame 76): a 3D version of its sprite.

Seen in episode 4 (BRAINIAC, level 22): ground-fixed or weaving mines that launch copies of
themselves sideways, so the same model is also the projectile. The sprite is a glossy red ball
(palette 117 at its median) with a long spike up and down, a short one left and right, bright
shoulders on the four diagonals and one black pit just below the centre. Its orange-white band
across the upper half is sheen on the glossy shell and its dark lower rows and black ring are
shading and outline (art rule 2): one mid red, lit by the game.

What it is, built as such: a welded steel contact mine. Two hemispheres of a pressed shell meet at
an equatorial weld seam (a modelled groove); the four spikes are turned cones on bolted base collars; the four bright shoulders are
short Hertz horns (stem plus rounded lead cap) raised 20 degrees on the diagonals; the pit is a
detonator port, a black socket inside a raised collar ring, on the upper front face where the
sprite draws it (column 5, row 8). Underside: the plain lower hemisphere with a small flat plug.

    blender --background --python assets/blender/enemies/newsh5-76.py

Exports public/models/enemies/newsh5-76.glb and its spriteModels entry (mesh + outline shell,
pal_<index> materials). Set TYRIAN_REVIEW_GLB=<path> to also write a copy there (review only).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT

NAME = "newsh5-76"
MODEL = f"enemies/{NAME}"
P = 1 / 12  # one sprite pixel
W, H = 12, 14
# Ball centre: column 5, row 6 (the inner mask spans columns 1-9 and rows 1-11 round it).
CX = (5 + 0.5 - W / 2) * P
CY = (H / 2 - (6 + 0.5)) * P
R = 4.35 * P  # ball radius


def revolve(bm, profile, origin, axis, sides, mats, phase=0.5):
    """A solid of revolution round `axis` through `origin`. `profile` is [(radius, d)] along the axis
    (radius 0 = a pole vertex); `mats` is one material slot or one per profile segment."""
    axis = Vector(axis).normalized()
    origin = Vector(origin)
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for rad, d in profile:
        c = origin + axis * d
        if rad <= 0:
            rings.append([bm.verts.new(c)])
            continue
        rings.append([bm.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * rad)
                      for a in (2 * math.pi * (k + phase) / sides for k in range(sides))])
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        mi = mats if isinstance(mats, int) else mats[i]
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = mi
    m0 = mats if isinstance(mats, int) else mats[0]
    m1 = mats if isinstance(mats, int) else mats[-1]
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = m0
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = m1


def body_profile():
    """(radius, z) of the shell from the top pole down: the upper hemisphere, the equatorial weld groove, the lower hemisphere, a small flat bottom plug."""
    pts = []
    sph = lambda a: (R * math.sin(a), R * math.cos(a))  # noqa: E731
    g = 0.11 * P  # groove depth
    # No hatch on top (in game a second ring beside the port read as a face): a plain dome.
    pts.append((0.0, R))
    a0 = 0.0
    a1 = math.acos(0.16 * P / R)  # stop just above the weld groove
    n = 17
    for i in range(1, n + 1):
        pts.append(sph(a0 + (a1 - a0) * i / n))
    # Weld groove round the equator: 0.2 px tall, a bead line between two chamfers.
    pts += [(R - 0.03 * P, 0.11 * P), (R - g, 0.07 * P), (R - g, -0.07 * P), (R - 0.03 * P, -0.11 * P)]
    b0 = math.acos(-0.16 * P / R)
    b1 = math.pi - math.asin(0.7 * P / R)
    n = 11
    for i in range(n + 1):
        pts.append(sph(b0 + (b1 - b0) * i / n))
    zb = -math.sqrt(R * R - (0.7 * P) ** 2)
    pts += [(0.62 * P, zb - 0.04 * P), (0.0, zb - 0.04 * P)]
    return pts


def spike_profile(base_r, tip):
    """(radius, d) of a spike on its bolted collar: the collar starts inside the shell, stands
    0.1-0.3 px proud of it, chamfered; the cone springs from a small neck and ends in a blunted tip."""
    c = 1.45 * P
    return [(0.0, 3.55 * P), (c, 3.55 * P), (c, 4.30 * P), (c - 0.08 * P, 4.40 * P), (1.15 * P, 4.42 * P),
            (base_r, 4.48 * P), (base_r * 0.66, 4.48 * P + (tip - 4.48 * P) * 0.36),
            (0.10 * P, tip - 0.10 * P), (0.0, tip)]


def horn_profile():
    """(radius, d) of a Hertz horn: a stem, a seating ring, and a rounded lead cap."""
    return [(0.0, 3.7 * P), (0.42 * P, 3.7 * P), (0.42 * P, 4.40 * P), (0.54 * P, 4.44 * P), (0.58 * P, 4.54 * P),
            (0.56 * P, 4.72 * P), (0.46 * P, 4.88 * P), (0.28 * P, 4.99 * P), (0.0, 5.03 * P)]


def build(sprite, coll, proxy=False):
    """The mine; `proxy`: only the ball and the spikes, the sealed copy the outline shell is made
    from, so the port boss and the horn bases leave no ink rings in their creases (D51)."""
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(117, metallic=0.45, roughness=0.2),  # 0 glossy red painted steel: shell, spikes, horns
        pal(1, metallic=0.0, roughness=0.85),  # 1 the black detonator socket
    ]
    SHELL, PIT = 0, 1
    bm = bmesh.new()
    c = Vector((CX, CY, 0.0))

    # body_profile runs top-down as (radius, z); revolve measures d along -Z, so d = -z.
    if proxy:
        prof = [(R * math.sin(a), -R * math.cos(a)) for a in (math.pi * i / 24 for i in range(25))]
        prof[0], prof[-1] = (0.0, prof[0][1]), (0.0, prof[-1][1])
        revolve(bm, prof, (CX, CY, 0.0), (0, 0, -1), 48, SHELL)
    else:
        revolve(bm, [(r, -z) for r, z in body_profile()], (CX, CY, 0.0), (0, 0, -1), 48, SHELL)
    # Spikes on the equator: up and down 6.6 px from the centre, through rows 1 and 11 into the tip
    # ink of rows 0 and 12 (thin-part border, counted neither way), left and right 5.6 px (columns 1
    # and 9 and the lone red pixel of column 10). Full length, so they survive the game's ink.
    for (dx, dy), base_r, tip in (((0, 1), 1.2 * P, 6.6 * P), ((0, -1), 1.2 * P, 6.6 * P),
                                  ((-1, 0), 1.1 * P, 5.6 * P), ((1, 0), 1.1 * P, 5.6 * P)):
        revolve(bm, spike_profile(base_r, tip), c, (dx, dy, 0), 14, SHELL)
    if proxy:
        return common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # Hertz horns on the diagonals, raised 20 degrees: the sprite's four bright shoulders.
    el = math.radians(20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        revolve(bm, horn_profile(), c, (math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)),
                10, SHELL)
    # Detonator port at column 5, row 8: 2 px in front of the centre, on the upper front face.
    n = Vector((0.0, -2.0 * P, math.sqrt(R * R - 4 * P * P))).normalized()
    # A raised boss (0.3 px proud) with the black socket's floor above the shell, so it shows.
    port = [(0.0, 3.95 * P), (0.80 * P, 3.95 * P), (0.80 * P, 4.52 * P), (0.73 * P, 4.60 * P),
            (0.62 * P, 4.60 * P), (0.56 * P, 4.55 * P), (0.54 * P, 4.40 * P), (0.0, 4.40 * P)]
    revolve(bm, port, c, n, 16, [SHELL] * 6 + [PIT])
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return obj


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    proxy = build(sprite, coll, proxy=True)
    shell = common.outline_shell(proxy, coll, voxel=0.006, faces=2500, smooth=2, inside=0.003, islands="outer")
    bpy.data.objects.remove(proxy, do_unlink=True)
    obj = build(sprite, coll)
    assert obj.name == NAME and shell.name == f"{NAME}_outline", (obj.name, shell.name)
    for o in (obj, shell):
        o["design_model"] = NAME
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"tris {tris} shell faces {len(shell.data.polygons)}")
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    review = os.environ.get("TYRIAN_REVIEW_GLB")
    if review:
        common.export_glb([obj, shell], review)


if __name__ == "__main__":
    main()
