"""newshj-77, the green-eyed ground pod of the TORM jungle (newshj.shp size 2, frames 77 / 79 / 81,
damage frame 41; 24 x 28 px block), design A for the e2-enemies-3 rebuild (D65, D120, D130, D173).

WHAT IT IS: a fixed armoured eye turret standing on the ground (terrain-fixed on the ground layer
in 2.1 and 2.12; the inventory's "air" flag does not make it fly, D120/D166). A squat oval puck:
a dark toe and a lit flange at the ground, a dark undercut, a battered armour wall, a light
bevelled rim, a narrow flat deck and a big green glass lens sunk in a dark socket. It fires its
turret (110) through the lens, which brightens over the animation (77 -> 79 -> 81, ani 11:
77 79 81 81 81 79 79 79 79 79 77). No pixel floor plate (D130): the jungle-floor greens 32-35 at
the sprite's edge are not built.

Reading the sprite (frame-77 rows/cols, px):
- Footprint rows 16-25, cols 4-19 (the inner mask, its ink ring left to the game's outline, D74):
  one smooth superellipse fitted to the inner masks of all three frames.
- The drawing is oblique: the deck (rows 16-22, palette 8) with the lens, then the front of the
  puck down the south rows: rim 22 (8-11, lit), wall 23 (7), a dark undercut 24 (3), the flange 25
  (5) and a dark toe 26. Built in plan as a deck set north in the footprint, the armour band wide
  to the south (3.5 px) and on the flanks (3 px), thin on the north (0.6 px): the tilted game
  camera sees that south band as the sprite's front.
- The 11-13 crescent on the north-west rim is the bevel's sheen (rim palette 11), not a bump.
- Lens: an 8 x 5 px ellipse (cols 8-15, rows 17-21) centred (12.0, 19.5); its hot core sits NW
  of centre (11.6, 19.0). Palette per frame (trimmed medians): core 201 / 206 / 207, mid
  195 / 198 / 204, rim 193 / 195 / 199 for 77 / 79 / 81. It glows (D126), metallic 1, rough (D173).
- The three frames are the same pod one and two px further south (79, 81); frame 77 also shows a
  dark band at row 26 under the toe: a dark mount collar in the ground, fixed, that the pod
  covers on 79 and 81. One mesh per frame (frame_part, D17), each with its own lens colours.
- Damage frame 41 (tyrian.hdt dGr 41, drawn when the pod is destroyed): the same pod at frame 77's
  place, burnt black (palette 1-2) but for the north-west rim and wall and patches of the front
  wall (grey 5-12), the lens shattered: a black pit with green glass shards in two clusters (192-201) and dark chips (34).
  Modelled (D173) so the wreck does not draw as an intact pod; it needs frame 41 added to the
  model's sprites entry when finished.

Outline shell per frame from a sealed pre-cull copy (D51/D90/D118), frame-tagged with its mesh.
No textures/newshj-77 folder, so no maps. Exports public/models/enemies/newshj-77.glb and the sprites
entry (frames 77 / 79 / 81 and the wreck frame 41).

    blender --background --factory-startup --python assets/blender/enemies/newshj-77.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshj-77"
MODEL = f"enemies/{NAME}"
PX = 1 / 12
NT = 96  # samples round


def bl(x, y, z):
    """Sprite px (column edge, row edge, height) to Blender units (24 x 28 block, centred)."""
    return Vector(((x - 12) * PX, (14 - y) * PX, z * PX))


# --- outlines (frame-77 px, image y down) ---------------------------------------------------------

O = (12.0, 19.5)  # ray centre for every ring: the lens centre
# Foot: superellipse fitted to the inner masks of 77/79/81 (fit2.py; grid IoU 0.958/0.980/0.979):
# cx, cy, rx west, rx east, ry north, ry south, n north, n south
FOOT = (12.386, 20.781, 8.801, 7.675, 4.794, 5.062, 3.639, 2.824)
# Deck: the flat top round the lens, set north in the footprint (the sprite's top face).
DECK = (12.15, 19.45, 5.25, 5.05, 3.15, 2.85, 2.6, 2.6)
# Socket (= the lens edge): cols 8-15, rows 17-21.
LENS = (12.0, 19.5, 4.05, 4.05, 2.58, 2.58, 2.0, 2.0)
CORE = (11.6, 19.0)  # the lens's hot core
# Mount collar in the ground (the dark row 26 of frame 77), fixed; hidden under the pod on 79/81.
COLLAR = (12.044, 23.767, 7.551, 7.551, 3.619, 3.619, 2.5, 2.5)
# The wreck (frame 41) has its own fit: the burnt pod's outline sits a little west and its toe
# slumps a little further south (fit2.py 41; grid IoU 0.963).
FOOT_WRECK = (11.271, 21.161, 7.038, 8.562, 4.969, 6.264, 3.446, 3.224)
COLLAR_WRECK = (11.516, 22.658, 7.222, 7.222, 3.076, 3.076, 2.5, 2.5)


def se_in(p, x, y):
    cx, cy, rxw, rxe, ryn, rys, nn, ns = p
    dx, dy = x - cx, y - cy
    rx = rxw if dx < 0 else rxe
    ry, n = (ryn, nn) if dy < 0 else (rys, ns)
    return abs(dx / rx) ** n + abs(dy / ry) ** n < 1


def ray(p, a, src=O, hi=20.0):
    """Distance from src to the outline p along image angle a (0 east, pi/2 south)."""
    ca, sa = math.cos(a), math.sin(a)
    lo = 0.0
    for _ in range(40):
        m = (lo + hi) / 2
        if se_in(p, src[0] + ca * m, src[1] + sa * m):
            lo = m
        else:
            hi = m
    return lo


ANG = [2 * math.pi * (k + 0.5) / NT for k in range(NT)]
RF = [ray(FOOT, a) for a in ANG]
RD = [ray(DECK, a) for a in ANG]
RL = [ray(LENS, a) for a in ANG]


def at(k, r, z):
    a = ANG[k]
    return (O[0] + r * math.cos(a), O[1] + r * math.sin(a), z)


# --- mesh helpers ---------------------------------------------------------------------------------

def grid_faces(bm, vr, mats):
    """Quads between consecutive closed rings vr[i] (each NT verts); mats[i] is the band above ring
    i: a material index or a function k -> index."""
    for i in range(len(vr) - 1):
        for k in range(NT):
            m = (k + 1) % NT
            f = bm.faces.new((vr[i][k], vr[i][m], vr[i + 1][m], vr[i + 1][k]))
            mi = mats[i]
            f.material_index = mi(k) if callable(mi) else mi


def cap(bm, ring, centre, mat, up=True):
    c = bm.verts.new(centre)
    for k in range(NT):
        m = (k + 1) % NT
        f = bm.faces.new((ring[k], ring[m], c) if up else (ring[m], ring[k], c))
        f.material_index = mat(k) if callable(mat) else mat


def loft(bm, rings, mat, caps=True):
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rings]
    n = len(vr[0])
    for r0, r1 in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    if caps:
        for r, flip in ((vr[0], True), (vr[-1], False)):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / n)
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((r[j], r[i], c) if flip else (r[i], r[j], c)).material_index = mat


def stud(bm, mat, cx, cy, z0, r, h, seg=8):
    rings = [[(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg), z0 - 0.15) for k in range(seg)]]
    for th in (0.0, 0.6, 1.1):
        rings.append([(cx + r * math.cos(th) * math.cos(2 * math.pi * k / seg),
                       cy + r * math.cos(th) * math.sin(2 * math.pi * k / seg), z0 + h * math.sin(th) / math.sin(1.1)) for k in range(seg)])
    loft(bm, rings, mat)


# --- the pod --------------------------------------------------------------------------------------

Z_DECK = 3.98
SEAMS = [k for k in range(NT) if any(abs(((ANG[k] - math.radians(d) + math.pi) % (2 * math.pi)) - math.pi) < math.pi / NT
                                       for d in (20, 55, 90, 125, 160, 200, 340))]


def band_profile(w, a):
    """(inset from the foot px, z px, band) rings up the armour, for a band w px wide at image angle
    a: toe, flange, undercut, battered wall, lit rim, deck edge. The fixed insets scale down where
    the band is thin (north), the wall takes the rest. The bevelled rim is broader on the west and
    north, where the sprite shows its lit crescent (cols 5-9, rows 16-20)."""
    s = max(0.2, min(1.0, w / 3.5))
    west = max(0.0, -math.cos(a))
    north = max(0.0, -math.sin(a))
    south = max(0.0, math.sin(a))
    nw = max(0.0, math.cos(a - math.radians(225)))  # toward the lit north-west
    if w < 1.6:
        rimw = w * (0.3 + 0.35 * nw)
    else:
        rimw = 1.0 * s * (0.7 + 0.3 * south) + 0.75 * west * s
    sl = s * (0.35 + 0.65 * south)  # toe/flange/undercut: full on the south (rows 24-25), narrow on the flanks
    r0 = max(1.75 * sl, w - rimw)  # wall top / rim start
    Z = 1.12
    return [
        (0.0, 0.0, "toe"), (0.0, 0.25 * Z, "toe"),
        (0.1 * sl, 0.4 * Z, "flange"), (0.7 * sl, 0.52 * Z, "flange"), (0.82 * sl, 0.6 * Z, "flange"),
        (0.9 * sl, 0.85 * Z, "under"), (1.5 * sl, 1.05 * Z, "under"),
        (1.62 * sl, 1.22 * Z, "wall"), ((1.62 * sl + r0) / 2, 2.05 * Z, "wall"),
        (r0, 2.9 * Z, "wall"),
        (r0 + (w - r0) * 0.55, 3.3 * Z, "rim"), (r0 + (w - r0) * 0.88, 3.5 * Z, "rim"), (w, Z_DECK, "deck"),
    ]


def build_pod(bm, I, lens_mats, wreck=False, char=None):
    """The closed pod: armour rings from the foot to the deck edge, the deck, the socket and the
    lens (or, wrecked, a black pit with shards). I: material name -> index. char(x, y) -> True
    where the wreck is burnt, "scorch" on the front wall's scorched unburnt patches, else False."""
    profs = [band_profile(RF[k] - RD[k], ANG[k]) for k in range(NT)]
    nring = len(profs[0])
    rings = []
    for i in range(nring):
        ring = []
        for k in range(NT):
            inset, z, _ = profs[k][i]
            r = RF[k] - inset
            if k in SEAMS and 7 <= i <= 9:
                r -= 0.14  # modelled panel seam down the wall
            ring.append(at(k, r, z))
        rings.append(ring)
    # deck: from the deck edge in to the socket, a faint crown, the socket chamfer, its wall, floor
    if not wreck:
        inner = [(0.5, Z_DECK + 0.06, "deck"), (1.0, Z_DECK, "deck"), (1.0, Z_DECK - 0.12, "bezel"),
                 (0.985, Z_DECK - 0.5, "socket")]
    else:
        inner = [(0.5, Z_DECK + 0.03, "deck"), (1.0, Z_DECK - 0.05, "deck"), (0.97, Z_DECK - 0.3, "socket"),
                 (0.9, Z_DECK - 1.0, "socket"), (0.0, Z_DECK - 1.0, "pit")]
    for frac, z, _ in inner:
        ring = []
        for k in range(NT):
            # frac 0.5: midway deck edge -> socket; 1.0 the socket edge; < 1 after 1.0: inside the socket
            if frac == 0.5 and _ == "deck":
                r = (RD[k] + RL[k]) / 2
            else:
                r = RL[k] * frac
            ring.append(at(k, r, z))
        rings.append(ring)
    bands = [p[2] for p in profs[0]] + [b for _, _, b in inner]
    vr = [[bm.verts.new(bl(*p)) for p in ring] for ring in rings]

    def band_mat(i):
        name = bands[i + 1]
        if name in ("wall",) and not wreck:
            return lambda k, i=i: I["seam"] if (k in SEAMS or (k + 1) % NT in SEAMS) and i in (7, 8) else I["wall"]
        return I[name]  # the wreck's burn is cut in afterwards (wreck_finish)

    grid_faces(bm, vr, [band_mat(i) for i in range(len(vr) - 1)])
    # bottom (plausible, closed)
    cap(bm, vr[0], bl(O[0], O[1], 0.0), I["toe"], up=False)
    if wreck:
        before = set(bm.faces)
        cap(bm, vr[-1], bl(O[0], O[1], Z_DECK - 1.0), I["pit"])
        wreck_finish(bm, I, keep={f for f in bm.faces if f not in before})
        build_shards(bm, I)
    else:
        build_lens(bm, vr[-1], lens_mats)
    build_details(bm, I, wreck, char)


