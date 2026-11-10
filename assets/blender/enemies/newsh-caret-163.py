"""newsh-caret-163, the blue energy orb (newsh^.shp 163/165, newshm.shp 129/131), a 3D version of its
sprite with a hard-surface containment collar (D50-D53, D65), its top view on the inner edge of the sprite's ink
border (D74).

What the sprite shows (reference/models/newsh-caret-163, 24x28, palette 5, centred on column edge 12, row edge 14):
- Plan: a round ball, 18 px across on 163/129 (inner mask: a disc of radius ~8.6 px), 20 px on 165/131 (~9.7 px),
  ringed by a broken ink border (81, 50). The two pairs are the same drawing; the big frames are every band one
  pixel further out (a pulse).
- Bands from the centre out (small frame, top-view radius in px): white-hot core 143 (< 4.2), pale cyan 141
  (< 5.1), 139 with 137/138 (< 6.1), light blue 157 with 155/158 (< 7.2), deep blue 154 (< 7.9), then a one-pixel
  dark teal ring (52, 210, 211, 212, 53; median 211) inside the ink.

Design: a ball of plasma held in a machined containment collar. The ball (slightly oblate) glows in the sprite's
bands, each band cut at its exact top-view radius so the boundaries are clean circles; the dark teal ring is the
collar: a satin-metal band round the equator (chamfered top and bottom, a machined groove round its outer face),
whose top face is that one-pixel ring from above, with eight clamp shoes over it (chamfered blocks, a bolt head
on each) that grip the ball a little above and below the band. Underside: the ball's lower half in the deep blue,
closed; nothing modelled there. One model per pulse size (frame_part), each with its own outline shell.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh-caret-163.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull  # noqa: E402

NAME = "newsh-caret-163"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Sprite px: x across from the centre column edge (12), y = row edge (centre 14), z up. T.finish maps to units.
YC = 14.0
SEG = 48            # segments round the ball and collar

# Top-view radii on the small frame (163/129); the big frame (165/131) adds one pixel to every one.
R_OUT = 8.62        # the collar's outer edge: the inner mask's edge
R_BALL = 7.92       # the ball's equator (the collar shows 0.7 px outside it, the sprite's dark ring)
# The sprite's bands (core 143 < 4.2 | 141 < 5.1 | 139 < 6.1 | 157 < 7.2 | 154), with its own in-between
# shades (138 and 158 where 139 meets 157, 155 where 157 meets 154) as thin bands so the glow grades smoothly.
OBLATE = 0.86       # the ball's height over its radius

# Material slots.
CORE, C141, C139, C138, B158, B157, B155, RIM, COLLAR, SHOE, BOLT = range(11)
BANDS = ((4.2, CORE), (5.1, C141), (5.8, C139), (6.15, C138), (6.5, B158), (7.0, B157), (7.4, B155))


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    return [
        pal(143, metallic=0.0, roughness=0.6, emission_strength=2.0),    # CORE white-hot core
        pal(141, metallic=0.0, roughness=0.6, emission_strength=1.3),   # C141 pale cyan
        pal(139, metallic=0.0, roughness=0.6, emission_strength=1.0),   # C139 cyan
        pal(138, metallic=0.0, roughness=0.6, emission_strength=1.0),   # C138
        pal(158, metallic=0.0, roughness=0.6, emission_strength=0.0),    # B158
        pal(157, metallic=0.0, roughness=0.6, emission_strength=0.0),    # B157 light blue
        pal(155, metallic=0.0, roughness=0.6, emission_strength=0.0),    # B155
        pal(154, metallic=0.0, roughness=0.6, emission_strength=0.0),    # RIM deep blue rim (and the underside)
        pal(211, metallic=0.55, roughness=0.42),           # COLLAR dark teal satin metal
        pal(212, metallic=0.55, roughness=0.45),           # SHOE clamp shoes, a step lighter
        pal(210, metallic=0.6, roughness=0.38),            # BOLT bolt heads, a step darker
    ]


def ring(part, rho, z, seg=SEG, phase=0.0):
    return [part.v((rho * math.cos(phase + 2 * math.pi * i / seg), YC + rho * math.sin(phase + 2 * math.pi * i / seg), z))
            for i in range(seg)]


def ball(part, grow):
    """The plasma ball: latitude rings at even polar angles plus one at each band's exact top-view radius."""
    rs = R_BALL + grow * 1.1
    hz = OBLATE * rs
    bands = [(b + grow, m) for b, m in BANDS]
    # Polar angle t from the top pole; top-view radius rs*sin(t), height hz*cos(t).
    ts = [math.radians(a) for a in [i * 7.5 for i in range(25)]]
    for b, _ in bands:
        tb = math.asin(b / rs)
        ts = [t for t in ts if abs(t - tb) > math.radians(1.2)] + [tb]
    ts = sorted(ts)
    zc = 0.0
    top = part.v((0.0, YC, zc + hz))
    bot = part.v((0.0, YC, zc - hz))
    rings = [ring(part, rs * math.sin(t), zc + hz * math.cos(t)) for t in ts[1:-1]]

    def mat_at(t0, t1):
        if (t0 + t1) / 2 > math.pi / 2:
            return RIM
        rho = rs * math.sin((t0 + t1) / 2)
        return next((m for b, m in bands if rho < b), RIM)

    centre = (0.0, YC, zc)
    m0 = mat_at(ts[0], ts[1])
    for i in range(SEG):
        part.f([top, rings[0][i], rings[0][(i + 1) % SEG]], m0, away=centre)
    for k in range(len(rings) - 1):
        m = mat_at(ts[k + 1], ts[k + 2])
        a, b = rings[k], rings[k + 1]
        for i in range(SEG):
            j = (i + 1) % SEG
            part.f([a[i], b[i], b[j], a[j]], m, away=centre)
    for i in range(SEG):
        part.f([rings[-1][i], bot, rings[-1][(i + 1) % SEG]], RIM, away=centre)
    return rs, hz


