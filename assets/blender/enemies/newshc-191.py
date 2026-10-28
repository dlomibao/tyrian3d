"""Grey gun-tower craft (newshc.shp frames 191, 193, 195): a 3D version of its sprite.

Seen in episode 3 (levels 3.6 and 3.23). Seen from above: a grey tower at the back with two dark
vent slots, a pair of round grey pods with dark glass canopies either side of it, a blue hull
underneath with green, sloped side panels, and a pink cannon whose dark mouth opens just in front
of the tower. The three frames only light up the strips on the green panels (dark green, then
brighter green, then bright yellow-green on the last frame), so one model covers them all: the
strips change palette colour on each frame (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshc-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "newshc-191"
ROOT = common.repo_root(__file__)
AXIS = 12.0  # the sprite is mirror symmetric about the edge between columns 11 and 12


def plane_solid(bm, outline, z0, zfun, mat, xy=(lib.W, lib.H)):
    """A solid over an outline of (col, row) pixel edges, flat underneath at z0 (px) and topped by
    a plane: zfun(col, row) gives the top's height in px and must be linear, so the top is flat."""
    w, h = xy
    pts = [(c, r) for c, r in outline]
    xyp = [(lib.X(c, w), lib.Y(r, h)) for c, r in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xyp, xyp[1:] + xyp[:1]))
    if area < 0:
        pts.reverse()
        xyp.reverse()
    bottom = [bm.verts.new((x, y, lib.P(z0))) for x, y in xyp]
    top = [bm.verts.new((x, y, lib.P(zfun(c, r)))) for (x, y), (c, r) in zip(xyp, pts)]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def sprite_pos(co):
    """A Blender point back to (col, row, z) in sprite pixels."""
    return co.x * 12 + lib.W / 2, lib.H / 2 - co.y * 12, co.z * 12