def build_lens(bm, socket_ring, LM):
    """The glass lens: a low dome from the socket floor, banded rim -> mid -> hot core by the
    distance from the core point (normalised to the lens ellipse)."""
    zs, zt = Z_DECK - 0.5, Z_DECK + 0.85
    fr = [0.94, 0.85, 0.74, 0.6, 0.42, 0.28, 0.14]
    rings = [socket_ring]
    pts = []
    for f in fr:
        h = zs + (zt - zs) * (1 - f * f) ** 0.6
        ring = [at(k, RL[k] * f, h) for k in range(NT)]
        # pull the dome's centre toward the core point (the core sits NW of the lens centre)
        ring = [(x + (CORE[0] - O[0]) * (1 - f) ** 1.5, y + (CORE[1] - O[1]) * (1 - f) ** 1.5, z) for x, y, z in ring]
        pts.append(ring)
        rings.append([bm.verts.new(bl(*p)) for p in ring])

    band = ["rim", "rim", "rim", "mid", "mid", "core", "core", "core"]  # band above ring i (f 0.94 .. 0.16)
    for i in range(len(rings) - 1):
        for k in range(NT):
            m = (k + 1) % NT
            f = bm.faces.new((rings[i][k], rings[i][m], rings[i + 1][m], rings[i + 1][k]))
            f.material_index = LM[band[i]]
    top = bl(CORE[0], CORE[1], zt)
    cap(bm, rings[-1], top, LM["core"])


