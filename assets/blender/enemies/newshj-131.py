"""newshj-131, final: the green beetle pod on its red mount (newshj.shp size 2, frame 131,
24 x 28 px), rebuilt as what it is (D65, D120, D122).

WHAT IT IS: an armoured green beetle-shell pod carried in a red cradle. Episode 2 custom-picture
enemy (events 49-52, bank 14, armor 5-15); link events move it a little relative to the terrain
(ev19 eyc 1-2, ev20 oscillation), so it is a mobile unit, not a building: no floor plate, a round
closed underside that reads both resting on the ground and hovering just over it.

Reading the sprite (row/col = sprite pixel; edges in px; mirror axis = column 12's centre, x 12.5):
- Carapace rows 8-15, inner mask cols 3-21 (half width 9.5): from the axis out, a raised pale
  armour plate (cols 10-14, 44; the 46/47 blaze in its middle is the white-hot SHEEN, not a bump),
  a dark channel (col 9, 39), a narrow rib (col 8, 42), the shell (col 7, 38-41), a dark groove
  (col 6, 35-37: the seam between shell and shoulder) and a shoulder pod (cols 3-5, 41) whose
  crest is on its inner side (col 5 is the pale 44 line, symmetric, so it is the pod's crest
  catching the light, not paint). Row 9 col 5 (47) is sheen.
- Head rows 5-7, cols 9-15 (40): a short domed head with a central keel (col 12, 42-43) and two
  slanted pale eyes (46 at row 6 col 11, 45 at row 7 col 10; mirrored).
- Red corner blocks rows 6-7, cols 5-7 (113/114) each with a lit red stud (119 at row 6 col 6),
  separated from the head by the dark gap at col 8 (the mount deck seen between them).
- Side housings rows 16-21, cols 5-7 (114) with a bright ridge (117/120) and a yellow lamp
  (124, row 19 col 6); a dark gap at col 8 again shows the deck.
- Split tail rows 16-22, cols 9-15: two lobes (39, crests 42/43 at rows 18-19) with a dark
  channel between (34-35, col 12) and a short tip (38) at rows 20-22.
- Red rim (114/115/116) round the bottom, rows 21-23, from each housing in under the tail tip.

Build: a red mount (deck with a round closed underside, blocks, housings, rim), the carapace on it
as pchip lofts with superellipse (chamfered) sections, raised plate / ribs / shoulder pods as
separate armour pieces with real seams, the head with keel and inset lenses. Outline shell from a
sealed pre-cull copy (D51/D90/D118); hidden faces then culled. No bake folder exists for this
model, so no maps.

    tools/build-models.sh -j 2 assets/blender/enemies/newshj-131.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

HERE = Path(__file__).resolve().parent
NAME = "newshj-131"
MODEL = f"enemies/{NAME}"
PX = 1 / 12
AX = 12.5  # mirror axis (column edge)


def bl(x, y, z):
    """Sprite px (column edge, row edge, height) to Blender units (24 x 28 block, centred)."""
    return Vector(((x - 12) * PX, (14 - y) * PX, z * PX))


# --- mesh helpers ----------------------------------------------------------------------------

def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def section(cx, y, hw, zb, zt, zc=None, n_top=2.6, n_bot=4.0, N=20, crown=None):
    """A closed superellipse section in the XZ plane at row y: half width hw, from zb to zt,
    widest at zc. Higher n = squarer (a chamfered box at ~4). `crown(u)` adds height at
    normalised x u in [-1, 1] on the top half (a profile across the piece)."""
    zc = zb + 0.35 * (zt - zb) if zc is None else zc
    pts = []
    for k in range(N):
        t = 2 * math.pi * k / N
        c, s = math.cos(t), math.sin(t)
        if s >= 0:
            u = spow(c, 2 / n_top)
            z = zc + (zt - zc) * spow(s, 2 / n_top)
            if crown:
                z += crown(u) * spow(s, 2 / n_top)
        else:
            u = spow(c, 2 / n_bot)
            z = zc + (zc - zb) * spow(s, 2 / n_bot)
        pts.append((cx + hw * u, y, z))
    return pts


def loft(bm, rings, mat, cap=True):
    """Quads between successive rings (lists of (x, y, z) sprite px), fan caps at the ends."""
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rings]
    faces = []
    for r0, r1 in zip(vr, vr[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    if cap:
        for r, flip in ((vr[0], True), (vr[-1], False)):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / len(r))
            n = len(r)
            for i in range(n):
                j = (i + 1) % n
                faces.append(bm.faces.new((r[j], r[i], c) if flip else (r[i], r[j], c)))
    for f in faces:
        f.material_index = mat
    return faces


def pod(bm, mat, cx, stations, N=20, n_top=2.6, n_bot=4.0, crown=None, zc_frac=0.35):
    """A loft along y: stations [(y, hw, zb, zt)], pchip-interpolated at 0.25 px steps (finer at
    the ends so noses stay round)."""
    ys = [s[0] for s in stations]
    f_hw = T.pchip(ys, [s[1] for s in stations])
    f_zb = T.pchip(ys, [s[2] for s in stations])
    f_zt = T.pchip(ys, [s[3] for s in stations])
    y0, y1 = ys[0], ys[-1]
    steps = max(6, int((y1 - y0) / 0.5))
    rings = []
    for i in range(steps + 1):
        u = i / steps
        y = y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(math.pi * u))  # cosine spacing: dense ends
        hw = max(0.04, f_hw(y))
        zb, zt = f_zb(y), f_zt(y)
        rings.append(section(cx, y, hw, zb, zt, zc=zb + zc_frac * (zt - zb), n_top=n_top, n_bot=n_bot, N=N,
                             crown=(lambda uu, y=y: crown(uu, y)) if crown else None))
    return loft(bm, rings, mat)


def sweep(bm, mat, path, sides=12, n=3.0):
    """A tube through path [(x, y, z, half_w, half_h)] (sprite px), sections upright,
    squarish (superellipse n), capped."""
    pts = [Vector((p[0], p[1], p[2])) for p in path]
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = Vector((-t.y, t.x, 0))
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            q = Vector((x, y, z)) + side * (w * spow(math.cos(a), 2 / n)) + Vector((0, 0, h * spow(math.sin(a), 2 / n)))
            ring.append(tuple(q))
        rings.append(ring)
    return loft(bm, rings, mat)


def hull(bm, mat, pts):
    """Convex hull of sprite-px points (a chamfered block), coplanar faces merged."""
    verts = [bm.verts.new(bl(*p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    for f in faces:
        f.material_index = mat
    return faces


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    chz = ch if chz is None else chz
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(x + sx * ch, y, z + sz * chz), (x, y + sy * ch, z + sz * chz), (x + sx * ch, y + sy * ch, z)]
    return pts


def dome(bm, mat, cx, cy, rx, ry, z0, h, seg=14, rings=5, tilt=0.0, base=0.15):
    """A lens/stud: an elliptic dome on a short skirt from z0 - base, rotated by tilt (radians)."""
    ca, sa = math.cos(tilt), math.sin(tilt)
    def P(u, v, z):
        return (cx + u * ca - v * sa, cy + u * sa + v * ca, z)
    rs = [[P(rx * math.cos(2 * math.pi * k / seg), ry * math.sin(2 * math.pi * k / seg), z0 - base) for k in range(seg)]]
    for i in range(rings):
        th = (math.pi / 2) * i / rings
        rs.append([P(rx * math.cos(th) * math.cos(2 * math.pi * k / seg), ry * math.cos(th) * math.sin(2 * math.pi * k / seg),
                     z0 + h * math.sin(th)) for k in range(seg)])
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rs]
    top = bm.verts.new(bl(cx, cy, z0 + h))
    faces = []
    for r0, r1 in zip(vr, vr[1:]):
        for k in range(seg):
            m = (k + 1) % seg
            faces.append(bm.faces.new((r0[k], r0[m], r1[m], r1[k])))
    for k in range(seg):
        m = (k + 1) % seg
        faces.append(bm.faces.new((vr[-1][k], vr[-1][m], top)))
    c = bm.verts.new(bl(cx, cy, z0 - base))
    for k in range(seg):
        m = (k + 1) % seg
        faces.append(bm.faces.new((vr[0][m], vr[0][k], c)))
    for f in faces:
        f.material_index = mat
    return faces


def cyl_x(bm, mat, x0, x1, y, z, r, seg=10):
    """A pin along x."""
    rings = [[(x, y + r * math.cos(2 * math.pi * k / seg), z + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
             for x in (x0, x1)]
    return loft(bm, rings, mat)


def mirror_x(bm, faces):
    """Mirror the given faces about the axis (x = AX) as new geometry."""
    geom = list({v for f in faces for v in f.verts}) + faces + list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=geom)
    nv = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    ax = (AX - 12) * PX
    for v in nv:
        v.co.x = 2 * ax - v.co.x
    nf = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=nf)
    return nf


# --- the model ---------------------------------------------------------------------------------

MATS = [  # (palette index, kwargs)
    (114, dict(metallic=0.35, roughness=0.5)),   # 0 MOUNT: deck, rim, housings
    (113, dict(metallic=0.35, roughness=0.55)),  # 1 BLOCK: corner blocks, hinge pins, deck skirt
    (117, dict(metallic=0.35, roughness=0.4)),   # 2 RIDGE: housing ridge
    (119, dict(metallic=0.2, roughness=0.3)),    # 3 STUD: lit red studs (glossy, sheen)
    (124, dict(metallic=0.0, roughness=0.25, emission_strength=1.0)),  # 4 LAMP: yellow lamps
    (38, dict(metallic=0.15, roughness=0.5)),    # 5 SHELL: carapace shell between the plates
    (41, dict(metallic=0.15, roughness=0.42)),   # 6 SHOULDER pods
    (44, dict(metallic=0.15, roughness=0.3)),    # 7 PLATE: raised centre plate (sheen: glossy)
    (42, dict(metallic=0.15, roughness=0.4)),    # 8 RIB
    (40, dict(metallic=0.15, roughness=0.45)),   # 9 HEAD
    (46, dict(metallic=0.0, roughness=0.15, emission_strength=0.35)),  # 10 EYE lenses
    (43, dict(metallic=0.15, roughness=0.4)),    # 11 KEEL
    (39, dict(metallic=0.15, roughness=0.45)),   # 12 TAIL lobes
    (35, dict(metallic=0.15, roughness=0.6)),    # 13 CHANNEL between the lobes
    (112, dict(metallic=0.3, roughness=0.6)),    # 14 DECK dark (seen in the gaps)
]
(MOUNT, BLOCK, RIDGE, STUD, LAMP, SHELL, SHOULDER, PLATE, RIB, HEAD, EYE, KEEL, TAIL, CHANNEL,
 DECK) = range(len(MATS))

Z_DECK = 1.6     # top of the mount deck
Z_SHELL0 = 1.3   # carapace underside


def build_left(bm):
    """Parts with a mirror twin (built on the left, x < AX)."""
    L = []
    # Corner block (rows 6-7, cols 5-7) with its lit stud.
    L += hull(bm, BLOCK, cbox(5.0, 8.0, 5.95, 8.6, 0.4, 4.3, 0.45, 0.4))
    L += dome(bm, STUD, 6.55, 6.85, 0.95, 0.85, 4.25, 0.75, seg=14, rings=4)
    # bolt heads on the block's front face corners (machined detail)
    L += dome(bm, BLOCK, 7.55, 7.75, 0.28, 0.28, 4.25, 0.18, seg=8, rings=2)
    # hinge pin: the carapace pivots on the blocks
    L += cyl_x(bm, BLOCK, 7.7, 9.0, 8.15, 3.6, 0.55)
    # Side housing (rows 16-21, cols 5-7): a chamfered pod with a ridge and the lamp near its rear.
    L += pod(bm, MOUNT, 6.5, [(15.7, 0.9, 0.3, 3.4), (16.4, 1.5, 0.3, 4.0), (18.0, 1.55, 0.3, 4.1),
                              (20.4, 1.55, 0.3, 3.9), (21.5, 1.35, 0.3, 3.4), (22.2, 0.6, 0.3, 2.6)],
             N=20, n_top=3.6, n_bot=3.0)
    L += pod(bm, RIDGE, 6.5, [(16.5, 0.2, 3.6, 4.15), (17.0, 0.5, 3.7, 4.35), (18.3, 0.5, 3.7, 4.3),
                              (18.8, 0.2, 3.6, 4.1)], N=10, n_top=2.4, n_bot=2.0)
    # lamp: a bezel ring and an emissive lens
    L += dome(bm, BLOCK, 6.5, 19.5, 0.95, 0.95, 3.95, 0.12, seg=14, rings=2)
    L += dome(bm, LAMP, 6.5, 19.5, 0.72, 0.72, 4.02, 0.42, seg=14, rings=4)
    # bolts at the housing's rear
    L += dome(bm, BLOCK, 6.5, 21.25, 0.3, 0.3, 3.45, 0.15, seg=8, rings=2)
    # Shoulder pod (cols 3-5, rows 9-15): crest on its inner side.
    def sh_crown(u, y):
        return 0.9 * math.exp(-((u - 0.45) / 0.45) ** 2)  # crest toward the inner edge (u > 0 = +x)
    L += pod(bm, SHOULDER, 4.62, [(8.3, 0.7, Z_SHELL0, 4.0), (8.9, 1.45, Z_SHELL0, 5.3), (9.9, 1.68, Z_SHELL0, 5.8),
                                (14.2, 1.68, Z_SHELL0, 5.7), (15.2, 1.45, Z_SHELL0, 5.0), (15.85, 0.7, Z_SHELL0, 3.8)],
             N=22, n_top=2.3, n_bot=3.0, crown=sh_crown)
    # Rib (col 8, rows 8-15).
    L += pod(bm, RIB, 8.5, [(7.9, 0.2, 5.0, 6.4), (8.5, 0.55, 5.2, 7.15), (13.8, 0.55, 5.2, 7.0),
                            (15.0, 0.5, 4.6, 6.3), (15.6, 0.2, 4.0, 5.4)], N=10, n_top=2.6, n_bot=2.0)
    # Tail lobe (cols 9-10, rows 16-21).
    L += pod(bm, TAIL, 10.2, [(15.4, 1.0, 2.0, 5.6), (16.3, 1.45, 2.0, 5.2), (18.3, 1.4, 2.0, 4.6),
                              (20.0, 1.1, 2.0, 3.9), (20.9, 0.4, 2.0, 3.2)], N=16, n_top=2.4, n_bot=3.0)
    # Eye lens (slanted, rows 6-7, cols 10-11).
    L += dome(bm, EYE, 10.95, 6.95, 1.05, 0.55, 5.35, 0.3, seg=14, rings=3, tilt=math.radians(-42), base=0.6)
    # Rim half: from the housing round under the tail to the axis.
    L += sweep(bm, MOUNT, [(6.4, 20.6, 1.5, 1.15, 1.25), (6.9, 21.9, 1.5, 1.05, 1.25), (8.0, 22.75, 1.45, 0.95, 1.2),
                           (9.6, 23.15, 1.4, 0.85, 1.15), (11.4, 23.2, 1.35, 0.8, 1.1), (12.5, 23.2, 1.35, 0.8, 1.1)],
               sides=12, n=3.0)
    return L


def build_centre(bm):
    # Mount deck: a low chamfered slab under everything, round closed underside.
    pod(bm, DECK, AX, [(5.05, 3.4, 0.0, Z_DECK), (5.7, 6.6, 0.0, Z_DECK), (6.5, 7.4, 0.0, Z_DECK),
                       (12.0, 7.4, 0.0, Z_DECK), (20.5, 7.4, 0.0, Z_DECK), (21.8, 6.6, 0.0, Z_DECK),
                       (22.6, 4.5, 0.0, Z_DECK), (23.0, 2.0, 0.0, Z_DECK)], N=20, n_top=5.0, n_bot=2.2, zc_frac=0.6)
    # Carapace shell (rows 8-16): the dome the armour sits on.
    pod(bm, SHELL, AX, [(7.75, 5.0, Z_SHELL0, 5.2), (8.3, 7.3, Z_SHELL0, 6.0), (9.0, 8.4, Z_SHELL0, 6.3),
                        (10.0, 9.0, Z_SHELL0, 6.8), (14.0, 9.0, Z_SHELL0, 6.7), (15.2, 8.2, Z_SHELL0, 6.0),
                        (15.9, 6.4, Z_SHELL0, 5.4), (16.3, 3.0, Z_SHELL0, 4.6)], N=24, n_top=2.2, n_bot=3.5)
    # Raised centre plate (cols 10-14): crowned, chamfered; sheen comes from the gloss.
    pod(bm, PLATE, AX, [(7.7, 1.6, 6.0, 7.2), (8.4, 2.4, 6.0, 7.8), (10.0, 2.5, 6.1, 8.2), (12.5, 2.5, 6.1, 8.2),
                        (14.0, 2.2, 5.9, 7.8), (15.0, 1.5, 5.5, 7.1), (15.7, 0.7, 5.1, 6.4)],
        N=20, n_top=3.2, n_bot=2.0, crown=lambda u, y: 0.45 * (1 - u * u))
    # a centre seam on the plate (the panel line down the spine)
    pod(bm, SHELL, AX, [(8.6, 0.06, 7.8, 8.36), (9.4, 0.13, 8.0, 8.7), (13.6, 0.13, 8.0, 8.7), (14.3, 0.06, 7.7, 8.3)],
        N=8, n_top=2.0, n_bot=2.0)
    # Head (rows 5-8, cols 9-15): a domed head with a keel ridge.
    pod(bm, HEAD, AX, [(5.0, 1.6, 1.0, 3.6), (5.4, 3.5, 1.0, 4.6), (6.2, 3.9, 1.0, 5.4), (7.5, 3.75, 1.0, 5.9),
                       (8.6, 3.4, 1.0, 6.0)], N=22, n_top=2.3, n_bot=3.0)
    pod(bm, KEEL, AX, [(5.0, 0.3, 3.0, 4.0), (5.5, 0.6, 3.6, 5.05), (7.0, 0.62, 4.6, 6.2), (8.2, 0.6, 5.2, 6.6),
                       (8.8, 0.3, 5.6, 6.9)], N=10, n_top=2.4, n_bot=2.0)
    # Tail core (the dark channel between the lobes) and the tip.
    pod(bm, CHANNEL, AX, [(15.4, 2.6, 2.0, 5.2), (16.5, 2.3, 2.0, 4.5), (19.0, 1.6, 2.0, 3.7), (20.4, 1.0, 2.0, 3.3)],
        N=16, n_top=2.4, n_bot=3.0)
    pod(bm, TAIL, AX, [(15.3, 1.4, 4.3, 5.75), (16.3, 1.3, 4.3, 5.3), (17.4, 0.7, 4.0, 4.6), (17.9, 0.2, 3.8, 4.2)],
        N=12, n_top=2.4, n_bot=2.0)  # the bridge between the lobes at row 16-17
    pod(bm, TAIL, AX, [(19.6, 0.4, 2.0, 3.4), (20.3, 1.45, 2.0, 3.55), (21.6, 1.3, 2.0, 3.35), (22.6, 0.75, 2.1, 3.0),
                       (23.0, 0.2, 2.2, 2.6)], N=14, n_top=2.4, n_bot=3.0)


def build(coll, sprite):
    mats = [common.palette_material(sprite, i, NAME, **kw) for i, kw in MATS]
    bm = bmesh.new()
    left = build_left(bm)
    mirror_x(bm, left)
    build_centre(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(38))
    return obj


def sealed_copy(obj, coll):
    me = obj.data.copy()
    seal = bpy.data.objects.new(f"{NAME}_seal", me)
    coll.objects.link(seal)
    return seal


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    seal = sealed_copy(obj, coll)  # pre-cull copy for the outline shell (D90/D118)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.01, faces=1500, smooth=5, inside=0.003)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(seal, do_unlink=True)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    print("triangles", tris, "shell faces", len(shell.data.polygons))


if __name__ == "__main__":
    main()
