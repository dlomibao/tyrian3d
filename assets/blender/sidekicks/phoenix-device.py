"""Phoenix Device (sidekick 8, tyrian.shp#8 frames 171, 190, 209, 228): a 3D version of its sprite.

What it is: a mounted side pod (style 0) that holds a ball of fire. The sprite is a round orb 11 px
across (columns 1-11, rows 1-11 of the 12x14 block, centre at px 6.5, 6.5) drawn in the fire ramp
112-127: a white-hot core up and left of centre (127/126), a yellow ring round it (124/125), orange
(121-123) and red (114-117) towards the rim at the top and left, and a bright yellow-white flame
tongue (125-127) curling round the lower right edge with a darker red band inside it. The four
frames are the same drawing cooling: 171 white-hot, 190 and 209 orange, 228 dark red; the loop
171, 190, 209, 228, 209, 190 makes it pulse.

As a machine:
- The orb: one smooth sphere (radius 5.5 px, the sprite's disc) whose fire bands are cut into the
  mesh by planes (caps on the sphere: exact, smooth boundaries, not per-face steps): five core
  bands round an axis through px (5.5, 5.5) and three flame-tongue bands round an axis low on the
  lower right, which wrap on down the side of the ball. Each band is one pal_<index> material
  that glows; its index on each frame is the median of the sprite's pixels under it on that frame
  (palette_material frames=, D17), so the one model pulses with the sprite.
- The cradle (all inside the orb's top-view disc, so the top view stays the sprite): a machined
  collar ring below the equator, four clamp claws that hug the ball above it, four small vent
  windows in the collar that glow with the core, and a hub under the collar with eight cooling
  fins, ending in a mounting stub. Dark red-black metal (the sprite's darkest indices 112-114).

Per-frame silhouette (D17 frame parts): the cooled frames 190, 209 and 228 draw the ball's rim in
the darkest fire steps (112/113, ink by tools/sprite_mask.py, heavy on the top and left), so the game's
own ink outline round the model takes their place and the model's top view goes to each frame's
inner mask (docs/agents/OUTLINE-BORDER.md). One orb per frame (frame_part), the same mesh and fire
bands, scaled and shifted onto its frame: full size on white-hot 171, shrunk about 7-11 % and moved
down-right as it cools, 209 and 228 with a low flame lick on the upper left where their colour runs
to the rim. The fireball swells and shrinks with its pulse. Each frame has its own outline shell.
The cradle is one part sized to sit inside every frame's ball.

Build: tools/build-models.sh -j 2 assets/blender/sidekicks/phoenix-device.py (review renders: -- --render <dir>)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "sidekick-phoenix-device"
MODEL = "sidekicks/phoenix-device"
P = 1 / 12  # one sprite pixel
CXp, CYp = 6.5, 6.5  # the orb's centre in sprite px
OX, OY = (CXp - 6) * P, (7 - CYp) * P  # world: the 12x14 block is centred on the origin
R_PX = 5.5
R = R_PX * P
ORB_Z = 1.2 * P
C = Vector((OX, OY, ORB_Z))

# Each frame's orb on the sprite grid, fitted to that frame's inner mask (scratch fit/fit3.py):
# centre px (cx, cy), radius px, flame lick (px, at that angle, degrees anticlockwise from +x).
ORB_FRAMES = {
    171: (6.5, 6.5, 5.5, 0.0, 0.0),
    190: (6.7, 7.0, 5.1, 0.0, 0.0),
    209: (6.7, 6.95, 5.1, 0.5, 120.0),
    228: (7.0, 7.0, 4.9, 0.5, 135.0),
}
# The cradle: centre px and the radius px of the ball it is built round (inside every frame's disc:
# its collar and bolts reach 0.955 * 4.55 + 0.24 = 4.59 px, 0.25 px off centre from 228's 4.9).
CRADLE_AT, CRADLE_R_PX = (6.8, 6.85), 4.55
CC = Vector(((CRADLE_AT[0] - 6) * P, (7 - CRADLE_AT[1]) * P, ORB_Z))
RC = CRADLE_R_PX * P

# --- Fire bands (anchors fitted to the sprite by fit_regions.py: 1.14 index/px mean error over the
# frames). Two families of bands, each the level sets of a smooth field on the sphere: the core's
# (round an axis through px 5.5, 5.5) and the flame tongue's (round an axis low over the lower right,
# fading out below the equator so from the side it is a crescent on the ball's shoulder, not a disc). The fields
# twist in a gentle spiral round their axes, so the band edges lick like flames instead of drawing a
# target. A narrow transition band (half way in palette steps) straddles each anchor edge, so the
# fire grades smoothly from the side as the sprite's pixels do from above.
CORE_AT = (5.5, 5.5)  # sprite px under the core axis
CORE_T = (0.45, 0.70, 0.88, 0.96)  # field > t: core levels 1..4 (0 = the rim beyond)
TONGUE_AT, TONGUE_Z = (9.0, 10.5), 0.2  # the flame tongue's axis: low over the lower right
TONGUE_T = (0.65, 0.80, 0.90)  # field > t: tongue levels 1..3
CORE_MIX = (1, 2)  # core edges that get a transition band (the others step one palette index only)
TONGUE_MIX = (1,)
Z_FADE = 0.2  # the tongue fades out below this (normal z)
W = 0.022  # half width of a transition band (field units)
WAVE = 0.025  # flame-lick amplitude (field units)


def axis(px, py, z=None):
    a = Vector(((px - CXp) / R_PX, -(py - CYp) / R_PX, 0.0))
    a.z = math.sqrt(max(0.0, 1 - a.x ** 2 - a.y ** 2)) if z is None else z
    return a.normalized()


CORE = axis(*CORE_AT)
TONGUE = axis(*TONGUE_AT, TONGUE_Z)


def _frame(ax):
    u = ax.cross(Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))).normalized()
    return u, ax.cross(u)


CU, CV = _frame(CORE)
TU, TV = _frame(TONGUE)


def field(n, ax, u, v, k, twist, phase):
    d = n.dot(ax)
    th = math.atan2(n.dot(v), n.dot(u))
    return d + WAVE * max(0.0, 1 - d * d) ** 0.5 * math.sin(k * th + twist * (1 - d) + phase)


def fc(n):
    return field(n, CORE, CU, CV, 3, 7.0, 0.4)


def fk(n):
    """The tongue's field, fading out down the ball's side below Z_FADE (smoothly, so its lower edge
    curls round the ball instead of ending on a straight cut; the top view, normal z >= 0.24 at the
    rim, is untouched)."""
    return field(n, TONGUE, TU, TV, 4, 7.0, 1.3) - 1.1 * max(0.0, Z_FADE - n.z)


def coarse(n, c=None, k=None):
    """(family, level): family 0 core (levels 0..4), 1 tongue (levels 1..3). `c`, `k`: the fields'
    values if already known (a face's mean over its corners)."""
    k = fk(n) if k is None else k
    if k > TONGUE_T[0]:
        return 1, sum(k > t for t in TONGUE_T)
    c = fc(n) if c is None else c
    return 0, sum(c > t for t in CORE_T)


def pixel_normal(x, y, frame=None):
    """The orb's surface normal seen at the centre of sprite pixel (x, y) from above: on the base
    orb, or on sprite frame `frame`'s orb (None where the pixel is off that frame's disc, its ink)."""
    cx, cy, r_px = (CXp, CYp, R_PX) if frame is None else ORB_FRAMES[frame][:3]
    nx, ny = (x + 0.5 - cx) / r_px, -(y + 0.5 - cy) / r_px
    r = math.hypot(nx, ny)
    if frame is not None and r > 1.0:
        return None
    if r > 0.97:
        nx, ny = nx * 0.97 / r, ny * 0.97 / r
    return Vector((nx, ny, math.sqrt(max(0.0, 1 - nx * nx - ny * ny))))


def anchor_tables(sprite):
    """{(family, level): (palette index per frame, in sprite frame order)}: the median of the sprite's
    pixels under each coarse band on each frame. The bands stay on the same sprite pixels on every
    frame (each frame's orb is cut through warp(), below); a frame's pixels off its own ball (its
    ink ring, drawn by the game's outline) are left out."""
    frames = sprite["frames"]
    px = [(x, y) for y, row in enumerate(frames[0]["pixels"]) for x, v in enumerate(row) if v >= 0]
    base = {xy: coarse(pixel_normal(*xy)) for xy in px}

    def median(vals):
        vals = sorted(vals)
        m = len(vals) // 2
        return vals[m] if len(vals) % 2 else round((vals[m - 1] + vals[m]) / 2 + 1e-9)

    out = {}
    for key in sorted(set(base.values())):
        tab = []
        for f in frames:
            labs = {xy: l for xy, l in base.items() if pixel_normal(*xy, f["index"]) is not None}
            vals = [f["pixels"][y][x] for (x, y), l in labs.items() if l == key]
            if not vals:
                vals = [f["pixels"][y][x] for (x, y), l in base.items() if l == key]
            tab.append(median(vals))
        out[key] = tuple(tab)
    return out


def mix(a, b):
    return tuple(int(math.floor((x + y) / 2 + 0.5)) for x, y in zip(a, b))


def fine_table(c, k, anchors):
    """The palette indices per frame where the fields are c (core) and k (tongue), transition bands
    included."""
    fam, lvl = coarse(None, c, k)
    if fam == 1:
        for j in TONGUE_MIX:
            if abs(k - TONGUE_T[j]) < W:
                return mix(anchors[(1, j)], anchors[(1, j + 1)])
        return anchors[(1, lvl)]
    for j in CORE_MIX:
        if abs(c - CORE_T[j]) < W:
            return mix(anchors[(0, j)], anchors[(0, j + 1)])
    return anchors[(0, lvl)]


def fire_material(sprite, tab, glow, tag):
    frames = [f["index"] for f in sprite["frames"]]
    base = tab[0]
    others = {f: i for f, i in zip(frames[1:], tab[1:]) if i != base}
    return common.palette_material(sprite, base, f"{NAME}-{tag}", metallic=0.0, roughness=0.7,
                                   emission_strength=glow, frames=others)


def iso_cut(bm, f, t, centre, radius, tags=None, fam=None):
    """Cut the (triangulated) sphere along the level set f(n) = t: split each crossing edge at the
    interpolated point (put back on the sphere) and join the two new points in each triangle."""
    val = {v: f((v.co - centre).normalized()) - t for v in bm.verts}
    on = {v for v, x in val.items() if abs(x) < 1e-9}
    for e in list(bm.edges):
        a, b = e.verts
        fa, fb = val[a], val[b]
        if fa * fb < 0:
            ne, nv = bmesh.utils.edge_split(e, a, fa / (fa - fb))
            nv.co = centre + (nv.co - centre).normalized() * radius
            val[nv] = 0.0
            on.add(nv)
            if tags is not None:
                tags.setdefault(nv, {})[fam] = t  # its exact level (its field value drifts once on the sphere)
    for face in list(bm.faces):
        vs = [v for v in face.verts if v in on]
        if len(vs) == 2 and not any(vs[1] in e.verts for e in vs[0].link_edges):
            bmesh.ops.connect_verts(bm, verts=vs)
    bmesh.ops.triangulate(bm, faces=[fc_ for fc_ in bm.faces if len(fc_.verts) > 3])


# --- Hard-surface helpers (local copies; nothing shared is edited).

def revolve(bm, prof, seg, mat, centre=C, cap_top=False, cap_bot=False, phase=0.0):
    """A solid of revolution about the orb's vertical axis: `prof` is (radius, z) points."""
    rings = []
    for i in range(seg):
        a = 2 * math.pi * (i + phase) / seg
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((centre.x + r * ca, centre.y + r * sa, z)) for r, z in prof])
    faces = []
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for k in range(len(prof) - 1):
            f = bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
            f.material_index = mat
            faces.append(f)
    if cap_bot:
        bm.faces.new([rings[i][0] for i in range(seg)][::-1]).material_index = mat
    if cap_top:
        bm.faces.new([rings[i][-1] for i in range(seg)]).material_index = mat
    return rings