# The shattered lens (frame 41): shards in the two clusters the sprite shows, cols 8-11 rows 17-19
# and cols 13-15 rows 19-20, each over the pixel(s) of its palette. (centre x, y px, radius px,
# corners, spin deg, top z low / high edge above the pit floor, tilt direction deg, material).
SHARDS = [
    (8.55, 18.45, 0.62, 3, 15, 0.45, 0.95, 200, "shard_192"),
    (9.45, 17.6, 0.55, 3, 70, 0.55, 0.85, 250, "shard_192"),
    (9.5, 18.55, 0.62, 4, 35, 0.6, 1.05, 160, "shard_193"),
    (10.5, 18.4, 0.68, 3, -20, 0.75, 1.2, 330, "shard_201"),
    (10.55, 19.5, 0.62, 4, 50, 0.55, 0.95, 60, "shard_197"),
    (11.5, 17.55, 0.52, 3, 100, 0.5, 0.8, 300, "shard_194"),
    (14.45, 19.45, 0.62, 3, 5, 0.6, 1.1, 20, "shard_196"),
    (15.4, 19.5, 0.5, 3, 80, 0.5, 0.85, 340, "shard_192"),
    (13.5, 20.45, 0.6, 4, 25, 0.5, 0.9, 210, "shard_196"),
    (14.5, 20.5, 0.62, 3, -40, 0.65, 1.15, 120, "shard_199"),
    (15.35, 20.45, 0.48, 3, 40, 0.45, 0.8, 80, "shard_193"),
]
# Dark glass chips low on the pit floor (the sprite's 32-35 in the pit).
CHIPS = [(8.9, 19.6, 0.55, 30), (12.5, 20.5, 0.45, 70), (12.6, 21.3, 0.4, 10), (11.3, 18.5, 0.4, 50)]


