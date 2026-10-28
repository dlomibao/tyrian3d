"""Twin red pods (newshf.shp frame 169): a 3D version of its sprite.

Seen in episodes 1-4. Two identical red missiles flying side by side, twelve pixels apart: each
a round tube about 6 px across with a forked top (two short prongs round a dark socket), a head
swollen to 10 px wide by rounded side pods, a purple band round its middle and a flared skirt
with three pink nozzle knobs above the blunt tip.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newshf-169.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402
from lib_b023 import common, ey  # noqa: E402

NAME = "newshf-169"
P = 1 / 12  # one sprite pixel


# Tags for the parts while building; each is then given its part's mid-tone palette index. The
# sprite's light and dark columns (bright left flank, dark right flank, black outline ring) are its
# drawn lighting, which the game's lights and outline make, so they are not painted on; only the
# purple band, the groove and the dark socket between the prongs are real markings.
TUBE, KNOB, FINE, SADDLE = range(4)
HULL = 71      # the red hull's mid-tone (the sprite's body pixels average index 69.6, lit to ~71)
NOZZLE = 74    # the pink nozzle knobs
BAND = 87      # the purple band, rows 17-18 (84-90)
GROOVE = 67    # the groove's floor, column 5, rows 15-20
SOCKET = 66    # the dark socket between the prongs, rows 5-6
# Painted metal hull: some sheen, not a mirror.
FINISH = {HULL: (0.4, 0.4), NOZZLE: (0.5, 0.35), BAND: (0.4, 0.4), GROOVE: (0.4, 0.5), SOCKET: (0.3, 0.6)}

# The tube's ring vertices sit on the sprite's column edges, so each face seen from above lies under
# one pixel column: X offsets in px across the top, equator to equator, with the groove's two walls
# just outside column 5 (-1..0), then one vertex underneath. A ring narrower than 3.2 px scales them.
TUBE_X = (99, 3.0, 2.0, 1.0, 0.15, 0.0, -1.0, -1.15, -2.0, -3.0, -99)
GROOVE_K = (TUBE_X.index(0.0), TUBE_X.index(-1.0))
POD_ANGLES = (0, 35, 65, 90, 115, 145, 180, 270)


def round_loft(bm, x0, sections, angles, mat, cap_start=True, cap_end=True):
    """Loft elliptical rings (y, half width, half height) along Y at X = x0, with ring vertices at
    the given angles (or, with angles=None, at the TUBE_X column edges); a section with zero size is
    a point."""
    rings = []
    for y, w, h in sections:
        if w == 0 and h == 0:
            rings.append([(x0, y, 0.0)])
            continue
        if angles is None:
            ref = max(w, 3.2 * P)
            ring_angles = [math.degrees(math.acos(max(-1.0, min(1.0, x * P / ref)))) for x in TUBE_X] + [270]
        else:
            ring_angles = angles
        rings.append([(x0 + w * math.cos(math.radians(a)), y, h * math.sin(math.radians(a))) for a in ring_angles])
    return lib.ring_loft(bm, rings, mat, cap_start=cap_start, cap_end=cap_end)


def resample(profile, keep):
    """The profile (row, half width, half height) sampled at every row edge it spans, plus its first
    section and the rows in `keep`, so faces split exactly where the sprite's rows do."""
    rows = sorted({profile[0][0]} | {float(r) for r in range(math.ceil(profile[0][0]), int(profile[-1][0]) + 1)}
                  | set(keep))
    out = []
    for r in rows:
        if r < profile[0][0] or r > profile[-1][0]:
            continue
        exact = [s for s in profile if abs(s[0] - r) < 1e-6]
        if exact:
            out.append(exact[0])
            continue
        a, b = next((a, b) for a, b in zip(profile, profile[1:]) if a[0] < r < b[0])
        t = (r - a[0]) / (b[0] - a[0])
        out.append((r, a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])))
    return out


