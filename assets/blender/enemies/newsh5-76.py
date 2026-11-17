"""Red spiked mine (newsh5.shp frame 76): a 3D version of its sprite.

Seen in episode 4 (BRAINIAC, level 22): ground-fixed or weaving mines that launch copies of
themselves sideways, so the same model is also the projectile. The sprite is a red-hot spiked ball:
a long spike up and down, a short one left and right, bright shoulders on the four diagonals, a
white-hot core (127 at column 5, row 5, in a 124/122 halo) on a speckled orange-yellow upper half
(119-124) over a darker red-brown south crust (112-116), and one black pit below the centre. In
game it has to read as a bright orange starburst with a hot core (E4 QA 2026-11-17: the glossy red
ball read dark red), so the casing glows like newshl-116's after D201: heat by palette index, not a
lit red; the ring and the darkest bottom rows stay shading and outline (art rule 2).

What it is, built as such: a welded steel contact mine, red-hot. Two hemispheres of a pressed shell
meet at an equatorial weld seam (a modelled groove); the four spikes are turned cones on bolted
base collars; the four bright shoulders are short Hertz horns (stem plus rounded lead cap) raised
20 degrees on the diagonals; a white-hot core plug crowns the dome; the pit is a detonator port, a
black socket inside a raised collar ring, on the front face below the core (column 5, row 8).
Underside: the plain lower hemisphere with a small flat plug.

Heat (D126/D173 glow: metallic 1, rough, emission rising with heat): a base by the angle from an
axis tipped north of up (hot north 118-120, falling fast past the crown to 116-117, south crust 114-115), seeded
speckle cells about a sprite pixel wide (hot spots to 124, a few dark pockets), the casing round
the core graded 123 -> 122 -> 121. Spike shafts glow orange (their roots in the sprite's base
colours) so they read through the game's ink; the north horn caps run hotter than the south ones.

    blender --background --python assets/blender/enemies/newsh5-76.py

Exports public/models/enemies/newsh5-76.glb and its spriteModels entry (mesh + outline shell,
pal_<index> materials). Set TYRIAN_REVIEW_GLB=<path> to also write a copy there (review only).
"""

import math
import os
import random
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

# Emission by heat (D126): below 1 the face is part lit, part glowing, so the ball keeps its form;
# 120 and up glow at the full palette colour and speckle against the rest.
GLOW = {112: 0.3, 113: 0.4, 114: 0.45, 115: 0.5, 116: 0.58, 117: 0.68, 118: 0.78, 119: 0.88,
        120: 1.0, 121: 1.05, 122: 1.1, 123: 1.15, 124: 1.2}
HEAT_TILT, HEAT_AZ = 50, -20     # heat axis: tipped this far north of up, leaning west (the hot NW)
HEAT = [(30, 120), (50, 119), (65, 118), (76, 117), (88, 116), (102, 115), (130, 114), (181, 113)]
CORE_DY = 0.2 * P                # core plug's top-view offset: the 15 deg game camera (D61) shows the
                                 # dome's crown about 1 px north of the ball, where the sprite has 127
PORT_DY = -2.6 * P               # detonator socket: the sprite's row 8 under the same camera
CORE_HEAT = [(9, 123), (15, 122), (20, 121)]
CELLS = 6                        # speckle plates per cube-face edge, about one sprite pixel each
JITTER = 0.30                    # chance a cell runs a step cooler or hotter
HOT_CELLS = (0.30, 0.04)         # chance a cell is a hot spot (+3..+5): hot side, crust side
COOL_CELLS = 0.12                # chance a cell is a dark pocket (-2)
SPIKE_SHAFT, SPIKE_TIP = 120, 118
# Spike roots take the sprite's colour at their bases (122 N row 1, 116 S row 11, 120 W column 1,
# 116 E column 10) so all four read through the ink; horn caps: hot north shoulders (121, 123), cooler south.
SPIKE_ROOT = {(0, 1): 122, (0, -1): 116, (-1, 0): 120, (1, 0): 118}
HORN_CAP = {0: 123, 1: 121, 2: 116, 3: 117}  # k: NE, NW, SW, SE


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