def shard_prism(bm, mat, cx, cy, rad, n, spin, zl, zh, tdir):
    """One glass shard: an irregular n-gon in plan whose top is a tilted plane (zl on one side, zh
    on the other, along image direction tdir), standing from just under the pit floor."""
    zf = Z_DECK - 1.05
    pts = []
    for i in range(n):
        a = math.radians(spin + 360 * i / n + 17 * math.sin(3.1 * i + cx))
        rr = rad * (1.0 + 0.18 * math.sin(2.7 * i + cy))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    td = math.radians(tdir)
    tx, ty = math.cos(td), math.sin(td)
    top = []
    for px, py in pts:
        u = ((px - cx) * tx + (py - cy) * ty) / (rad * 1.2)
        z = zf + 0.05 + (zl + zh) / 2 + (zh - zl) / 2 * max(-1.0, min(1.0, u))
        top.append((px, py, z))
    # the top edge slightly narrower than the base: a chipped, tapering shard
    top = [(cx + (px - cx) * 0.82, cy + (py - cy) * 0.82, z) for px, py, z in top]
    base = [(px, py, zf) for px, py in pts]
    loft(bm, [base, top], mat)


def build_shards(bm, I):
    """The wreck's shattered lens: green glass shards standing in the black pit, tall enough to rise
    out of it so the broken lens still reads from the top and the tilted camera."""
    for cx, cy, rad, n, spin, zl, zh, tdir, m in SHARDS:
        shard_prism(bm, I[m], cx, cy, rad, n, spin, zl, zh, tdir)
    for cx, cy, rad, spin in CHIPS:
        shard_prism(bm, I["shard_c"], cx, cy, rad, 3, spin, 0.12, 0.28, spin + 90)


