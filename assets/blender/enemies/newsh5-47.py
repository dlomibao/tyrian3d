"""Purple belted pod (newsh5.shp frame 47), design A: a 3D version of its sprite.

Seen in episode 4 (HARVEST 4.1 and LAVA RUN 4.12): it drifts up the screen and launches copies of
itself (e4:72, the same picture), so the model is also its own projectile.

What the sprite shows, read as an object: a pressure pod, a body of revolution round its flight
axis (sprite up, +Y), as round across as it is tall (plan a near-ellipse 22.8 x 24.6 px). Two
pressed hemishells meet at flanges under a maroon V-band clamp (sprite rows 11-16, the dark rows 10
and 17 are the grooves either side, shading); a gold T-bolt latch closes the band on top (columns
11-12) with a pale nut at its front (row 11) and its gold trunnion across the band's rear edge (row
16, the bright 251 with the 246 either side). Behind the band on top a launch port opens (rows
18-22, columns 6-16): a raised coaming round a well whose walls catch the light at its sides and
whose floor is dark, where the copies come out. The near-white spot on the front dome, the darker
lower half and the outline ring are sheen, shading and ink (art rule 2): one mid purple (85, the trimmed median of the shell pixels).
Front and rear poles carry small bolted cap plates (front/rear views); the underside is the plain
shell continued (closed, no detail).

    blender --background --python assets/blender/enemies/newsh5-47.py

Exports public/models/enemies/newsh5-47.glb and its spriteModels entry (mesh + outline shell, pal_<index> materials).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]  # the repo: assets/blender/enemies/<this file>
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies")]
import common  # noqa: E402

NAME = "newsh5-47"
MODEL = f"enemies/{NAME}"
P = 1 / 12  # one sprite pixel
Y0 = 0.5 * P  # body centre (inner mask rows 1-25 centre on edge 13.5)
A, B, N = 11.3 * P, 12.3 * P, 2.1  # plan superellipse: half width, half length, exponent
BAND = 3.0 * P  # V-band half width (rows 11-16 span Y -3..+3 px)
FL = 3.9 * P  # flange outer face from the band centre
R_BAND = 11.35 * P
SIDES = 40


def shell_r(y):
    """Radius of the hull section at Y (Blender units)."""
    u = min(1.0, abs(y - Y0) / B)
    return A * max(0.0, 1 - u ** N) ** (1 / N)


def revolve(bm, profile, origin, axis, sides, mats, phase=0.5, closed=False):
    """A solid of revolution round `axis` through `origin`. `profile` is [(radius, d)] along the axis
    (radius 0 = a pole vertex); `mats` is one material slot or one per profile segment. `closed`
    joins the last profile point back to the first (a ring with a closed section, no caps)."""
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
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for i, (r0, r1) in enumerate(pairs):
        mi = mats if isinstance(mats, int) else mats[min(i, len(mats) - 1)]
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
    if not closed:
        m0 = mats if isinstance(mats, int) else mats[0]
        m1 = mats if isinstance(mats, int) else mats[-1]
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0]))).material_index = m0
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1]).material_index = m1


def hull_profile(plain=False):
    """(radius, y) of the hull from the front pole to the rear pole: front dome with a bolted cap
    plate seam near the pole, the front flange, a waist under the band, the rear flange, the rear
    dome with its cap plate seam. `plain`: the sealed outline proxy (no seams, no waist)."""
    yt, yb = Y0 + B, Y0 - B
    pts = [(0.0, yt)]
    if plain:
        n = 40
        for i in range(1, n):
            y = yt - (yt - yb) * (i / n) ** 1.0
            pts.append((shell_r(y), y))
        pts.append((0.0, yb))
        return pts

    def dome(y_from, y_to, n):
        return [(shell_r(y), y) for y in (y_from + (y_to - y_from) * i / n for i in range(n + 1))]

    def seam(y, sign):
        # A cap plate's edge: a 0.12 px chamfered groove 0.3 px wide on the dome.
        r = shell_r(y)
        g = 0.12 * P
        return [(r, y + sign * 0.18 * P), (r - g, y + sign * 0.06 * P), (r - g, y - sign * 0.06 * P),
                (shell_r(y - sign * 0.18 * P), y - sign * 0.18 * P)]

    # Front dome: pole cap first (finer near the pole so it stays round).
    cap = Y0 + B - 1.1 * P  # cap plate seam ~4.6 px radius
    for t in (0.04, 0.12, 0.25, 0.42, 0.62, 0.82):
        y = yt - (yt - (cap + 0.18 * P)) * t
        pts.append((shell_r(y), y))
    pts += seam(cap, 1)
    pts += dome(cap - 0.3 * P, BAND + FL - 0.6 * P + 0.6 * P, 10)[1:]
    # Front flange: a 0.25 px proud lip with chamfers, then the waist under the band.
    yf = FL
    rf = shell_r(yf) + 0.15 * P
    pts += [(rf, yf), (rf + 0.1 * P, yf - 0.12 * P), (rf + 0.1 * P, BAND + 0.25 * P),
            (rf - 0.05 * P, BAND + 0.1 * P), (10.4 * P, BAND + 0.1 * P), (10.4 * P, -BAND - 0.1 * P)]
    yr = -FL
    rr = max(shell_r(yr) + 0.15 * P, 10.85 * P)
    pts += [(rr - 0.05 * P, -BAND - 0.1 * P), (rr + 0.1 * P, -BAND - 0.25 * P), (rr + 0.1 * P, yr + 0.12 * P),
            (rr, yr)]
    # Rear dome down to its cap plate seam and the pole.
    rcap = Y0 - B + 1.1 * P
    pts += dome(yr - 0.05 * P, rcap + 0.3 * P, 10)[1:]
    pts += seam(rcap, -1)
    for t in (0.82, 0.62, 0.42, 0.25, 0.12, 0.04):
        y = yb + ((rcap - 0.18 * P) - yb) * t
        pts.append((shell_r(y), y))
    pts.append((0.0, yb))
    return pts


def band_profile():
    """Closed (radius, y) section of the V-band clamp: chamfered edges, a slight crown."""
    ro, ri, h = R_BAND, 10.3 * P, BAND
    return [(ri, -h + 0.05 * P), (ro - 0.35 * P, -h), (ro - 0.08 * P, -h + 0.25 * P), (ro, -h + 0.9 * P),
            (ro + 0.04 * P, 0.0), (ro, h - 0.9 * P), (ro - 0.08 * P, h - 0.25 * P), (ro - 0.35 * P, h),
            (ri, h - 0.05 * P)]


def chamfer_box(bm, x0, x1, y0, y1, z0, z1, ch, mat):
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(x + sx * ch, y, z + sz * ch), (x, y + sy * ch, z + sz * ch), (x + sx * ch, y + sy * ch, z)]
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts)
    bmesh.ops.delete(bm, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)], context="VERTS")
    for f in {f for v in verts if v.is_valid for f in v.link_faces}:
        f.material_index = mat


# Launch port outline on top behind the band: a rounded "D", flat-ish along the band.
# Sized to the sprite's dark opening (rows 18-22, cols 6-16): the lip's outer edge stays within
# ~75 % of the local hull radius so it never reaches the limb.
PCX, PCY = -0.5 * P, -6.15 * P
PRX, PRY_UP, PRY_DN = 5.7 * P, 1.9 * P, 2.6 * P
PSIDES = 40


def port_xy(k, scale):
    ang = 2 * math.pi * (k + 0.5) / PSIDES
    c, s = math.cos(ang), math.sin(ang)
    e = 2 / 3.2  # superellipse exponent 3.2: flatter along the band than an ellipse
    x = PRX * scale * math.copysign(abs(c) ** e, c)
    ry = PRY_UP if s > 0 else PRY_DN
    y = ry * scale * math.copysign(abs(s) ** e, s)
    return PCX + x, PCY + y


def surf_z(x, y):
    r = shell_r(y)
    return math.sqrt(max(0.0, r * r - x * x))


def surf_point(x, y, d):
    """The hull point above (x, y), offset by d along the hull's outward normal there."""
    z = surf_z(x, y)
    h = 0.01 * P
    rp = (shell_r(y + h) - shell_r(y - h)) / (2 * h)
    n = Vector((x, -shell_r(y) * rp, z)).normalized()
    return Vector((x, y, z)) + n * d


