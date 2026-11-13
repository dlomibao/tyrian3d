"""Mace chain rings (newsha.shp frames 87, 125, 127), design A: forged round-link steel rings.

What they are: the links of the flail chains in 3.12 MACES and 3.3 GAUNTLET. Each spiked ball
(assembly-newsha-115) hangs off a tan ball-turret bunker (assembly-newsha-121) by a chain of three
rings that grow from the hub out: 87 (17 px), 125 (21 px), 127 (24 px). ev19/20/27 swing them at
2 / 4 / 6 px per tick, in proportion to their distance from the hub, so the chain turns rigidly
about the bunker (checked in the game capture at main=25, tick 180: bunker, three rings, ball).

The sprite is a flat ring lit from the upper left: bright on the outer upper-left face and on the
inner lower-right face, dark on the opposite faces, so a round tube (a torus lying flat). The ink
rings (index 1) inside and outside are the outline; the game's own ink draws both. Plan: circles
fitted to the rule's inner mask (ringfit.py: every pixel matches at radii in the windows below;
the radii sit in the middle of each window). The tube is a slightly full (superellipse 2.4)
round section, as tall as it is wide, resting on z = 0.

Detail where the camera sees it: the forge weld of a round-link chain, a collar between two
machined grooves on the lower-right (south-east) side of each ring, and a fine flash line round
the tube's crown. Satin forged steel in the sprite's median grey (trimmed median of each ring's
colour pixels: 87 -> 5, 125 -> 7, 127 -> 7); the light and dark bands are lighting. Underside: the
same closed tube.

One frame each. Exports newsha-87_A.glb (and the merged siblings newsha-125_A.glb,
newsha-127_A.glb) beside this script only.

Library for newsha-87.py, newsha-125.py, newsha-127.py (each calls lib_b107.main(NAME)).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
PX = 1 / 12
W, H = 24, 28

# name: (centre col, centre row (pixel edges), r_in, r_out (px), palette index, weld angle (deg))
RINGS = {
    "newsha-87": (12.5, 14.5, 5.55, 7.45, 5, -40.0),
    "newsha-125": (12.5, 14.5, 7.45, 9.675, 7, -40.0),
    "newsha-127": (12.0, 14.0, 7.725, 10.875, 7, -40.0),
}
SIDES = 18          # stations round the tube's section
SUPER = 2.4         # section superellipse exponent (2 = round)
TALL = 1.0          # section half height / half width
GROOVE_W = 0.32     # groove width along the ring, px
GROOVE_D = 0.16     # groove depth, as a share of the tube's half width
COLLAR = 1.5        # distance between the two grooves (the weld collar), px
COLLAR_SWELL = 0.04  # the collar's swell (share of half width; small, keeps the plan)
FLASH_W = 0.12      # crown flash line: half width in section angle (rad)
FLASH_H = 0.035     # its rise (share of half width)


def P(u, v, z):
    return ((u - W / 2) * PX, (H / 2 - v) * PX, z * PX)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def section_scale(s, s_weld):
    """Section scale at arc position s (px along the centre line), from the weld's grooves/collar."""
    d = s - s_weld
    k = 1.0
    for g in (-COLLAR / 2, COLLAR / 2):
        x = abs(d - g) / (GROOVE_W / 2)
        if x < 1.0:
            k -= GROOVE_D * (0.5 + 0.5 * math.cos(math.pi * x))  # a rounded V groove
    if abs(d) < COLLAR / 2 - GROOVE_W / 2:
        k += COLLAR_SWELL * (1 - smoothstep(COLLAR / 2 - GROOVE_W, COLLAR / 2 - GROOVE_W / 2, abs(d)))
    return k


def stations(rc, weld_deg):
    """Angles round the ring: every 4 degrees, dense through the weld."""
    circ = 2 * math.pi * rc
    s_weld = math.radians(weld_deg) % (2 * math.pi) * rc
    pts = set()
    n = 90
    for i in range(n):
        pts.add(round(circ * i / n, 5))
    lo, hi = s_weld - COLLAR / 2 - GROOVE_W, s_weld + COLLAR / 2 + GROOVE_W
    s = lo
    while s <= hi:
        pts.add(round(s % circ, 5))
        s += 0.09
    out = sorted(pts)
    # drop uniform stations that crowd the dense run
    keep = []
    for s in out:
        if keep and s - keep[-1] < 0.06:
            continue
        keep.append(s)
    return keep, s_weld, circ


def ring_mesh(name, bm, spec):
    cu, cv, ri, ro, _, weld = spec
    rc, a = (ri + ro) / 2, (ro - ri) / 2
    b = a * TALL
    ss, s_weld, circ = stations(rc, weld)
    rings = []
    for s in ss:
        th = s / rc
        d = s - s_weld
        if d > circ / 2:
            d -= circ
        if d < -circ / 2:
            d += circ
        k = section_scale(d + s_weld, s_weld)
        ring = []
        for j in range(SIDES):
            ph = 2 * math.pi * j / SIDES
            c, sn = math.cos(ph), math.sin(ph)
            ex = math.copysign(abs(c) ** (2 / SUPER), c)
            ez = math.copysign(abs(sn) ** (2 / SUPER), sn)
            # crown flash line: a fine ridge along the top of the tube
            dphi = abs(((ph - math.pi / 2) + math.pi) % (2 * math.pi) - math.pi)
            lift = FLASH_H * max(0.0, 1 - dphi / FLASH_W) if dphi < FLASH_W else 0.0
            r = rc + a * k * ex * (1 + lift)
            z = b + b * k * ez * (1 + lift)
            ring.append(bm.verts.new(P(cu + r * math.cos(th), cv - r * math.sin(th), z)))
        rings.append(ring)
    n = len(rings)
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(SIDES):
            jj = (j + 1) % SIDES
            bm.faces.new((r0[j], r1[j], r1[jj], r0[jj]))
    return n


def sink_shell(shell, model, margin, reach):
    """Copied from newshv-10.py (D185): drop every shell vertex to `margin` under the lowest model top
    within `reach` (seen from above), so the outline's ink stays on the silhouette."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            an = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(an), w.y + rad * math.sin(an), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def build(name):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, name)
    spec = RINGS[name]
    coll = common.reset_collection(name)
    mat = common.palette_material(sprite, spec[4], name, metallic=0.3, roughness=0.3)
    bm = bmesh.new()
    ring_mesh(name, bm, spec)
    obj = common.mesh_object(name, bm, [mat], coll, smooth=True)
    # D90/D118: the shell from a sealed copy (the ring is one closed island; nothing culled).
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.008, faces=1600, inside=0.003)
    sink_shell(shell, sealed, 0.3 * PX, 0.6 * PX)
    shell.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    assert len(shell.data.polygons) > 0, "empty outline shell"
    common.export_sprite_model(WT, [obj, shell], f"enemies/{name}", sprite["sprites"])
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{name}: model triangles {tris}, shell faces {len(shell.data.polygons)}")


def main(name):
    build(name)