def chamfer_ring(r_in, r_out, z0, z1, b):
    """(radius, z) profile of a ring with a rectangular section, its outer corners chamfered by b,
    going round from inner bottom to inner top (closed by revolve's last strip back to the start)."""
    return [(r_in, z0), (r_out - b, z0), (r_out, z0 + b), (r_out, z1 - b), (r_out - b, z1), (r_in, z1), (r_in, z0)]


def box(bm, centre, u, v, w, hu, hv, hw, mat, ch=0.0):
    """A chamfered box at `centre` with axes u, v, w (unit) and half sizes; chamfer on the w-top edges."""
    pts = []
    for sw, inset in ((-1, 0.0), (1 - ch / max(hw, 1e-6) if ch else 1, 0.0), (1, ch)):
        loop = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            loop.append(bm.verts.new(centre + u * (su * (hu - inset)) + v * (sv * (hv - inset)) + w * (sw * hw)))
        pts.append(loop)
    if not ch:
        pts = [pts[0], pts[2]]
    for a, b in zip(pts, pts[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bm.faces.new(pts[0][::-1]).material_index = mat
    bm.faces.new(pts[-1]).material_index = mat


def sphere_r(z):
    """The cradle's ball's radius at height z (world)."""
    dz = z - ORB_Z
    return math.sqrt(max(0.0, RC * RC - dz * dz))


def warp(frame):
    """n -> n0: the base orb's normal (CXp, CYp, R_PX; where the fire fields live) over the same
    sprite point that frame `frame`'s orb has normal n over, so the fire bands keep their sprite
    pixels while the ball shrinks and shifts (the sprite's frames are one drawing, recoloured). Below
    the equator the height is carried on continuously (the identity on frame 171)."""
    cx, cy, r_px = ORB_FRAMES[frame][:3]
    KNEE = 1.0 if frame == 171 else 0.8

    def f(n):
        x0 = (cx + r_px * n.x - CXp) / R_PX
        y0 = (CYp - cy + r_px * n.y) / R_PX
        h = math.hypot(x0, y0)
        if h > KNEE:  # past the base ball's rim (the shifted ball's far side): eased in, never flat
            h0 = KNEE + (1 - KNEE) * math.tanh((h - KNEE) / (1 - KNEE))
            x0, y0 = x0 * h0 / h, y0 * h0 / h
        else:
            h0 = h
        z0 = math.sqrt(max(0.0, 1 - h0 * h0))
        if n.z < 0:
            z0 = n.z + z0 - math.sqrt(max(0.0, 1 - n.x * n.x - n.y * n.y))
        return Vector((x0, y0, z0)).normalized()
    return f


def frame_orb(o, frame):
    """Place orb `o` (built at C, radius R) on sprite frame `frame`'s circle and show it on that
    frame only."""
    cx, cy, r_px, lick, ang = ORB_FRAMES[frame]
    me = o.data
    th0 = math.radians(ang)
    # It rests in the cradle: its surface passes through the collar's seat (the lip's inner edge), so
    # a smaller ball sits lower (171 rides about 1.6 px higher than the cradle's own ball).
    z_seat = ORB_Z - 0.47 * RC
    r_seat = sphere_r(z_seat)
    centre = Vector(((cx - 6) * P, (7 - cy) * P, z_seat + math.sqrt(max(0.0, (r_px * P) ** 2 - r_seat ** 2))))
    for v in me.vertices:
        n = (Vector(v.co) - C) / R
        nxy = math.hypot(n.x, n.y)
        push = lick * max(0.0, math.cos(math.atan2(n.y, n.x) - th0)) ** 4 * nxy if lick else 0.0
        v.co = centre + n * ((r_px + push) * P)
    me.update()
    common.frame_part(o, [frame])
    return o


def build(sprite):
    coll = common.reset_collection(NAME)
    anchors = anchor_tables(sprite)

    # --- The orb, one per frame: a sphere cut along every band edge, each face given its band's
    # material (one material per band table, shared by the frames).
    mats = {}
    orbs = {}
    for fr in sprite["frames"]:
        frame = fr["index"]
        wf = warp(frame)
        fcw = lambda n, wf=wf: fc(wf(n))  # noqa: E731
        fkw = lambda n, wf=wf: fk(wf(n))  # noqa: E731
        cx, cy, r_px = ORB_FRAMES[frame][:3]
        core = Vector(((CORE_AT[0] - cx) / r_px, -(CORE_AT[1] - cy) / r_px, 0.0))
        core.z = math.sqrt(max(0.0, 1 - core.x ** 2 - core.y ** 2))  # this frame's normal over the core's axis
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=R)
        # Poles on the core's axis: the core's band edges then run along the rings (clean, few cuts).
        bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector((0, 0, 0)),
                         matrix=Vector((0, 0, 1)).rotation_difference(core).to_matrix())
        bmesh.ops.triangulate(bm, faces=bm.faces)
        # Twice as fine round the core (its two innermost edges lie inside the first ring of the pole).
        edges = [e for e in bm.edges if all(v.co.normalized().dot(core) > 0.935 for v in e.verts)]
        res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
        for v in res["geom_inner"]:
            if isinstance(v, bmesh.types.BMVert):
                v.co = v.co.normalized() * R
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        O = Vector((0, 0, 0))
        tags = {}
        for j, t in enumerate(CORE_T):
            for dt in ((-W, W) if j in CORE_MIX else (0.0,)):
                iso_cut(bm, fcw, t + dt, O, R, tags, "c")
        for j, t in enumerate(TONGUE_T):
            for dt in ((-W, W) if j in TONGUE_MIX else (0.0,)):
                iso_cut(bm, fkw, t + dt, O, R, tags, "k")
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        # Each face by its corners' mean field values: corners on a cut sit on its level, the others on
        # one side, so the mean is on the face's side even where the curved level set leaves the
        # straight cut (a centroid test there gives sawtooth edges).
        fcv = {v: tags.get(v, {}).get("c", fcw(v.co.normalized())) for v in bm.verts}
        fkv = {v: tags.get(v, {}).get("k", fkw(v.co.normalized())) for v in bm.verts}

        def face_value(vs, val, f):
            xs = [val[v] for v in vs]
            if max(xs) - min(xs) < 1e-9:  # all corners on one cut (a fan along a curved edge): its middle decides
                return f(sum((v.co for v in vs), Vector()).normalized())
            return sum(xs) / len(xs)

        tabs = {}
        for face in bm.faces:
            vs = face.verts
            tab = fine_table(face_value(vs, fcv, fcw), face_value(vs, fkv, fkw), anchors)
            face.material_index = tabs.setdefault(tab, len(tabs))
        bmesh.ops.translate(bm, verts=bm.verts, vec=C)
        # Glow: the hotter the band (on the white-hot frame), the more it is pure light (D126).
        fire = []
        for tab, i in sorted(tabs.items(), key=lambda kv: kv[1]):
            if tab not in mats:
                glow = round(0.65 + 0.35 * min(1.0, max(0.0, (tab[0] - 116) / 10)), 2)
                mats[tab] = fire_material(sprite, tab, glow, "fire" + "-".join(map(str, tab)))
            fire.append(mats[tab])
        orbs[frame] = frame_orb(common.mesh_object(f"{NAME}-orb-{frame}", bm, fire, coll, smooth=True), frame)

    # --- The cradle: dark metal, all inside the orb's disc seen from above.
    HUB, COLLAR, CLAW = 0, 1, 2
    vent_mat = fire_material(sprite, anchors[(0, 3)], 1.0, "vent")
    metal = [common.palette_material(sprite, 113, f"{NAME}-hub", metallic=0.35, roughness=0.45),
             common.palette_material(sprite, 114, f"{NAME}-collar", metallic=0.35, roughness=0.4),
             common.palette_material(sprite, 115, f"{NAME}-claw", metallic=0.35, roughness=0.4),
             vent_mat]
    VENT = 3
    bm = bmesh.new()
    # Collar: a ring round the ball's lower hemisphere, its outer face standing proud of the ball.
    zc0, zc1 = ORB_Z - 0.68 * RC, ORB_Z - 0.47 * RC
    r_in = sphere_r(zc1) - 0.35 * P
    r_out = 0.955 * RC
    revolve(bm, chamfer_ring(r_in, r_out, zc0, zc1, 0.28 * P), 24, COLLAR, centre=CC)
    # A thin raised band (machined lip) on the collar's top, and its groove below: panel lines.
    lip_in, lip_out = sphere_r(zc1 + 0.25 * P) - 0.2 * P, sphere_r(zc1) + 0.25 * P
    revolve(bm, [(lip_in, zc1 - 0.05 * P), (lip_out, zc1 - 0.05 * P), (lip_out, zc1 + 0.12 * P),
                 (lip_out - 0.12 * P, zc1 + 0.25 * P), (lip_in, zc1 + 0.25 * P), (lip_in, zc1 - 0.05 * P)], 24, CLAW, centre=CC)
    # Four clamp claws at the diagonals: thin plates hugging the ball from the collar up to just
    # below the widest point (z = -0.33 RC), each curved round the ball in three segments.
    for i in range(4):
        a = math.radians(45 + 90 * i)
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        zs = [zc1 - 0.1 * P, ORB_Z - 0.42 * RC, ORB_Z - 0.36 * RC, ORB_Z - 0.31 * RC]
        hw = [0.8 * P, 0.75 * P, 0.65 * P, 0.5 * P]
        th = 0.32 * P
        loops = []
        for z, w in zip(zs, hw):
            rs = sphere_r(z) - 0.05 * P
            base = Vector((CC.x, CC.y, z)) + d * rs
            nrm = (base - CC).normalized()
            loops.append([base - t * w, base + t * w, base + t * w + nrm * th, base - t * w + nrm * th])
        vs = [[bm.verts.new(p) for p in lp] for lp in loops]
        for la, lb in zip(vs, vs[1:]):
            for k in range(4):
                kk = (k + 1) % 4
                bm.faces.new((la[k], la[kk], lb[kk], lb[k])).material_index = CLAW
        bm.faces.new(vs[0][::-1]).material_index = CLAW
        bm.faces.new(vs[-1]).material_index = CLAW
        # A bolt head on the claw's foot.
        box(bm, Vector((CC.x, CC.y, zc0 + 0.45 * (zc1 - zc0))) + d * (r_out + 0.1 * P), t, Vector((0, 0, 1)), d,
            0.28 * P, 0.28 * P, 0.14 * P, CLAW, ch=0.06 * P)
    # Four vent windows between the claws, in the collar's outer face, glowing with the core.
    for i in range(4):
        a = math.radians(90 * i)
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        box(bm, Vector((CC.x, CC.y, (zc0 + zc1) / 2)) + d * (r_out - 0.05 * P), t, Vector((0, 0, 1)), d,
            0.75 * P, 0.22 * P, 0.1 * P, VENT)
    # Hub: a chamfered bowl under the collar tapering to a mounting stub, its profile pchip-smooth.
    import usp_talon as T
    zs = [zc0 + 0.05 * P, zc0 - 0.6 * P, zc0 - 1.4 * P, zc0 - 2.2 * P, zc0 - 2.6 * P]
    rs = [r_out - 0.35 * P, 3.55 * P, 2.6 * P, 1.65 * P, 1.45 * P]
    f = T.pchip(zs[::-1], rs[::-1])
    prof = [(f(z), z) for z in [zs[0] - (zs[0] - zs[-1]) * k / 5 for k in range(6)]]
    zb = zs[-1]
    prof += [(1.45 * P, zb - 0.3 * P), (1.15 * P, zb - 0.35 * P), (1.15 * P, zb - 0.8 * P),  # stub neck
             (1.0 * P, zb - 1.0 * P), (0.55 * P, zb - 1.0 * P), (0.55 * P, zb - 0.85 * P), (0.0, zb - 0.85 * P)]  # bore
    revolve(bm, prof[::-1], 16, HUB, centre=CC, phase=0.5)
    # Eight radial cooling fins round the hub, under the collar.
    for i in range(8):
        a = math.radians(22.5 + 45 * i)
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        z_top, z_bot = zc0 - 0.1 * P, zc0 - 1.9 * P
        r0, r1t, r1b = 1.4 * P, r_out - 0.6 * P, 2.4 * P
        hw = 0.13 * P
        quad = [(r0, z_bot), (r1b, z_bot), (r1t, z_top), (r0, z_top)]
        lo = [bm.verts.new(Vector((CC.x, CC.y, z)) + d * r - t * hw) for r, z in quad]
        hi = [bm.verts.new(Vector((CC.x, CC.y, z)) + d * r + t * hw) for r, z in quad]
        for k in range(4):
            kk = (k + 1) % 4
            bm.faces.new((lo[k], lo[kk], hi[kk], hi[k])).material_index = HUB
        bm.faces.new(lo[::-1]).material_index = HUB
        bm.faces.new(hi).material_index = HUB
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    cradle = common.mesh_object(f"{NAME}-cradle", bm, metal, coll, smooth=False)
    # Autosmooth-like: keep hard edges (flat) — the cradle is machined.

    # --- Outline shells (D51), one per frame from a joined copy of that frame's orb and the cradle.
    shells = []
    for frame, orb in orbs.items():
        tmp = [o.copy() for o in (orb, cradle)]
        for o in tmp:
            o.data = o.data.copy()
            coll.objects.link(o)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in tmp:
            o.select_set(True)
        bpy.context.view_layer.objects.active = tmp[0]
        bpy.ops.object.join()
        joined = tmp[0]
        for k in [k for k in joined.keys() if k == "tyrian_frames"]:
            del joined[k]
        shell = common.outline_shell(joined, coll, voxel=0.012, faces=350, inside=0.004)
        bpy.data.objects.remove(joined, do_unlink=True)
        shell.name = f"{NAME}-outline-{frame}"
        common.frame_part(shell, [frame])
        shells.append(shell)
    return [*orbs.values(), cradle, *shells], anchors