def build(sprite, coll, proxy=False):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(85, metallic=0.4, roughness=0.46),  # 0 purple painted steel hull (the sprite median; sheen from the lights)
        pal(243, metallic=0.5, roughness=0.42),  # 1 maroon V-band
        pal(250, metallic=0.85, roughness=0.32),  # 2 satin gold latch and trunnion
        pal(94, metallic=0.85, roughness=0.3),  # 3 pale nut
        pal(81, metallic=0.0, roughness=0.85),  # 4 dark port floor
    ]
    SHELL, BAND_M, GOLD, PALE, DARK = range(5)
    bm = bmesh.new()
    origin = (0.0, 0.0, 0.0)
    revolve(bm, [(r, y) for r, y in hull_profile(plain=proxy)], origin, (0, 1, 0), SIDES, SHELL)
    if proxy:
        revolve(bm, band_profile(), origin, (0, 1, 0), SIDES, BAND_M, closed=True)
        return common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # The hull alone takes the port cut (one closed manifold for the exact boolean); the band follows.
    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # Launch port: cut the well (walls taper in to 80 %, 3.2 px deep, floor following the hull).
    depth = 3.0 * P
    cb = bmesh.new()
    rings = []
    for scale, dz in ((1.0, "top"), (1.0, None), (1.0, -0.25 * P), (0.94, -depth), (0.5, -depth)):
        ring = []
        for k in range(PSIDES):
            x, y = port_xy(k, scale)
            if dz == "top":
                ring.append(cb.verts.new((x, y, 2.0)))
            elif dz is None:  # above the hull along its normal, so the cut wall meets the lip square
                ring.append(cb.verts.new(surf_point(x, y, 1.0 * P)))
            elif dz > -depth:  # the rim follows the hull normal
                ring.append(cb.verts.new(surf_point(x, y, dz)))
            else:
                ring.append(cb.verts.new((x, y, surf_z(x, y) + dz)))
        rings.append(ring)
    mats_ring = [SHELL, SHELL, SHELL, DARK]
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(PSIDES):
            j = (k + 1) % PSIDES
            cb.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mats_ring[i]
    cx, cy = PCX, PCY - 0.4 * P
    centre = cb.verts.new((cx, cy, surf_z(cx, cy) - depth))
    for k in range(PSIDES):
        j = (k + 1) % PSIDES
        cb.faces.new((rings[-1][k], rings[-1][j], centre)).material_index = DARK
    cb.faces.new(list(reversed(rings[0]))).material_index = SHELL
    cutter = common.mesh_object(NAME + "-cutter", cb, mats, coll)
    mod = body.modifiers.new("port", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

    bm = bmesh.new()
    bm.from_mesh(body.data)
    revolve(bm, band_profile(), origin, (0, 1, 0), SIDES, BAND_M, closed=True)
    # Coaming: a chamfered lip round the port, 0.35 px proud along the hull normal, ~0.6 px wide;
    # a sealed ring (its buried underside closes the section).
    sec = [(0.99, -0.3 * P), (0.99, 0.25 * P), (1.025, 0.35 * P), (1.08, 0.3 * P), (1.12, -0.05 * P),
           (1.12, -0.3 * P)]
    lip = []
    for k in range(PSIDES):
        ring = []
        for s, dz in sec:
            x, y = port_xy(k, s)
            ring.append(bm.verts.new(surf_point(x, y, dz)))
        lip.append(ring)
    for k in range(PSIDES):
        j = (k + 1) % PSIDES
        for i in range(len(sec)):
            i1 = (i + 1) % len(sec)
            bm.faces.new((lip[k][i], lip[j][i], lip[j][i1], lip[k][i1])).material_index = SHELL
    # Launch rail mouth in the well floor: a dark ring boss with a hole, guide rails either side.
    fz = surf_z(PCX, PCY - 0.4 * P) - depth
    for side in (-1, 1):
        xr = PCX + side * 2.3 * P
        chamfer_box(bm, xr - 0.35 * P, xr + 0.35 * P, PCY - 1.7 * P, PCY + 1.2 * P,
                    fz - 0.2 * P, surf_z(xr, PCY) - depth + 0.45 * P, 0.1 * P, DARK)

    # T-bolt latch on the top of the band: gold bar (columns 11-12, rows 12-16), pale nut at its
    # front (row 11), gold trunnion across the band's rear edge (row 16, columns 10-13).
    zt = R_BAND + 0.02 * P
    chamfer_box(bm, -0.9 * P, 0.9 * P, -2.4 * P, 2.0 * P, zt - 0.5 * P, zt + 0.55 * P, 0.22 * P, GOLD)
    chamfer_box(bm, -0.95 * P, 0.95 * P, 1.9 * P, 2.95 * P, zt - 0.5 * P, zt + 0.75 * P, 0.25 * P, PALE)
    # Trunnion: a short gold cylinder along X at the band's rear edge.
    st = len(bm.verts)
    revolve(bm, [(0.0, -2.0 * P), (0.45 * P, -2.0 * P), (0.55 * P, -1.85 * P), (0.55 * P, 1.85 * P),
                 (0.45 * P, 2.0 * P), (0.0, 2.0 * P)], (0.0, -2.55 * P, zt + 0.05 * P), (1, 0, 0), 12, GOLD)
    # Hinge lugs either side of the trunnion (band colour).
    for side in (-1, 1):
        chamfer_box(bm, side * 2.05 * P - 0.25 * P, side * 2.05 * P + 0.25 * P, -3.0 * P, -2.0 * P,
                    zt - 0.4 * P, zt + 0.4 * P, 0.1 * P, BAND_M)

    # Hard edges: split normals where faces meet at more than 38 degrees.
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(38):
            e.smooth = False
    bm.to_mesh(body.data)
    bm.free()
    for poly in body.data.polygons:
        poly.use_smooth = True
    return body


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    proxy = build(sprite, coll, proxy=True)
    shell = common.outline_shell(proxy, coll, voxel=0.01, faces=2500, smooth=2, inside=0.003, islands="outer")
    bpy.data.objects.remove(proxy, do_unlink=True)
    obj = build(sprite, coll)
    assert obj.name == NAME and shell.name == f"{NAME}_outline", (obj.name, shell.name)
    assert len(shell.data.polygons) > 0
    for o in (obj, shell):
        o["design_model"] = NAME
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"tris {tris} shell faces {len(shell.data.polygons)}")
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    if "--review" in ARGV:  # review output only behind a flag
        common.export_glb([obj, shell], Path(ARGV[ARGV.index("--review") + 1]))


if __name__ == "__main__":
    main()