def build_details(bm, I, wreck, char):
    """Bolts round the flange (where the band is wide enough to show them) and a rear access hatch
    on the north wall."""
    for deg in range(-10, 200, 18):
        a = math.radians(deg)
        k = min(range(NT), key=lambda j: abs(((ANG[j] - a + math.pi) % (2 * math.pi)) - math.pi))
        w = RF[k] - RD[k]
        if w < 2.2:
            continue
        s = max(0.2, min(1.0, w / 3.5))
        s *= 0.35 + 0.65 * max(0.0, math.sin(ANG[k]))
        x, y, _ = at(k, RF[k] - 0.42 * s, 0)
        m = I["bolt"]
        if wreck and char(x, y) in (True, "deep"):
            m = I["char"]
        stud(bm, m, x, y, 0.58, 0.17, 0.13)
    # rear hatch: a plate on the north wall with two bolt heads
    k = min(range(NT), key=lambda j: abs(ANG[j] - 1.5 * math.pi))
    x, y, _ = at(k, RF[k] - 0.15, 0)
    hm = I["char"] if wreck else I["hatch"]
    loft(bm, [[(x + dx, y + dy, z) for dx, dy in ((-1.3, -0.12), (1.3, -0.12), (1.3, 0.3), (-1.3, 0.3))]
              for z in (1.4, 2.85)], hm)
    for dx in (-0.9, 0.9):
        stud(bm, I["char"] if wreck else I["bolt"], x + dx, y - 0.14, 2.1, 0.12, 0.0001)


def build_collar(bm, I, COLLAR=COLLAR):
    """The mount collar in the ground: a low dark ring (frame 77's row 26), fixed."""
    angs = [2 * math.pi * k / 96 for k in range(96)]
    src = (COLLAR[0], COLLAR[1])
    rr = [ray(COLLAR, a, src=src) for a in angs]
    def ring(inset, z):
        return [(src[0] + (r - inset) * math.cos(a), src[1] + (r - inset) * math.sin(a), z) for r, a in zip(rr, angs)]
    loft(bm, [ring(0.0, 0.0), ring(0.0, 0.18), ring(0.25, 0.4), ring(1.5, 0.4)], I["collar"])


# --- materials ------------------------------------------------------------------------------------

