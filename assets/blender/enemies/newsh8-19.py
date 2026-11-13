"""newsh8-19 (and its lib_b035 partner newsh8-267), design A: hard-surface builds of both sprites.

(1) newsh8-19, the spinning twin pod (newsh8.shp, ten 12x14 frames, a small weaving flyer of 3.4
IXMUCANE and 3.9 SAWBLADES). What it is: a small tan drone made of two engine pods joined by a
lens-section wing plate, flying south (down the screen) and rolling about its flight axis as it
weaves. The sprite's red caps on the north ends are the pods' hot exhaust bells (orange-yellow
cores on the frames that look into them), the bright bands at rows 2 and 8 are two raised collars
round each pod (their sheen; the row 9 dark band is the groove under the second collar), and the
pods' south ends carry a fork of two tines round a recessed emitter face. The tines sit on a
gimballed collar that keeps them level as the hull rolls on the rolled frames 38/151 and 57/132
(where the sprite draws them side by side, 1 px either side of the pod's axis); elsewhere they are
clocked across the pod as before. The plate between the pods has a raised spine (the sprite's
bright column 5 is its sheen), a dark recessed slot bed (rows 8-10), a thin tail keel on the roll
axis (edge on face on, the sprite's dark tail plate at rows 9-10 as the craft rolls), and two tail
prongs that converge toward the keel (rows 10-12.7). Fix round 1 reshaped the keel, prongs and
tines row by row so every frame's top view passes (iou_rule_grid >= 0.958). The ten frames are the craft rolled: 19 face on, 114 edge on, the other
eight four rolled pairs (38/151, 57/132, 76/152, 95/133) where the first of a pair has its left
pod raised toward the camera (the plate covers the inner edge of the lower, right pod) and the
second its right pod. Pods are round (3 px wide edge on, the sprite's 3 px), 7.3 px apart; the
roll angles are fitted to the sprite's widths (10, 10, 8, 6, 4, 3 px). Like the original script,
six models (newsh8-19, -f2..-f6); a pair's model holds both rolls as frame parts (D17), each with
its own outline shell from the sealed mesh (D51/D90/D118).

(2) newsh8-267, the tan claw craft (newsh8.shp 267/269/271, 24x28): two thick tan arms rise from
beside a red T-shaped emitter, arch over the shoulders and curl down and forward into claw legs
either side of a grey housing; the housing's front holds a hot slot that closes over the three
frames (5, 3 and 1 px wide). Three models (newsh8-267, -f2, -f3); 267 is drawn one px right of
the others, so its axis is too (as the original script).

Hard surface: lathed and lofted sections (pchip stations), chamfered collars and ends, modelled
grooves, no bake, no foil. pal_<index> materials, glow surfaces metallic 1 / rough (D126/D173).

Run: blender --background --python assets/blender/enemies/newsh8-19.py [-- --only 19|267|all]
Run directly it exports only newsh8-19 (--only 19); newsh8-267.py loads this file and runs main("267"),
so a full tools/build-models.sh run writes each glb once.
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

PX = 1 / 12


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# --- helpers (copied, not shared) ---------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation (copy of usp_talon.pchip)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


class Mesh:
    """A bmesh in sprite px (x across, v = row-edge coordinate, south is +v, z up)."""

    def __init__(self):
        self.bm = bmesh.new()

    def loft(self, rings, mats, cap0=True, cap1=True, flat=False):
        """Rings: lists of (x, v, z) of equal length (a 1-point ring is a pole). mats[i] is the
        material of the band from ring i to i+1 (an int applies to all)."""
        bm = self.bm
        vs = [[bm.verts.new(p) for p in r] for r in rings]
        mats = mats if isinstance(mats, list) else [mats] * (len(rings) - 1)
        faces = []
        for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
            n = max(len(r0), len(r1))
            for k in range(n):
                j = (k + 1) % n
                if len(r0) == 1:
                    q = (r0[0], r1[k], r1[j])
                elif len(r1) == 1:
                    q = (r0[k], r1[0], r0[j])
                else:
                    q = (r0[k], r1[k], r1[j], r0[j])
                f = bm.faces.new(q)
                f.material_index = mats[i]
                f.smooth = not flat
                faces.append(f)
        if cap0 and len(vs[0]) > 2:
            f = bm.faces.new(list(reversed(vs[0])))
            f.material_index = mats[0]
            faces.append(f)
        if cap1 and len(vs[-1]) > 2:
            f = bm.faces.new(vs[-1])
            f.material_index = mats[-1]
            faces.append(f)
        return faces

    def lathe(self, profile, cx, cz, sides=16, rx=1.0, rz=1.0, phase=0.0):
        """A solid of revolution about the v axis through (cx, cz): profile = [(v, r, mat)], the
        band to point i+1 takes point i+1's mat; r = 0 is a pole."""
        rings = []
        for v, r, _ in profile:
            if r <= 1e-6:
                rings.append([(cx, v, cz)])
            else:
                rings.append([(cx + r * rx * math.cos(phase + 2 * math.pi * k / sides), v,
                               cz + r * rz * math.sin(phase + 2 * math.pi * k / sides)) for k in range(sides)])
        return self.loft(rings, [m for _, _, m in profile[1:]], cap0=False, cap1=False)

    def to_object(self, name, mats, coll, smooth_angle=34.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        return obj


def superellipse(cx, v, cz, hw, hh, n=2.6, pts=20, zfn=None):
    """A closed section in the x-z plane at v: |dx/hw|^n + |dz/hh|^n = 1 (n > 2: flatter, a
    machined slab with rounded edges). zfn(dx) adds a camber."""
    out = []
    for k in range(pts):
        a = 2 * math.pi * k / pts
        c, s = math.cos(a), math.sin(a)
        dx = hw * math.copysign(abs(c) ** (2 / n), c)
        dz = hh * math.copysign(abs(s) ** (2 / n), s)
        out.append((cx + dx, v, cz + dz + (zfn(dx) if zfn else 0.0)))
    return out


def transform_mesh(obj, fn):
    for vtx in obj.data.vertices:
        vtx.co = fn(Vector(vtx.co))
    obj.data.update()


def spec_level(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def shell_for(obj, coll, frames=None):
    """D51 outline shell from the sealed mesh (this model is closed and has no culled copy):
    D90/D118 voxel, held a hair inside. Every part overlaps its neighbour, so the remesh is one
    island; checked after."""
    bpy.context.view_layer.update()
    sh = common.outline_shell(obj, coll, voxel=0.010, faces=2500, smooth=4, inside=0.003)
    if frames:
        common.frame_part(sh, frames)
    return sh


# =================================================================================================
# (1) newsh8-19
# =================================================================================================

N19 = "newsh8-19"
W19, H19 = 12, 14
A_POD = 3.75   # pod axis, px from the roll axis
R_POD = 1.3    # barrel radius (3 px edge on with the game's ink)
BLADE = 0.85   # half depth of the tail blades past row 11
R_BELL = 1.2   # hot exhaust bell radius
R_END = 1.12   # nozzle bell and forebody radius (the sprite's pods narrow at rows 1-2 and 10-11)
PRONG_IN = (1.15, 0.98, 0.95)  # the tail prongs' axis off the roll axis, converging (rows 11-12.7)
KEEL = [(7.9, 0.2, 0.6), (8.6, 0.2, 1.7), (10.55, 0.2, 1.7), (10.9, 0.15, 1.0), (11.05, 0.1, 0.3)]
FORK_LEVEL = {38, 151, 57, 132}  # frames whose tines are clocked level (the sprite draws them side by side)
# model -> [(frame, roll degrees, x shift px)]: + raises the left pod toward the camera.
MODELS19 = [
    (N19, [(19, 0.0, 0.0)]),
    (f"{N19}-f2", [(38, 20.0, 0.0), (151, -20.0, 0.0)]),
    (f"{N19}-f3", [(57, 44.0, 0.0), (132, -44.0, 0.0)]),
    (f"{N19}-f4", [(76, 63.0, 0.0), (152, -63.0, 0.0)]),
    (f"{N19}-f5", [(95, 79.0, 0.0), (133, -79.0, 0.0)]),
    (f"{N19}-f6", [(114, 90.0, 0.5)]),
]


def mats19(sprite, tag):
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    m = [
        pal(25, metallic=0.4, roughness=0.58),  # 0 pod barrel (satin tan, the pods' median)
        pal(27, metallic=0.45, roughness=0.5),   # 1 collars (the sprite's bright bands are their sheen)
        pal(22, metallic=0.45, roughness=0.6),   # 2 grooves, emitter face, nozzle throat
        pal(24, metallic=0.4, roughness=0.58),   # 3 wing plate
        pal(119, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 4 hot exhaust bell
        pal(123, metallic=1.0, roughness=0.9, emission_strength=1.0),   # 5 white-hot core
        pal(20, metallic=0.4, roughness=0.7),    # 6 dark slot bed
        pal(25, metallic=0.4, roughness=0.55),   # 7 forebody, prongs, spine
    ]
    for x in m[:4] + m[6:]:
        spec_level(x, 0.4)  # satin tan, not bronze (fix round 1)
    return m


POD, COL, GRV, PLATE, GLOW, CORE, SLOT, FORE = range(8)


def pod_profile():
    R = R_POD
    return [
        (1.3, 0.0, CORE), (1.3, 0.62, CORE),              # white-hot core deep in the bell
        (1.1, 0.8, GRV),                                  # throat
        (0.82, 0.92, GLOW), (0.76, 1.0, GLOW),            # bell lip (inner)
        (0.8, 1.12, GLOW), (0.95, R_BELL, GLOW),          # lip chamfer
        (1.95, R_BELL, GLOW),                             # hot bell
        (2.0, R_END - 0.04, GRV), (2.08, R_END - 0.04, GRV), (2.12, R_END + 0.02, COL),  # seam
        (2.75, R, COL), (2.85, R, POD),                   # conical shoulder (the sprite's row 2 band)
        (5.0, R, POD), (5.06, R - 0.07, GRV), (5.18, R - 0.07, GRV), (5.24, R, POD),  # panel seam
        (7.95, R, POD),
        (8.2, R + 0.12, COL), (8.8, R + 0.12, COL),      # collar (row 8 band)
        (9.0, R_END - 0.04, GRV), (9.4, R_END - 0.04, GRV), (9.55, R_END + 0.05, FORE),  # groove (row 9)
        (11.8, R_END, FORE), (12.0, R_END - 0.3, FORE),  # chamfered nose
        (12.02, 0.6, GRV), (12.15, 0.5, GRV), (12.25, 0.0, GRV),  # emitter boss between the prongs
    ]


def build19_mesh(roll=0.0, fork_level=False):
    """The craft unrolled (face on), in px: x across, v rows, z up; roll axis x = z = 0. `roll`
    (degrees, as place19) clocks the gimballed fork tines so they stay level."""
    M = Mesh()
    for s in (-1, 1):
        cx = s * A_POD
        M.lathe(pod_profile(), cx, 0.0, sides=18)
        # A fork of two prongs on each pod's nose, above and below it (the sprite's forked pod
        # ends: one prong face on, two at the pod's edges as the craft rolls).
        for k in range(2):
            phi = (math.radians(roll) if fork_level else math.pi / 2) + k * math.pi
            rc = 0.86
            thick = 1.4 if fork_level else 1.0  # level tines: a little deeper (their width from above)
            rings = []
            st = [(11.4, 0.45, 0.3, 0.0), (11.95, 0.44, 0.29, 0.1), (12.6, 0.42, 0.27, 0.15),
                  (12.9, 0.36, 0.22, 0.15), (13.05, 0.2, 0.12, 0.12), (13.1, 0.0, 0.0, 0.1)]
            for v, hw, hh, dr in st:
                if hw == 0:
                    r = rc + dr
                    rings.append([(cx + r * math.cos(phi), v, r * math.sin(phi))])
                    continue
                ring = []
                for q in range(8):
                    a = 2 * math.pi * q / 8
                    t = hw * math.cos(a)        # tangential
                    r = rc + dr + thick * hh * math.sin(a)  # radial
                    ring.append((cx + r * math.cos(phi) - t * math.sin(phi), v,
                                 r * math.sin(phi) + t * math.cos(phi)))
                rings.append(ring)
            M.loft(rings, FORE)
    # Wing plate: a lens-section slab from pod axis to pod axis, rows 2.2-8.2; its north corners
    # round off inside the pods (the sprite's ink notch at row 2, column 3).
    plate_st = [(2.15, 1.7, 0.28), (2.3, 2.05, 0.48), (2.55, 2.5, 0.6), (2.9, 3.2, 0.62), (3.3, A_POD, 0.62),
                (7.9, A_POD, 0.62), (8.1, A_POD, 0.55), (8.25, A_POD - 0.3, 0.35)]
    rings = [superellipse(0.0, v, 0.0, hw, hh, n=2.2, pts=24) for v, hw, hh in plate_st]
    M.loft(rings, PLATE)
    # Raised spine along the plate's centre, both faces (it rolls): chamfered bar.
    for zs in (1, -1):
        sp = [(2.45, 0.0, 0.0), (2.7, 0.45, 0.16), (7.6, 0.45, 0.16), (7.95, 0.0, 0.0)]
        rings = []
        for v, hw, hh in sp:
            if hw == 0:
                rings.append([(0.0, v, zs * 0.55)])
            else:
                rings.append([(-hw, v, zs * 0.5), (-hw * 0.6, v, zs * (0.6 + hh)), (hw * 0.6, v, zs * (0.6 + hh)),
                              (hw, v, zs * 0.5), (0.0, v, zs * 0.4)])
        M.loft(rings, FORE, flat=True)
    # Two short prongs off the plate's south edge (cheeks out to the pods, then the prong), with
    # a dark recessed slot bed between them (rows 8-9).
    for sg in (-1, 1):
        # The prongs are deep blades (taller than wide, thin past row 11): edge on to the camera when the craft is
        # face on, they fill the slot between them when it rolls, as the sprite draws it.
        st = [(7.8, 2.4, 1.3, 0.55), (9.3, 2.4, 1.3, 0.55), (9.75, 1.6, 0.55, 0.9), (10.8, 1.5, 0.5, 0.88),
              (11.1, PRONG_IN[0], 0.24, BLADE), (12.0, PRONG_IN[1], 0.2, BLADE - 0.1), (12.45, PRONG_IN[2], 0.15, 0.45),
              (12.6, PRONG_IN[2], 0.08, 0.2), (12.7, PRONG_IN[2], 0.0, 0.0)]
        rings = [[(sg * cx, v, 0.0)] if hw == 0 else superellipse(sg * cx, v, 0.0, hw, hh, n=2.4, pts=14)
                 for v, cx, hw, hh in st]
        M.loft(rings, FORE)
    rings = [superellipse(0.0, v, 0.0, 1.15, hh, n=3.0, pts=16) for v, hh in ((8.0, 0.3), (9.95, 0.26))]
    M.loft(rings, SLOT)
    # Tail keel: a thin dorsal/ventral fin on the roll axis between the prongs (the sprite's dark
    # tail plate at rows 9-10). Edge on to the camera face on; it shows as the craft rolls.
    rings = [superellipse(0.0, v, 0.0, hw, hh, n=2.6, pts=16) for v, hw, hh in KEEL]
    M.loft(rings, GRV)
    return M


def place19(obj, roll_deg, shift):
    a = math.radians(roll_deg)
    ca, sa = math.cos(a), math.sin(a)

    def fn(p):
        x, v, z = p
        xr = x * ca + z * sa
        zr = -x * sa + z * ca
        return Vector(((xr + shift) * PX, (H19 / 2 - v) * PX, zr * PX))
    transform_mesh(obj, fn)


def build19(sprite):
    out = []  # (model, [objects])
    for name, frames in MODELS19:
        coll = common.reset_collection(name)
        mats = mats19(sprite, "nsh8_19")
        objs = []
        for f, roll, shift in frames:
            oname = name if len(frames) == 1 else f"{name}-{f}"
            obj = build19_mesh(roll, f in FORK_LEVEL).to_object(oname, mats, coll)
            place19(obj, roll, shift)
            obj.data.set_sharp_from_angle(angle=math.radians(34))
            tag = [f] if len(frames) > 1 else None
            if tag:
                common.frame_part(obj, tag)
            sh = shell_for(obj, coll, tag)
            objs += [obj, sh]
        out.append((name, objs, [f for f, _, _ in frames]))
    return out


# =================================================================================================
# (2) newsh8-267
# =================================================================================================

N267 = "newsh8-267"
W267, H267 = 24, 28
# frame -> (axis column edge coordinate, slot width px)
FRAMES267 = [(267, 12.5, 5.0), (269, 11.5, 3.0), (271, 11.5, 1.0)]


def mats267(sprite, tag):
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    m = [
        pal(23, metallic=0.4, roughness=0.55),  # 0 tan arm (the sprite's arm median, 22.5; mean 23.1)
        pal(19, metallic=0.45, roughness=0.6),   # 1 armour seams
        pal(7, metallic=0.5, roughness=0.4),     # 2 grey housing
        pal(11, metallic=0.75, roughness=0.3),   # 3 light grey lid
        pal(113, metallic=0.5, roughness=0.6),   # 4 dark red slot frame
        pal(124, metallic=1.0, roughness=0.9, emission_strength=1.0),  # 5 hot slot (top)
        pal(119, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 6 red emitter
        pal(124, metallic=1.0, roughness=0.9, emission_strength=1.0),  # 7 emitter bulb
        pal(9, metallic=0.7, roughness=0.35),    # 8 grey prongs
        pal(4, metallic=0.5, roughness=0.5),     # 9 dark grey pylon
        pal(27, metallic=0.6, roughness=0.35),   # 10 (spare: light tan)
        pal(117, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 11 red foot of the slot
    ]
    for x in m[:5] + m[8:]:
        spec_level(x, 0.45)
    return m


ARM, ADARK, HOUSE, LID, RIM, HOT, RED, BULB, PRONG, HDARK, CREST, HOT2 = range(12)


def arm_path():
    """The left arm's centreline as stations: (v, x from axis, z, half width, half height)."""
    # Sprite: root rows 9-10 at cols 8-10 (x -4.5..-1.5), shoulder rows 11-16 out to col 1,
    # leg rows 17-23 at cols 4-6 (x -8..-5.5 for 267's axis 12.5... measured from the axis).
    # Measured from the sprite's inner mask, row by row: outer edge x = -4.5 (row 9), -5.5, -6.5,
    # -8.5, -9.5, -10.5 (rows 14-17), -9.5 (18), -8.5 (19-22), -7.5 (23); inner edge against the
    # emitter and housing down to row 17, then -5.5 down the leg.
    return [
        (7.85, -2.5, 1.7, 0.0, 0.0),
        (8.2, -2.55, 1.75, 0.8, 0.55),
        (9.5, -3.0, 1.95, 1.55, 1.0),
        (10.5, -3.55, 2.05, 2.0, 1.2),
        (11.5, -4.3, 2.05, 2.3, 1.35),
        (12.5, -5.75, 1.95, 2.8, 1.5),
        (13.5, -6.55, 1.8, 3.0, 1.55),
        (14.6, -7.0, 1.55, 3.45, 1.6),
        (16.4, -7.05, 1.05, 3.45, 1.5),
        (17.5, -7.45, 0.6, 2.95, 1.35),
        (18.5, -7.45, 0.25, 2.0, 1.2),
        (19.5, -7.0, -0.05, 1.55, 1.1),
        (21.5, -7.0, -0.45, 1.52, 1.05),
        (22.6, -6.95, -0.75, 1.35, 0.95),
        (23.4, -6.7, -0.95, 0.95, 0.7),
        (23.85, -6.6, -1.05, 0.45, 0.3),
        (24.0, -6.6, -1.07, 0.0, 0.0),
    ]


def build267_mesh(slot):
    """Built about the axis x = 0 (px), v = row edge coordinate, z up."""
    M = Mesh()
    st = arm_path()
    vs = [s[0] for s in st]
    fx = pchip(vs, [s[1] for s in st])
    fz = pchip(vs, [s[2] for s in st])
    fw = pchip(vs, [s[3] for s in st])
    fh = pchip(vs, [s[4] for s in st])
    # Stations along the arm, dense round the armour seams (shoulder, knee, ankle).
    seams = (12.7, 17.7, 21.6)
    samples = [vs[0], vs[0] + 0.15] + [vs[0] + 0.15 + i * (vs[-1] - 0.3 - vs[0]) / 34 for i in range(1, 35)]
    for sv in seams:
        samples += [sv - 0.16, sv - 0.08, sv + 0.08, sv + 0.16]
    samples = sorted(set(round(x, 4) for x in samples if vs[0] <= x <= vs[-1] - 0.15)) + [vs[-1]]
    # Armour section: a chamfered octagon, flat top and flanks (u across, w up, unit half sizes).
    SEC = [(1.0, -0.35), (1.0, 0.3), (0.72, 0.82), (0.28, 1.0), (-0.28, 1.0), (-0.72, 0.82), (-1.0, 0.3),
           (-1.0, -0.35), (-0.7, -0.88), (0.7, -0.88)]

    def groove(v):
        return min(abs(v - sv) for sv in seams) < 0.1

    for side in (-1, 1):
        rings, mats = [], []
        for i, v in enumerate(samples):
            w, h = fw(v), fh(v)
            cx, cz = (fx(v) if side < 0 else -fx(v)), fz(v)
            if w < 0.02 or i == 0 or i == len(samples) - 1:
                rings.append([(cx, v, cz)])
            else:
                g = 0.9 if groove(v) else 1.0
                rings.append([(cx + u * w * g, v, cz + q * h * g) for u, q in SEC])
            mats.append(ADARK if i > 0 and groove(v) and groove(samples[i - 1]) else ARM)
        M.loft(rings, mats[1:], flat=True)
        # Two armour ribs along the arm's crown with a channel between them (the sprite's bright
        # lines down each arm are their sheen, the dark columns between them the channel).
        rv = [v for v in samples if 9.8 <= v <= 22.6]
        for off, lo, hi in ((0.45, 9.8, 22.6), (-0.32, 10.6, 17.2)):
            rr = [v for v in rv if lo <= v <= hi]
            rings = []
            for j, v in enumerate(rr):
                w, h = fw(v), fh(v)
                cx = (fx(v) if side < 0 else -fx(v)) + side * w * off
                t = min(1.0, j / 3, (len(rr) - 1 - j) / 3)
                hw, hz = 0.36 * max(t, 0.1), 0.2 * max(t, 0.1)
                z0 = fz(v) + h * (0.95 - 0.2 * abs(off) ** 2)
                rings.append([(cx - hw, v, z0), (cx - hw * 0.55, v, z0 + hz + 0.07), (cx + hw * 0.55, v, z0 + hz + 0.07),
                              (cx + hw, v, z0), (cx, v, z0 - 0.15)])
            M.loft(rings, ARM, flat=True)
        # Grey prong under the housing's front (row 19, 2 px off the axis).
        px = -2.0 * (1 if side < 0 else -1)
        st2 = [(16.4, 0.55, 0.45), (19.2, 0.5, 0.42), (19.75, 0.3, 0.25), (19.95, 0.0, 0.0)]
        rings = [[(px, v, -0.5)] if hw == 0 else superellipse(px, v, -0.5, hw, hh, n=2.4, pts=10) for v, hw, hh in st2]
        M.loft(rings, PRONG)
    # Grey housing between the arms (rows 12-17, 7 px wide): a chamfered block, sloped flanks.
    hs = [(11.3, 2.3, 0.9), (11.6, 3.2, 1.25), (12.2, 3.5, 1.45), (17.4, 3.5, 1.45), (17.75, 3.2, 1.2), (17.9, 2.6, 0.8)]
    rings = [superellipse(0.0, v, 0.0, hw, hh, n=3.2, pts=24) for v, hw, hh in hs]
    M.loft(rings, HOUSE)
    # Light lid across the top (row 14) with chamfered edges.
    lid = [(13.85, 2.3, 0.0), (14.0, 2.6, 0.22), (14.8, 2.6, 0.22), (14.95, 2.3, 0.0)]
    rings = [[(-w, v, 1.38), (-w, v, 1.45 + h), (w, v, 1.45 + h), (w, v, 1.38)] for v, w, h in lid]
    M.loft(rings, LID, flat=True)
    # Front slot (rows 15-17) in a dark red frame: the glow is hot yellow at its top (row 16) and
    # red at its foot (row 17); its width set by the frame.
    sw = slot / 2
    fr = [(14.9, sw + 0.5, 0.0), (15.05, sw + 0.62, 0.17), (17.8, sw + 0.62, 0.17), (17.95, sw + 0.5, 0.0)]
    rings = [[(-w, v, 1.3), (-w, v, 1.45 + h), (w, v, 1.45 + h), (w, v, 1.3)] for v, w, h in fr]
    M.loft(rings, RIM, flat=True)
    for v0, v1, mat in ((15.9, 16.95, HOT), (16.95, 17.65, HOT2)):
        rings = [[(-sw, v, 1.5), (-sw, v, 1.67), (sw, v, 1.67), (sw, v, 1.5)] for v in (v0, v1)]
        M.loft(rings, mat, flat=True)
    # Red T emitter on the housing's back: crossbar (row 7), bulb (row 8), stem (rows 9-13).
    bar = [(-2.7, 0.0, 0.0), (-2.5, 0.75, 0.55), (2.5, 0.75, 0.55), (2.7, 0.0, 0.0)]
    rings = []
    for x, hw, hh in bar:
        if hw == 0:
            rings.append([(x, 7.5, 2.4)])
        else:
            rings.append([(x, 7.5 + hw * math.cos(a), 2.4 + hh * math.sin(a)) for a in [2 * math.pi * k / 12 for k in range(12)]])
    M.loft(rings, RED)
    M.lathe([(7.95, 0.0, BULB), (7.95, 0.55, BULB), (8.3, 0.85, BULB), (8.9, 0.85, BULB), (9.2, 0.5, BULB), (9.3, 0.0, BULB)],
            0.0, 2.45, sides=14, rx=1.0, rz=0.75)
    stem = [(8.8, 0.62, 0.5), (12.6, 0.62, 0.5), (13.3, 0.55, 0.42), (13.6, 0.0, 0.0)]
    rings = [[(0.0, v, 2.0)] if hw == 0 else superellipse(0.0, v, 2.0, hw, hh, n=2.4, pts=12) for v, hw, hh in stem]
    M.loft(rings, RED)
    # Stem pylon down into the housing (dark).
    py = [(9.0, 0.95, 0.9), (13.0, 0.95, 0.9)]
    rings = [superellipse(0.0, v, 1.2, hw, hh, n=3.0, pts=12) for v, hw, hh in py]
    M.loft(rings, HDARK)
    return M


def place267(obj, axis):
    def fn(p):
        x, v, z = p
        return Vector(((axis - W267 / 2 + x) * PX, (H267 / 2 - v) * PX, z * PX))
    transform_mesh(obj, fn)


def build267(sprite):
    out = []
    for i, (frame, axis, slot) in enumerate(FRAMES267):
        name = N267 if i == 0 else f"{N267}-f{i + 1}"
        coll = common.reset_collection(name)
        obj = build267_mesh(slot).to_object(name, mats267(sprite, "nsh8_267"), coll)
        place267(obj, axis)
        obj.data.set_sharp_from_angle(angle=math.radians(24))
        sh = shell_for(obj, coll)
        out.append((name, [obj, sh], [frame]))
    return out


def export_models(models, sprite):
    base = sprite["sprites"][0]
    for name, objs, frames in models:
        for o in objs:
            if o.type == "MESH" and o.get("tyrian_outline"):
                assert len(o.data.polygons) > 0, f"{o.name}: empty outline shell"
        common.export_sprite_model(WT, objs, f"enemies/{name}", [{**base, "frames": frames}])


def main(only=None):
    only = only or arg("--only", "19")
    if only == "all":
        only = None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    if only in (None, "19"):
        s19 = common.load_sprite(WT, N19)
        export_models(build19(s19), s19)
    if only in (None, "267"):
        s267 = common.load_sprite(WT, N267)
        export_models(build267(s267), s267)


if __name__ == "__main__":
    main()