class Mats:
    """Palette materials by (index, glow): glowing casing metallic 1 / rough (D126/D173)."""

    def __init__(self, sprite):
        self.sprite, self.list, self.slots = sprite, [], {}

    def __call__(self, idx, glow):
        key = (idx, round(glow, 3))
        if key not in self.slots:
            tag = f"{NAME}-{len(self.list)}"
            if glow > 0:
                m = common.palette_material(self.sprite, idx, tag, metallic=1.0, roughness=0.85,
                                            emission_strength=glow)
            else:
                m = common.palette_material(self.sprite, idx, tag, metallic=0.0, roughness=0.85)
            self.slots[key] = len(self.list)
            self.list.append(m)
        return self.slots[key]

    def heat(self, idx):
        return self(idx, GLOW[idx])


HEAT_AXIS = Vector((math.sin(math.radians(HEAT_AZ)) * math.sin(math.radians(HEAT_TILT)),
                    math.cos(math.radians(HEAT_AZ)) * math.sin(math.radians(HEAT_TILT)),
                    math.cos(math.radians(HEAT_TILT))))
CORE_AXIS = Vector((0.0, CORE_DY, math.sqrt(R * R - CORE_DY * CORE_DY))).normalized()


def band(table, ang):
    return next((i for lim, i in table if ang < lim), table[-1][1])