MATS = {  # name: (palette index, kwargs)
    "deck": (8, dict(metallic=0.6, roughness=0.34)),
    "rim": (11, dict(metallic=0.65, roughness=0.28)),
    "bezel": (10, dict(metallic=0.65, roughness=0.3)),
    "wall": (7, dict(metallic=0.55, roughness=0.4)),
    "seam": (4, dict(metallic=0.5, roughness=0.55)),
    "under": (3, dict(metallic=0.4, roughness=0.6)),
    "flange": (5, dict(metallic=0.55, roughness=0.42)),
    "toe": (2, dict(metallic=0.3, roughness=0.7)),
    "socket": (2, dict(metallic=0.3, roughness=0.7)),
    "bolt": (9, dict(metallic=0.65, roughness=0.32)),
    "hatch": (6, dict(metallic=0.55, roughness=0.42)),
    "collar": (2, dict(metallic=0.3, roughness=0.75)),
}
# The lens per frame: (core, mid, rim) palette indices; emission per band.
LENS_PAL = {77: (201, 195, 193), 79: (206, 198, 195), 81: (207, 204, 199)}
LENS_EM = {"core": 1.0, "mid": 0.85, "rim": 0.6}
WRECK = {  # extra materials of the wreck (frame 41)
    "char": (2, dict(metallic=0.2, roughness=0.85)),
    "scorch": (4, dict(metallic=0.45, roughness=0.6)),
    "scorch_rim": (7, dict(metallic=0.5, roughness=0.5)),
    "char_dark": (1, dict(metallic=0.1, roughness=0.9)),
    "pit": (1, dict(metallic=0.1, roughness=0.9)),
    "shard_192": (192, dict(metallic=1.0, roughness=0.9, emission_strength=0.25)),
    "shard_193": (193, dict(metallic=1.0, roughness=0.9, emission_strength=0.3)),
    "shard_194": (194, dict(metallic=1.0, roughness=0.9, emission_strength=0.35)),
    "shard_196": (196, dict(metallic=1.0, roughness=0.9, emission_strength=0.4)),
    "shard_197": (197, dict(metallic=1.0, roughness=0.9, emission_strength=0.45)),
    "shard_199": (199, dict(metallic=1.0, roughness=0.9, emission_strength=0.5)),
    "shard_201": (201, dict(metallic=1.0, roughness=0.9, emission_strength=0.55)),
    "shard_c": (34, dict(metallic=0.6, roughness=0.6)),
}


# The wreck's front patches are scorched metal, a step or two darker than the intact pod (sprite
# rows 22-25: 4-5 on the wall with dark flecks, 7-8 on the rim edge).
SCORCH = {"wall": "scorch", "seam": "scorch", "rim": "scorch_rim", "deck": "scorch_rim", "flange": "scorch"}


def make_mats(sprite, tag, frame=None, wreck=False):
    names, mats = [], []
    for n, (idx, kw) in MATS.items():
        names.append(n)
        mats.append(common.palette_material(sprite, idx, NAME, **kw))
    lm = {}
    if frame is not None:
        for band, idx in zip(("core", "mid", "rim"), LENS_PAL[frame]):
            lm[band] = len(mats)
            names.append(f"lens_{band}")
            mats.append(common.palette_material(sprite, idx, f"{NAME}-lens{frame}{band}", metallic=1.0, roughness=0.9,
                                                emission_strength=LENS_EM[band]))
    if wreck:
        for n, (idx, kw) in WRECK.items():
            names.append(n)
            mats.append(common.palette_material(sprite, idx, f"{NAME}-wreck", **kw))
    return mats, {n: i for i, n in enumerate(names)}, lm


def _ragged(x, y):
    """A small irregular offset (fraction of a patch radius) for burn edges, so they run as torn lines, not straight cuts."""
    return 0.08 * math.sin(2.3 * x + 1.7 * y + 0.4) + 0.05 * math.sin(3.1 * y - 2.3 * x)


# Unburnt (scorched) patches of the wreck's front wall in plan px (frame 41 rows 22-25), as soft
# blobs (cx, cy, rx, ry): west, the grey bar on row 22 cols 7-11 over the patch of rows 23-25
# cols 6-11; east, cols 13-16 rows 22-25; SE lip: the lit edge of col 19 rows 20-23. Between the
# two front patches runs the crack down col 12 (its own narrow tapered band, CRACK_*), and the east
# patch is burnt through in a hole on row 24 cols 14-15 (WRECK_HOLE). Every boundary is the zero
# line of a smooth field, cut into the mesh (cut_iso), so the burn edges run as faired curves.
WRECK_PATCHES = [(9.0, 24.2, 3.1, 2.55), (14.95, 24.1, 2.15, 2.4), (19.25, 21.9, 0.85, 2.1)]
WRECK_HOLE = (14.95, 24.4, 1.05, 0.75)