def new_faces(bm, before):
    return [f for f in bm.faces if f not in before]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # One mid-tone per part: the sprite's outline ring, its lit/shaded halves and its highlights are
    # the game's lighting and outline, so they are not painted on (rubric: "The sprite's lighting
    # is not paint"); the shine comes from the metallic/glossy materials.
    mats = [
        pal(7, metallic=0.75, roughness=0.3),  # 0 grey tower: polished metal hood
        pal(2, metallic=0.1, roughness=0.9),  # 1 dark vent slots
        pal(105, metallic=0.7, roughness=0.3),  # 2 grey-blue pods: polished metal balls
        pal(100, metallic=0.05, roughness=0.1),  # 3 navy glass canopies
        pal(57, metallic=0.4, roughness=0.4),  # 4 blue hull: painted metal
        pal(59, metallic=0.4, roughness=0.4),  # 5 light blue stripes on the hull's crests
        pal(38, metallic=0.05, roughness=0.75),  # 6 green side panels: matte paint
        # 7 glowing strip: the panel's dark green on 191, green on 193, bright green on 195
        common.palette_material(sprite, 38, f"{NAME}-glow", emission_strength=3.0, frames={193: 43, 195: 202}),
        pal(89, metallic=0.6, roughness=0.3),  # 8 pink pod: polished metal
        pal(82, metallic=0.1, roughness=0.9),  # 9 dark opening in the pink pod
        pal(103, metallic=0.4, roughness=0.4),  # 10 grey deck under the pods
        pal(56, metallic=0.4, roughness=0.5),  # 11 recessed gap between the pods and the hull
    ]
    TOWER, SLOT, POD, GLASS, HULL, RIB, GREEN, GLOW, PINK, MOUTH, DECK, GAP = range(12)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    # Blue hull (rows 14-25, the 1 px dark rim included), stepped in at its lower corners, with
    # the notch between the two halves of its front edge (row 25, columns 11-12).
    # Its chamfered rim keeps the hull colour: the sprite's dark 1 px edge is its outline.
    lib.slab(bm, [(0.0, 14.2), (AXIS, 14.2), (AXIS, 25.0), (11.0, 25.0), (11.0, 26.0), (4.0, 26.0),
                  (4.0, 25.75), (2.8, 25.0), (1.2, 24.0), (0.0, 22.8)], -3.2, 0.2, mat=HULL, bevel=0.9)
    # Green side panel: a band down the outer edge (column 1 at row 18 to columns 4-6 at row 24),
    # tilted down towards the outside, and its glow strip just proud of it.
    green_z = lambda c, r: 0.5 + 0.12 * (c - 1.0)  # noqa: E731
    plane_solid(bm, [(1.0, 18.9), (2.4, 18.9), (3.0, 19.4), (4.0, 20.9), (5.0, 21.2), (5.4, 22.4),
                     (6.4, 23.4), (7.2, 24.6), (7.0, 25.0), (4.0, 25.0), (3.9, 24.0), (2.0, 24.0), (1.2, 23.0)],
                -2.6, green_z, GREEN)
    plane_solid(bm, [(2.0, 20.8), (3.0, 21.0), (3.0, 22.8), (4.0, 23.0), (4.0, 24.0), (3.0, 24.0), (2.0, 22.9)],
                -1.0, lambda c, r: green_z(c, r) + 0.2, GLOW)
    # The hull's light diagonal (columns 4-8, rows 20-24) is the lit face of an angular crest
    # running from just under the pod down to the front edge: a ridge with a light blue stripe on
    # its outer face (drawn on both sides, so a marking) and hull blue sloping down to the pink pod.
    r0c, r0r, r1c, r1r = 5.8, 19.4, 8.9, 25.0
    dl = math.hypot(r1c - r0c, r1r - r0r)
    nc, nr = -(r1r - r0r) / dl, (r1c - r0c) / dl  # across the ridge, towards the outside

    def across(c, r):
        return (c - r0c) * nc + (r - r0r) * nr

    plane_solid(bm, [(4.0, 19.6), (r0c, r0r), (r1c, r1r), (7.0, 25.0), (5.0, 21.2)],
                -1.0, lambda c, r: 1.6 - 0.35 * across(c, r), RIB)
    plane_solid(bm, [(r0c, r0r), (7.0, 18.9), (9.6, 18.9), (9.6, 25.0), (r1c, r1r)],
                -1.0, lambda c, r: 1.6 + 0.3 * across(c, r), HULL)
    # The sprite's dark navy line under the pods (row 18, and down beside the pink pod to row 21):
    # a gap between the pods and the hull's crests, its floor just above the hull.
    lib.slab(bm, [(0.6, 17.0), (3.9, 17.0), (3.9, 17.7), (AXIS, 17.7), (AXIS, 18.9), (0.6, 18.9)], -1.0, 0.5, mat=GAP)
    # Grey deck the pods sit on (rows 13-18), behind the hull.
    lib.slab(bm, [(1.6, 13.0), (AXIS, 13.0), (AXIS, 18.0), (1.6, 18.0)], -1.8, 0.4, mat=DECK, bevel=0.5)
    # Round pod (columns 1-8, rows 9-17): a ball standing about 5.5 px above the hull, a navy glass
    # canopy capping its back half. The sprite's pale lower half is the shine on a metal ball, so
    # the rest is one grey. The canopy is a cap cut by a plane on the unit sphere (y is backwards),
    # so its edge is a clean curve; the band cut stays only to keep the mesh as it was.
    before = set(bm.faces)
    pc, pr, pz, prx, pry, prz = 4.5, 13.5, 2.2, 3.95, 4.4, 3.95
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)

    def unit_cap(normal):
        n = Vector(normal).normalized()
        return n

    glass_n, glass_d = unit_cap((0.0, math.sin(math.radians(35)), math.cos(math.radians(35)))), 0.78
    band_n, band_d = unit_cap((0.3, -math.sin(math.radians(55)), math.cos(math.radians(55)))), 0.67
    for n, d in ((glass_n, glass_d), (band_n, band_d)):
        pod = new_faces(bm, before)
        geom = list({v for f in pod for v in f.verts}) + list({e for f in pod for e in f.edges}) + pod
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n)
    pod = new_faces(bm, before)
    for f in pod:
        m = f.calc_center_median()
        f.smooth = True
        f.material_index = GLASS if m.dot(glass_n) > glass_d else POD
    for v in {v for f in pod for v in f.verts}:
        k = 1.0 if v.co.z >= 0 else 0.6
        v.co.x, v.co.y, v.co.z = lib.X(pc) + v.co.x * lib.P(prx), lib.Y(pr) + v.co.y * lib.P(pry), \
            lib.P(pz + v.co.z * prz * k)
    lib.mirror_x(bm, AXIS)

    # ---- centre ----
    # Grey tower (columns 7-16, rows 3-13): a hood of half-round section, crown about 4.8 px
    # above the deck, rounded down at its back, flat underneath.
    before = set(bm.faces)
    lib.loft_y(bm, AXIS, [(3.0, 2.9, 2.6, 0.0), (3.6, 3.7, 3.6, 0.0), (4.4, 4.3, 4.3, 0.0),
                          (5.0, 4.9, 4.9, 0.0), (5.6, 5.1, 5.1, 0.0), (7.0, 5.1, 5.1, 0.0),
                          (11.6, 5.1, 5.1, 0.0), (13.8, 5.1, 5.1, 0.0)],
               sides=16, mat=TOWER, smooth=True)
    tower = new_faces(bm, before)
    for v in {v for f in tower for v in f.verts}:
        v.co.z = max(v.co.z, lib.P(-1.5))
    slots = []
    for f in tower:
        c, r, z = sprite_pos(f.calc_center_median())
        # the sprite's bright crown line and dark lower sides are the hood's sheen and shading
        if 7.0 < r < 11.6 and 1.0 < abs(c - AXIS) < 2.9 and z > 3.5:
            slots.append(f)  # the two dark vent slots (columns 9-10 and 13-14, rows 7-11)
    res = bmesh.ops.inset_individual(bm, faces=slots, thickness=lib.P(0.1), depth=-lib.P(1.7))
    for f in slots + res["faces"]:
        f.material_index = SLOT
        f.smooth = False
    # Pink pod (columns 9-14, rows 13-22): a round body 6 px across lying on the hull, its dark
    # opening cut into its top just in front of the tower; its pale and dark sides are lighting.
    before = set(bm.faces)
    lib.loft_y(bm, AXIS, [(12.9, 2.2, 2.2, 2.6), (13.4, 3.0, 3.0, 2.6), (14.0, 3.0, 3.0, 2.6),
                          (17.4, 3.0, 3.0, 2.6), (18.0, 3.0, 3.0, 2.6), (22.0, 3.0, 3.0, 2.6),
                          (22.6, 2.3, 2.5, 2.5), (23.3, 1.1, 1.3, 2.4)],
               sides=12, mat=PINK, smooth=True)
    mouth = []
    for f in new_faces(bm, before):
        c, r, z = sprite_pos(f.calc_center_median())
        if 14.0 < r < 17.4 and abs(c - AXIS) < 2.2 and z > 4.6:
            mouth.append(f)
    res = bmesh.ops.inset_region(bm, faces=mouth, thickness=lib.P(0.15), depth=-lib.P(1.6))
    for f in mouth + res["faces"]:
        f.material_index = MOUTH
        f.smooth = False

    obj = lib.to_object(NAME, bm, mats, coll)
    obj.location.z = -0.4 / 12
    return obj


def main():
    lib.run_single(ROOT, NAME, build)


if __name__ == "__main__":
    main()