def revolve_loop(part, loop, mat, seg=SEG):
    """Revolve a closed (rho, z) section round the ball's axis: a ring band."""
    rings = [ring(part, r, z, seg) for r, z in loop]
    n = len(loop)
    for k in range(n):
        a, b = rings[k], rings[(k + 1) % n]
        r_mid = (loop[k][0] + loop[(k + 1) % n][0]) / 2
        z_mid = (loop[k][1] + loop[(k + 1) % n][1]) / 2
        for i in range(seg):
            j = (i + 1) % seg
            # outward hint: away from the section's own centre, in the (rho, z) plane at this angle
            ang = 2 * math.pi * (i + 0.5) / seg
            part.f([a[i], b[i], b[j], a[j]], mat,
                   away=(SEC_C[0] * math.cos(ang), YC + SEC_C[0] * math.sin(ang), SEC_C[1]))
    del r_mid, z_mid


SEC_C = (0.0, 0.0)


def collar(part, grow, rs, hz):
    """The containment collar round the equator, its top face the sprite's dark one-pixel ring."""
    global SEC_C
    ro = R_OUT + grow * 1.15   # the big frame's disc fits ~9.77 px (its mask is a touch squarer)
    ri = rs - 0.9          # buried inside the ball
    h = 0.95               # half height
    c = 0.26               # chamfer
    g, gd = 0.13, 0.2      # groove half height, depth
    loop = [(ri, -h), (ro - c, -h), (ro, -h + c), (ro, -g), (ro - gd, -g + 0.05), (ro - gd, g - 0.05), (ro, g),
            (ro, h - c), (ro - c, h), (ri, h)]
    SEC_C = ((ri + ro) / 2, 0.0)
    revolve_loop(part, loop, COLLAR)
    # Eight clamp shoes over the band: chamfered blocks gripping the ball above and below it, a bolt on each.
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        zt = 1.45
        r0 = rs * math.sqrt(max(0.0, 1 - (zt / hz) ** 2)) - 0.12   # meets the ball at its top
        r1 = ro - 0.04
        w = 0.62
        pts = cbox(r0, r1, -w, w, -zt, zt, 0.16, 0.2)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x * ca - y * sa, YC + x * sa + y * ca, z) for x, y, z in pts]
        hull(part, pts, SHOE)
        # bolt head on the shoe's top face
        rb = (r0 + r1) / 2 + 0.05
        bx, by = rb * ca, YC + rb * sa
        bolt = []
        for i in range(10):
            t = 2 * math.pi * i / 10
            for z in (zt - 0.05, zt + 0.16):
                rr = 0.24 if z > zt else 0.27
                bolt.append((bx + rr * math.cos(t), by + rr * math.sin(t), z))
        hull(part, bolt, BOLT)


def build(sprite, coll):
    mats = materials(sprite)
    objs = []
    for grow, frames, suffix in ((0.0, [163, 129], ""), (1.0, [165, 131], "-big")):
        P = Part(f"{NAME}{suffix}", smooth_angle=40.0)
        rs, hz = ball(P, grow)
        collar(P, grow, rs, hz)
        obj = T.finish(P, mats, coll)
        shell = common.outline_shell(obj, coll, voxel=0.012, faces=1000, smooth=6, inside=0.004)
        common.frame_part(obj, frames)
        common.frame_part(shell, frames)
        objs += [obj, shell]
    return objs


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(sprite, coll)
    for o in objs:
        o.data.calc_loop_triangles()
        print(f"{o.name}: {len(o.data.loop_triangles)} triangles")
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