def _smooth(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def crack_x(y):
    """The crack's centre line (the sprite's col 12), wandering a little."""
    return 12.45 + 0.12 * math.sin(1.9 * y + 0.7) + 0.05 * math.sin(4.3 * y)


def crack_hw(y):
    """The crack's half width in px: open at the rim (row 22), closing toward the toe."""
    return 0.16 + 0.32 * (1 - _smooth(21.8, 27.0, y))


def f_clean(x, y):
    """> 0 in the unburnt sector from the west round to the north (rim, wall and the deck's north
    strip stay grey: cols 4-7 rows 16-19 and row 16 cols 11-16), in degrees about the lens centre;
    the edges wander with the radius so they run as torn lines."""
    a = math.degrees(math.atan2(y - O[1], x - O[0])) % 360
    r = math.hypot((x - O[0]) / 8.0, (y - O[1]) / 5.0)
    j = 9 * math.sin(7.0 * r + 1.3) + 5 * math.sin(13.0 * r)
    return min(a - (168 + j), (300 - j) - a)


def f_hole(x, y):
    cx, cy, rx, ry = WRECK_HOLE
    return 1 + 0.6 * _ragged(x, y) - math.hypot((x - cx) / rx, (y - cy) / ry)


def f_crack(x, y):
    return crack_hw(y) - abs(x - crack_x(y))


def f_scorch(x, y):
    """> 0 on the scorched (unburnt) patches, less the crack and the hole."""
    g = _ragged(x, y)
    p = max(1 + g - math.hypot((x - cx) / rx, (y - cy) / ry) for cx, cy, rx, ry in WRECK_PATCHES)
    return min(p, -2.0 * f_crack(x, y), -f_hole(x, y))


def char_fn(x, y):
    """The wreck's finish at plan point (x, y): False unburnt, "scorch" scorched metal, "deep" the
    crack and the burnt-through hole (black), True burnt."""
    if f_clean(x, y) > 0:
        return False
    if f_scorch(x, y) > 0:
        return "scorch"
    if f_hole(x, y) > 0 or (f_crack(x, y) > 0 and y > 21.4):
        return "deep"
    return True


def notch_depth(x, y, z):
    """How far (px, along the inward normal) the wreck's surface is pushed in: a V-notch down the
    col-12 crack through the rim and the front wall, tapering out toward the toe, and a steep-sided
    recess for the burnt-through hole. Nothing below the flange moves, so the outline is untouched."""
    zf = _smooth(0.45, 1.15, z)
    d = 0.0
    hw = crack_hw(y) * 1.15
    t = 1 - abs(x - crack_x(y)) / hw
    if t > 0:
        d = max(d, (0.18 + 0.27 * (1 - _smooth(22.0, 26.5, y))) * t * _smooth(21.3, 22.1, y) * (1 - _smooth(25.9, 26.9, y)))
    cx, cy, rx, ry = WRECK_HOLE
    rn = math.hypot((x - cx) / rx, (y - cy) / ry) - 0.6 * _ragged(x, y)
    d = max(d, 0.5 * _smooth(1.0, 0.62, rn))
    return d * zf


def _plan(co):
    return co.x / PX + 12, 14 - co.y / PX, co.z / PX


def cut_iso(bm, fn):
    """Cut the mesh along the zero line of fn(x, y) (plan px): triangulate every face it crosses,
    split each crossed edge at the interpolated zero and split the faces between the new points
    (marching triangles), so a material change along it is a faired curve, not a face staircase."""
    val = {v: fn(*_plan(v.co)[:2]) for v in bm.verts}
    crossed = [f for f in bm.faces if len({val[v] > 0 for v in f.verts}) > 1]
    bmesh.ops.triangulate(bm, faces=crossed)
    on = set()
    for e in [e for e in bm.edges if (val[e.verts[0]] > 0) != (val[e.verts[1]] > 0)]:
        v0, v1 = e.verts
        t = max(0.02, min(0.98, val[v0] / (val[v0] - val[v1])))
        _e, nv = bmesh.utils.edge_split(e, v0, t)
        val[nv] = 0.0
        on.add(nv)
    for f in [f for f in bm.faces if sum(v in on for v in f.verts) >= 2]:
        vs = [v for v in f.verts if v in on]
        if len(vs) == 2 and not any(e for e in vs[0].link_edges if vs[1] in e.verts):
            bmesh.utils.face_split(f, vs[0], vs[1])


def wreck_finish(bm, I, keep=()):
    """The wreck's burn: subdivide the front (where the patches, crack and hole are), cut every burn
    boundary along its smooth field, give each face its finish by its centre, then press in the
    crack's V-notch and the hole's recess."""
    names = {i: n for n, i in I.items()}
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    def front(f):
        x, y, z = _plan(f.calc_center_median())
        return y > 21.0 and 5.3 < x < 19.2 and f.normal.z > -0.3 and names[f.material_index] not in ("pit", "socket")

    bm.normal_update()
    sel = [f for f in bm.faces if front(f)]
    bmesh.ops.subdivide_edges(bm, edges=list({e for f in sel for e in f.edges}), cuts=2, use_grid_fill=True)
    for fn in (f_clean, f_scorch, f_hole, lambda x, y: min(f_crack(x, y), y - 21.4)):
        cut_iso(bm, fn)
    for f in bm.faces:
        if f in keep:
            continue
        name = names[f.material_index]
        c = char_fn(*_plan(f.calc_center_median())[:2])
        if c is True:
            f.material_index = I["char_dark" if name in ("toe", "under", "socket") else "char"]
        elif c == "deep":
            f.material_index = I["char_dark"]
        elif c == "scorch":
            f.material_index = I[SCORCH.get(name, name)]
    bm.normal_update()
    moves = []
    for v in bm.verts:
        d = notch_depth(*_plan(v.co))
        if d > 1e-4:
            moves.append((v, -v.normal * (d * PX)))
    for v, dv in moves:
        v.co += dv


# --- assemble -------------------------------------------------------------------------------------

def make_object(name, coll, sprite, frame, wreck, dy):
    global RF
    RF = [ray(FOOT_WRECK if wreck else FOOT, a) for a in ANG]
    mats, I, lm = make_mats(sprite, name, None if wreck else frame, wreck)
    bm = bmesh.new()
    build_pod(bm, I, lm, wreck=wreck, char=char_fn)
    pod = common.mesh_object(f"{name}_pod", bm, mats, coll, smooth=True)
    pod.data.transform(Matrix.Translation((0.0, -dy * PX, 0.0)))
    bm = bmesh.new()
    build_collar(bm, I, COLLAR_WRECK if wreck else COLLAR)
    col = common.mesh_object(f"{name}_collar", bm, mats, coll, smooth=True)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(o in (pod, col))
    bpy.context.view_layer.objects.active = pod
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    obj.data.set_sharp_from_angle(angle=math.radians(35))
    return obj


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    out = []
    for frame, dy, wreck in ((77, 0, False), (79, 1, False), (81, 2, False), (41, 0, True)):
        name = NAME if frame == 77 else f"{NAME}-{frame}"
        obj = make_object(name, coll, sprite, frame, wreck, dy)
        seal = bpy.data.objects.new(f"{name}_seal", obj.data.copy())
        coll.objects.link(seal)
        bpy.context.view_layer.update()
        shell = common.outline_shell(seal, coll, voxel=0.01, faces=1500, smooth=5, inside=0.003)
        shell.name = shell.data.name = f"{name}_outline"
        bpy.data.objects.remove(seal, do_unlink=True)
        T.cull_hidden(obj)
        common.frame_part(obj, [frame])
        common.frame_part(shell, [frame])
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print("built", name, "frame", frame, "triangles", tris, "shell faces", len(shell.data.polygons))
        out += [obj, shell]
    sprites = [dict(sprite["sprites"][0], frames=[77, 79, 81, 41])]
    common.export_sprite_model(WT, out, MODEL, sprites)


if __name__ == "__main__":
    main()