# ------------------------------------------------------------------------------------------------
# Review renders (scratch only).

def set_frame(objects, frame, shells=False):
    """Show the parts of sprite frame `frame` (frame_part; outline shells only with `shells`) and
    recolour every pal_ material for it, the game's way (D126): lit colour × (1 - glow), emission =
    palette colour × glow."""
    for o in objects:
        if "tyrian_frames" in o:
            o.hide_render = int(frame) not in list(o["tyrian_frames"]) or (bool(o.get("tyrian_outline")) and not shells)
    for o in objects:
        if o.type != "MESH":
            continue
        for m in o.data.materials:
            if not m or not m.name.startswith("pal_"):
                continue
            idx = int(m.get("tyrian_frame_pal", {}).get(str(frame), int(m.name.split("_")[1])))
            rgb = common.srgb(*SPRITE["colors"][str(idx)])
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            g = m.get("_glow")
            if g is None:
                g = float(bsdf.inputs["Emission Strength"].default_value)
                m["_glow"] = g
            bsdf.inputs["Base Color"].default_value = (*[c * max(0.0, 1 - g) for c in rgb], 1)
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
            bsdf.inputs["Emission Strength"].default_value = g
            m.diffuse_color = (*rgb, 1)


def render_views(objects, out):
    import numpy as np
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    model = [o for o in objects if not o.get("tyrian_outline")]
    shell = [o for o in objects if o.get("tyrian_outline")]
    for o in scene.objects:
        o.hide_render = o not in objects
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.25, 0.27, 0.3, 1)
    bg.inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(30))
    scene.collection.objects.link(sun)

    def cam(name, loc, look, ortho=None):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = 60
        c = bpy.data.objects.new(name, data)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return c

    tgt = (OX, OY, ORB_Z + 0.2 * P)
    D = 2.4
    views = {
        "top": cam("top", (0, 0, 5), (0, 0, 0), ortho=14 * P),
        "side": cam("side", (D, OY, tgt[2]), tgt, ortho=16 * P),
        "front": cam("front", (OX, -D, tgt[2]), tgt, ortho=16 * P),
        "rear": cam("rear", (OX, D, tgt[2]), tgt, ortho=16 * P),
        "q34": cam("q34", (D * 0.55, -D * 0.6, D * 0.55), tgt),
        "game": cam("game", (0, -D * 0.5, D * 0.86), tgt),
        "under": cam("under", (D * 0.3, -D * 0.4, -D * 0.6), tgt),
    }
    views["top"].rotation_euler = (0, 0, 0)
    for v in ("side", "front", "rear", "q34", "game", "under"):
        if views[v].data.type != "ORTHO":
            views[v].data.lens = 70
    scene.render.resolution_x = scene.render.resolution_y = 320
    scene.render.film_transparent = True
    for o in shell:
        o.hide_render = True
    for f in SPRITE["frames"]:
        set_frame(objects, f["index"])
        for v in (["top", "game", "q34"] if f["index"] != 171 else list(views)):
            scene.camera = views[v]
            scene.render.filepath = str(out / f"{v}_{f['index']}.png")
            bpy.ops.render.render(write_still=True)
    # Flat top view on the sprite grid for the IoU (k = 24 px per sprite px, alpha), and the flat
    # palette colour per sprite pixel (emission only) for the colour check.
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.view_settings.view_transform = "Standard"
    top = views["top"]
    top.data.ortho_scale = 14 * P
    top.location = (0, 0, 5)
    scene.render.resolution_x, scene.render.resolution_y = 12 * 24, 14 * 24
    for f in SPRITE["frames"]:
        set_frame(objects, f["index"])
        scene.camera = top
        scene.render.filepath = str(out / f"flat_{f['index']}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    SPRITE = common.load_sprite(WT, NAME)
    objects, table = build(SPRITE)
    for b, t in table.items():
        print("anchor", b, t)
    common.export_sprite_model(WT, objects, MODEL, SPRITE["sprites"])
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects if o.type == "MESH")
    print("triangles", tris,
          {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects})
    if "--render" in sys.argv:
        render_views(objects, Path(sys.argv[sys.argv.index("--render") + 1]))