def angle(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


class Speckle:
    """Seeded heat offset per plate of a cube-sphere grid (CELLS x CELLS per cube face, about a
    sprite pixel each): a step cooler or hotter, a hot spot (mostly on the hot north half) or a dark
    pocket, so the ball speckles at the sprite's grain without following the lathe's rings."""

    def __init__(self):
        self.rng, self.cells = random.Random(76), {}

    def __call__(self, d):
        ax = max(range(3), key=lambda i: abs(d[i]))
        u, v = [d[i] / abs(d[ax]) for i in range(3) if i != ax]
        key = (ax, d[ax] > 0, min(CELLS - 1, int((u + 1) / 2 * CELLS)), min(CELLS - 1, int((v + 1) / 2 * CELLS)))
        if key not in self.cells:
            r = self.rng.random()
            shift = -1 if r < JITTER / 2 else (1 if r > 1 - JITTER / 2 else 0)
            t = max(0.0, min(1.0, (d.dot(HEAT_AXIS) + 0.6) / 1.2))
            r = self.rng.random()
            if r < HOT_CELLS[1] + (HOT_CELLS[0] - HOT_CELLS[1]) * t:
                shift += self.rng.choice((3, 4, 4, 5))
            elif r > 1 - COOL_CELLS:
                shift -= 2
            self.cells[key] = shift
        return self.cells[key]


def casing_heat(d, shift):
    idx = max(113, min(124, band(HEAT, angle(d, HEAT_AXIS)) + shift))
    core = band(CORE_HEAT, angle(d, CORE_AXIS)) if angle(d, CORE_AXIS) < CORE_HEAT[-1][0] else 0
    return max(idx, core)


def new_faces(bm, before):
    bm.faces.ensure_lookup_table()
    return [bm.faces[i] for i in range(before, len(bm.faces))]


def build(sprite, coll, proxy=False):
    """The mine; `proxy`: only the ball and the spikes, the sealed copy the outline shell is made
    from, so the port boss, the core plug and the horn bases leave no ink rings in their creases (D51)."""
    mat = Mats(sprite)
    bm = bmesh.new()
    c = Vector((CX, CY, 0.0))

    # body_profile runs top-down as (radius, z); revolve measures d along -Z, so d = -z.
    if proxy:
        prof = [(R * math.sin(a), -R * math.cos(a)) for a in (math.pi * i / 24 for i in range(25))]
        prof[0], prof[-1] = (0.0, prof[0][1]), (0.0, prof[-1][1])
        revolve(bm, prof, (CX, CY, 0.0), (0, 0, -1), 48, 0)
    else:
        revolve(bm, [(r, -z) for r, z in body_profile()], (CX, CY, 0.0), (0, 0, -1), 48, 0)
        speckle = Speckle()
        groove = 0.12 * P
        for f in new_faces(bm, 0):
            q = f.calc_center_median() - c
            d = q.normalized()
            idx = casing_heat(d, speckle(d))
            if abs(q.z) < groove:  # the weld seam: a step cooler, a shadowed line
                idx = max(113, idx - 1)
            f.material_index = mat.heat(idx)
    # Spikes on the equator: up and down 6.6 px from the centre, through rows 1 and 11 into the tip
    # ink of rows 0 and 12 (thin-part border, counted neither way), left and right 5.6 px (columns 1
    # and 9 and the lone red pixel of column 10). Full length, so they survive the game's ink.
    for (dx, dy), base_r, tip in (((0, 1), 1.2 * P, 6.6 * P), ((0, -1), 1.2 * P, 6.6 * P),
                                  ((-1, 0), 1.1 * P, 5.6 * P), ((1, 0), 1.1 * P, 5.6 * P)):
        n0 = len(bm.faces)
        revolve(bm, spike_profile(base_r, tip), c, (dx, dy, 0), 14, 0)
        if proxy:
            continue
        axis = Vector((dx, dy, 0))
        root, shaft = 4.48 * P + 0.3 * (tip - 4.48 * P), 4.48 * P + 0.72 * (tip - 4.48 * P)
        for f in new_faces(bm, n0):
            h = (f.calc_center_median() - c).dot(axis)
            f.material_index = mat.heat(SPIKE_ROOT[(dx, dy)] if h < root else
                                        (SPIKE_SHAFT if h < shaft else SPIKE_TIP))
    if proxy:
        mat.heat(117)
        return common.mesh_object(NAME, bm, mat.list, coll, smooth=True)
    # Hertz horns on the diagonals, raised 20 degrees: the sprite's four bright shoulders.
    el = math.radians(20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        axis = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        n0 = len(bm.faces)
        revolve(bm, horn_profile(), c, axis, 10, 0)
        for f in new_faces(bm, n0):
            h = (f.calc_center_median() - c).dot(axis)
            f.material_index = mat.heat(HORN_CAP[k] if h > 4.46 * P else 118)
    # White-hot core plug on the crown (sprite 127 at column 5, row 5, ringed by 124): a dome in a
    # 124 rim, a touch proud of the casing, no recessed wall (no dark band round it).
    o = c + CORE_AXIS * R
    core = [(-0.25 * P, 0.0), (-0.25 * P, 0.78 * P), (0.03 * P, 0.78 * P), (0.07 * P, 0.66 * P),
            (0.11 * P, 0.52 * P), (0.16 * P, 0.37 * P), (0.20 * P, 0.20 * P), (0.22 * P, 0.0)]
    rim, hot = mat(124, 1.6), mat(127, 3.0)
    revolve(bm, [(r, d) for d, r in core], o, CORE_AXIS, 20, [rim] * 4 + [hot] * 3)
    # Detonator port at column 5, row 8 under the game camera (PORT_DY), on the front face: a raised
    # boss (0.3 px proud, a cooler collar) with the black socket's floor above the shell, so it shows.
    n = Vector((0.0, PORT_DY, math.sqrt(R * R - PORT_DY * PORT_DY))).normalized()
    port = [(0.0, 3.95 * P), (0.80 * P, 3.95 * P), (0.80 * P, 4.52 * P), (0.73 * P, 4.60 * P),
            (0.62 * P, 4.60 * P), (0.56 * P, 4.55 * P), (0.54 * P, 4.40 * P), (0.0, 4.40 * P)]
    boss, pit = mat.heat(115), mat(1, 0.0)
    revolve(bm, port, c, n, 16, [boss] * 6 + [pit])
    obj = common.mesh_object(NAME, bm, mat.list, coll, smooth=True)
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