def pod(bm, x0):
    """One pod centred on X = x0 (the left pod covers columns 1-10, centred on column edge 6).

    A round tube about 6 px across (columns 3-8) from the forked top (row 6) to the blunt tip
    (row 27): a socket between the two prongs, a head swollen to about 8 px thick across rows
    8-15 with a rounded side pod on each flank (columns 1-2 and 9-10, so the head is 10 px wide),
    the raised purple band (rows 17-18), a 1 px groove down the lower body (column 5, rows 15-21)
    and a skirt flaring to 8 px (rows 23-24) carrying three round nozzle knobs, then the tip
    narrowing to 4 px."""
    socket = [
        (7.3, 0.9, 0.9),      # socket floor between the prongs (rows 5-6 dark)
        (6.0, 1.1, 1.1),      # socket lip
        (6.0, 2.5, 2.5),      # top face
    ]
    profile = [
        (6.6, 2.95, 2.95),
        (8.6, 3.1, 3.7),      # the head swells
        (9.6, 3.2, 4.1),
        (14.4, 3.2, 4.1),
        (15.4, 3.1, 3.6),
        (16.4, 3.0, 3.0),
        (16.85, 3.0, 3.0),
        (17.0, 3.25, 3.25),   # raised purple band, rows 17-18
        (19.0, 3.25, 3.25),
        (19.15, 3.0, 3.0),
        (22.2, 3.0, 3.0),     # skirt flares out
        (22.9, 3.7, 3.5),
        (23.4, 4.0, 3.7),
        (24.6, 4.0, 3.7),
        (25.1, 3.4, 3.2),
        (26.0, 2.6, 2.5),     # tip, 4 px wide at row 26
        (26.6, 1.8, 1.7),
        (26.95, 0.9, 0.8),
        (27.0, 0.0, 0.0),
    ]
    secs = socket + resample(profile, (14.85, 16.85, 19.15, 22.15, 26.6, 26.95))
    rings = round_loft(bm, x0, [(ey(r), w * P, h * P) for r, w, h in secs], None, TUBE, cap_end=False)
    # Notch the top end between the prongs (columns 5-6, rows 5-7), so it reads dark from above.
    for k, r in ((1, 7.2), (2, 7.2), (3, 7.7)):
        for v in rings[k]:
            if v.co.z > 0 and abs(v.co.x - x0) < 1.6 * P:
                v.co.y = ey(r)
    # The groove: sink column 5's two top vertices 0.8 px from row 15 to row 22, between steep walls.
    for (r, *_), ring in zip(secs, rings):
        if 15 - 1e-6 <= r <= 22 + 1e-6 and len(ring) > 1:
            for k in GROOVE_K:
                ring[k].co.z -= 0.8 * P
    # Side pods on the head's flanks (columns 1-2 and 9-10, rows 8-15), sunk into the tube: round
    # capsules about as tall as they are wide, narrowing to a rounded nose at the top (rows 8-10)
    # and closing round at the back.
    pod_secs = [(7.95, 0.0, 0.0), (8.25, 0.6, 0.9), (9.0, 1.0, 1.6), (10.0, 1.4, 2.3), (11.0, 1.6, 2.6),
                (12.0, 1.6, 2.6), (13.0, 1.6, 2.6), (14.0, 1.6, 2.6), (15.0, 1.3, 2.1), (15.6, 0.8, 1.2),
                (16.05, 0.0, 0.0)]
    for side in (-1, 1):
        round_loft(bm, x0 + side * 3.4 * P, [(ey(r), w * P, h * P) for r, w, h in pod_secs], POD_ANGLES, TUBE)
    # Three round nozzle knobs half sunk into the top of the skirt (columns 3, 5-6 and 8, rows 23-24):
    # 2-2.5 px across, the middle one rising to about 4.5 px.
    for dc, r, ry in ((-2.5, 0.9, 1.05), (0.0, 1.3, 1.15), (2.5, 0.9, 1.05)):
        zs = 3.7 * (1 - (dc / 3.75) ** 2) ** 0.5  # the skirt's top under the knob
        top = zs + (0.85 if dc == 0 else 0.75)
        lib.dome(bm, x0 + dc * P, ey(24.0), (zs - 0.7) * P, r * P, ry * P, (top - zs + 0.7) * P,
                 mat_index=KNOB, segs=8, rings=3)
    # The forked top: two square prongs, 2 px thick tapering to 1 px (columns 3-4 and 7-8, rows 4-7),
    # rising from the tube's rim, joined by a low dark saddle across the socket (columns 5-6, row 6).
    for dc in (-1, 1):
        lib.polyline_tube(bm, [(x0 + dc * 1.95 * P, ey(7.6), 1.6 * P), (x0 + dc * 1.95 * P, ey(5.6), 2.2 * P),
                               (x0 + dc * 1.5 * P, ey(4.05), 2.4 * P)],
                          [1.4 * P, 1.35 * P, 0.7 * P], sides=4, mat_index=FINE, flat=1.0)
    lib.polyline_tube(bm, [(x0 - 1.5 * P, ey(6.6), 1.4 * P), (x0 + 1.5 * P, ey(6.6), 1.4 * P)],
                      0.7 * P, sides=4, mat_index=SADDLE, flat=1.2)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lib.palette(sprite, NAME)
    bm = bmesh.new()
    for x0 in (-0.5, 0.5):  # pod centres: column edges 6 and 18
        pod(bm, x0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        x0 = -0.5 if c.x < 0 else 0.5
        dx, r = (c.x - x0) / P, 14 - c.y / P  # px from the pod's centre line, sprite row
        top = f.normal.z > 0.35
        if f.material_index == KNOB:
            idx = NOZZLE
        elif f.material_index == SADDLE or (f.material_index == TUBE and r < 7.6 and abs(dx) < 1.2
                                             and f.normal.z > 0.2):
            idx = SOCKET
        elif f.material_index == TUBE and 16.8 <= r <= 19.2 and abs(dx) < 3.6:
            idx = GROOVE if top and -1.0 < dx < 0.0 else BAND
        elif f.material_index == TUBE and top and 15 <= r <= 21 and -1.0 < dx < 0.0:
            idx = GROOVE
        else:
            idx = HULL
        f.material_index = idx
    used = sorted({f.material_index for f in bm.faces})
    slot = {i: k for k, i in enumerate(used)}
    for f in bm.faces:
        f.material_index = slot[f.material_index]
    mats = [pal(i, metallic=FINISH[i][0], roughness=FINISH[i][1]) for i in used]
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
