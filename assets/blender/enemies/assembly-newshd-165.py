"""Giant stone face (newshd 155/165 + newshp 123/127, one 48x56 carving), design B.

A bald grey stone head lying face up, crown to screen top. Design B leads with the silhouette and
with what reads from the small tilted game camera: one sculpted surface built on the sprite's
inner-mask outline (a pchip profile down the face times a superellipse section across it), then
carved like a stone mask with hard, chamfered pads and cut grooves:
  a raised forehead plate with a seam round it, a brow bar overhanging two deep eye sockets that
  hold closed lens-dome lids with a cut lid line, a triangular-section nose ridge from the bridge
  to a tip with flared wings, cheekbone pads, the groove under the nose, an upper lip bar, the
  mouth slit, a lower lip bar and a chin pad.
Fix round 1: the forehead plate and its pal_9 paint are gone (the sprite's bright ring is sheen on
the dome), the nose ridge rises to a rounded tip ~2.5 px over the cheeks, the brow blends into the
skull, the lips are one pad with a mouth line, and the sockets/lids are smooth (protected from the
decimation, sharp angle 55 deg).
Fix round 2: the outline shell keeps only the silhouette ring (its top faces over the carved face
are removed: the smoothed hull bridged the carving and drew black cracks and specks there); the
cheekbones are broad elongated swells angled down and out from under the outer sockets with no rim;
the forehead swell is feathered to zero slope; each socket is a shallow rim groove round a full
closed eyeball dome; the decimation keeps more of the budget (0.44) so the cheek and jaw slopes stay
smooth.
The side profile (brow, nose, lips, chin) is pushed enough that the head reads as a face from the
side, front and rear too. Underside: flat base at z 0 (a ground structure, closed shape only).
Built whole in assembly coordinates, then cut into the four pieces (common.split_assembly), with an
outline shell (D51) cut open per piece. Exports ONLY this design's scratch .glb (and the pieces
under pieces/ for an in-game check through a scratch dev-server middleware).

Coordinates: sprite edge px (x right, y down) of the 48x56 assembly; model X = (x - 24) / 12,
Y = (28 - y) / 12, Z = z / 12.
Run: blender -b --factory-startup -P assembly-newshd-165_B.py
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)
NAME = "assembly-newshd-165"
TAG = "nshd165"
W, H = 48, 56
# piece: (x0, y0) of its 24x28 box in the assembly
PIECES = {"newshd-155": (0, 0), "newshp-123": (24, 0), "newshd-165": (0, 28), "newshp-127": (24, 28)}

# --------------------------------------------------------------------------------------------
# Silhouette: the sprite's inner mask (D74): half width per row centre about the axis x 24.5, the
# pixel staircase smoothed (three [1 2 1] passes) and the crown and chin rounded off. Coverage at
# sprite resolution reproduces the inner mask exactly (IoU 1.0 before meshing).
# --------------------------------------------------------------------------------------------
HALF = [(4.0, 3.0), (4.5, 4.5), (5.5, 6.047), (6.5, 7.375), (7.5, 8.484), (8.5, 9.5), (9.5, 10.484),
        (10.5, 11.391), (11.5, 12.141), (12.5, 12.719), (13.5, 13.141), (14.5, 13.391), (15.5, 13.484),
        (16.5, 13.5), (26.5, 13.5), (27.5, 13.484), (28.5, 13.391), (29.5, 13.156), (30.5, 12.828),
        (31.5, 12.5), (32.5, 12.172), (33.5, 11.828), (34.5, 11.5), (35.5, 11.172), (36.5, 10.844),
        (37.5, 10.594), (38.5, 10.406), (39.5, 10.156), (40.5, 9.828), (41.5, 9.5), (42.5, 9.156),
        (43.5, 8.719), (44.5, 8.141), (45.5, 7.391), (46.5, 6.484), (47.5, 5.5), (48.5, 4.5),
        (49.5, 3.5), (50.5, 2.5), (51.0, 1.6)]
MID = 24.5
R0, R1 = HALF[0][0], HALF[-1][0]
_half = T.pchip([s[0] for s in HALF], [s[1] for s in HALF])


def _left(r):
    return MID - _half(r)


def _right(r):
    return MID + _half(r)


# Height of the head down its middle (px, without carving): crown, forehead, brow, face, chin.
PROFILE = T.pchip([4.0, 4.6, 6.5, 9.5, 13.5, 18.0, 21.5, 25.0, 30.0, 35.0, 40.0, 44.0, 46.0, 47.5, 49.0, 50.3, 51.0],
                  [0.0, 2.5, 4.9, 6.8, 8.0, 8.6, 8.8, 8.2, 7.9, 7.6, 7.2, 6.6, 5.6, 4.4, 2.8, 1.3, 0.0])
SECTION_P = 2.25   # (kept for reference; the section is now the rolled falloff below)
# Across the head: a rolled section, 1 on the middle line down to 0 at the outline with a finite
# slope (no vertical skirt): the temples, cheeks and crown curve down into the outline.
# Fix 1: defined symmetric over -1..1 so its slope is 0 on the middle line (no crease down the
# crown, which the plain forehead now shows).
_RU = [0.0, 0.35, 0.6, 0.78, 0.9, 0.97, 1.0]
_RV = [1.0, 0.97, 0.86, 0.68, 0.43, 0.17, 0.0]
ROLL = T.pchip([-u for u in _RU[:0:-1]] + _RU, _RV[:0:-1] + _RV)
AXIS = 24.75   # face axis (edge column): the nose ridge sits at 25, the head middle at 24.5


def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def ramp(t, f=0.18):
    """0 -> 1 linear ramp with small rounded ends (chamfer with a fillet at top and foot)."""
    if t <= -f:
        return 0.0
    if t >= 1 + f:
        return 1.0
    if t < f:
        return (t + f) ** 2 / (4 * f)
    if t > 1 - f:
        return 1 - (1 + f - t) ** 2 / (4 * f)
    return t


# --- 2D signed distances (px; negative inside) ---
def sd_rrect(x, y, x0, x1, y0, y1, r):
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = abs(x - cx) - hx, abs(y - cy) - hy
    out = math.hypot(max(qx, 0), max(qy, 0))
    return out + min(max(qx, qy), 0) - r


def sd_cap(x, y, ax, ay, bx, by, r):
    px, py, vx, vy = x - ax, y - ay, bx - ax, by - ay
    t = clamp((px * vx + py * vy) / (vx * vx + vy * vy))
    return math.hypot(px - vx * t, py - vy * t) - r


def sd_ell(x, y, cx, cy, rx, ry):
    k = math.hypot((x - cx) / rx, (y - cy) / ry)
    return (k - 1) * min(rx, ry) if k > 1 else (k - 1) * min(rx, ry)


def dome(d, h, r):
    """A rounded bar or boss: height h at its spine, a quarter-round falling to 0 at its edge
    (d the signed distance, r the depth from the edge to the spine)."""
    t = clamp(-d / r)
    return h * math.sqrt(1 - (1 - t) ** 2)


def boss(d, h, r):
    """A soft boss (cheekbone, chin): parabolic, meeting the face at a finite slope."""
    t = clamp(-d / r)
    return h * (1 - (1 - t) ** 2)


def soft(k, k0=0.0, k1=1.0):
    """1 inside k0, 0 beyond k1, smoothstep between: zero slope at both ends (no rim edge)."""
    t = clamp((k - k0) / (k1 - k0))
    return 1.0 - t * t * (3 - 2 * t)


def swell(x, y, cx, cy, ax, ay, ang, h):
    """Fix 2: an elongated cheekbone or brow swell that fades into the surface with no edge: a
    smoothstep of the rotated elliptic radius (major semi-axis ax along angle ang, minor ay)."""
    c, s_ = math.cos(ang), math.sin(ang)
    dx, dy = x - cx, y - cy
    u, v = (dx * c + dy * s_) / ax, (-dx * s_ + dy * c) / ay
    return h * soft(math.hypot(u, v), 0.0, 1.0) ** 1.3


def pad(d, h, ch):
    """A flat-topped pad (h > 0) or pocket (h < 0) with a chamfer `ch` wide inside the shape."""
    return h * ramp(-d / ch)


# --- the carving ------------------------------------------------------------------------------
PLATE = (16.9, 31.4, 10.4, 21.0, 3.6)
SOCKETS = [(18.9, 25.5, 4.6, 2.75), (30.3, 25.6, 4.5, 2.8)]
LIDS = [(18.9, 25.9, 3.4, 1.75), (30.2, 26.0, 3.4, 1.75)]
NOSE_X = 25.0
# Fix 1: the ridge rises toward the tip so the profile carries a nose (tip ~2.5 px over the cheeks,
# ~1.5 px over the forehead), then drops steeply under the tip into the groove above the lip.
NOSE_H = T.pchip([22.2, 23.5, 27.0, 30.0, 32.4, 33.5, 34.5, 35.3], [0.0, 0.55, 1.35, 2.3, 3.2, 3.15, 1.6, 0.0])
NOSE_TIP = (25.0, 33.1, 1.5, 1.4, 2.5)   # bulb at the tip: centre, radii, height
NOSE_W = T.pchip([22.2, 25.0, 29.0, 32.0, 33.6, 35.1], [1.2, 1.5, 2.0, 2.6, 2.9, 3.0])


def carve(x, y):
    """Relief over the base head (px) and the region name at (x, y)."""
    pos = []
    region = None
    # forehead: a soft swell of the skull dome (no plate, no paint: the sprite's bright ring is
    # sheen on the dome, rule 2)
    # fix 2: feathered (smoothstep to zero slope well past the old ellipse), so no oval rim
    k = math.hypot((x - 24.4) / 9.5, (y - 16.2) / 7.2)
    add = 0.5 * soft(k, 0.0, 1.0)
    seam = 0.0
    # brow ridge: a long chamfered rise out of the forehead (no step on the skull line), a
    # shorter fall into the sockets below
    db = sd_cap(x, y, 17.4, 21.6, 31.6, 21.6, 0.0)
    fall = 3.2 if y < 21.6 else 1.3
    pos.append(0.6 * (1.0 - ramp(db / fall, 0.25)))
    # cheekbones (fix 2): broad elongated swells from under the outer socket, angled down and out
    # toward the jaw, fading into cheek and jaw with no rim (the sprite's cheek highlights are the
    # lit faces of these, rule 2); added, not max-ed, so no crease where they meet other forms
    add += swell(x, y, 16.5, 30.6, 5.0, 2.6, math.radians(115), 1.35)
    add += swell(x, y, 32.4, 30.7, 4.9, 2.6, math.radians(65), 1.35)
    # nose ridge: triangular section with a narrow rounded crest
    nose = 0.0
    if 22.2 < y < 35.1:
        w = NOSE_W(y)
        u = abs(x - NOSE_X) / w
        # ridge section: rounded crest, flanks easing into the cheeks with no crease at the foot
        nose = NOSE_H(y) * (1.0 - u ** 1.7) ** 1.6 if u < 1.0 else 0.0
    nose = max(nose, boss(sd_ell(x, y, 25.0, 33.2, 2.3, 1.7), 3.25, 1.7))   # rounded tip
    pos.append(nose)
    # nostril wings: low rounded pads flaring from the tip
    for cx in (23.1, 26.9):
        pos.append(pad(sd_ell(x, y, cx, 34.0, 1.6, 1.2), 0.9, 0.7))
    # lips and chin
    # lips: one carved pad (upper lip, mouth line, lower lip), its lower edge running into the chin
    dl = sd_ell(x, y, 24.4, 39.8, 5.9, 3.4)
    lip = pad(dl, 0.95, 1.6) - 0.25 * clamp((y - 37.0) / 6.0)   # leans back a little to the chin
    pos.append(lip)
    pos.append(pad(sd_ell(x, y, 24.0, 45.0, 5.0, 3.6), 0.7, 1.5))
    z = max(pos) + add
    # cuts
    z += seam
    sock = 0.0
    for (cx, cy, rx, ry), (lx, ly, lrx, lry) in zip(SOCKETS, LIDS):
        d = sd_ell(x, y, cx, cy, rx, ry)
        if d < 0.6:
            # fix 2: a shallow socket rim round a full closed eyeball + lid mound that fills most
            # of its depth (oblique views read as a closed stone eye, not a hole with a fin)
            s = pad(d, -0.95, 0.55)
            k = math.hypot((x - cx) / (rx - 0.5), (y - (cy + 0.15)) / (ry - 0.35))
            s += 0.85 * soft(k, 0.15, 1.0)   # eyeball dome easing into the rim groove
            sock = min(sock, s)
    z += sock
    lid_l = sd_cap(x, y, 15.9, 24.5, 21.8, 24.6, 0.42)
    lid_r = sd_cap(x, y, 27.3, 24.7, 33.2, 24.8, 0.42)
    z += pad(min(lid_l, lid_r), -0.45, 0.22)
    dsub = sd_cap(x, y, 22.8, 35.7, 27.2, 35.7, 0.5)   # fix 1: a short soft dip under the tip
    z += pad(dsub, -0.25, 0.6)
    dmouth = sd_cap(x, y, 19.6, 39.9, 29.2, 39.9, 0.32)
    z += pad(dmouth, -0.5, 0.4)
    dnl = min(sd_cap(x, y, 21.3, 34.9, 18.9, 39.4, 0.45), sd_cap(x, y, 28.3, 34.9, 30.4, 39.4, 0.45))
    z += pad(dnl, -0.22, 0.7)   # fix 1: soft folds, not cut lines framing the mouth

    # regions (palette by the blueprint's per-part medians)
    if min(lid_l, lid_r) < 0:
        region = "lidline"
    elif any(math.hypot((x - lx) / lrx, (y - ly) / lry) < 1.0 for lx, ly, lrx, lry in LIDS):
        region = "eyelid"
    elif any(sd_ell(x, y, *s) < 0.1 for s in SOCKETS):
        region = "socket"
    elif db < 0.1 or nose > 0.15 or dsub < 0.1 or dmouth < 0.1 or dnl < 0.05 or z > 0.25:
        region = "pad"
    elif y < 22:
        region = "cranium"
    elif y < 35.5:
        region = "midface"
    else:
        region = "jaw"
    return z, region


# The head itself is one part: its trimmed median is 5 (lit left half 6, shaded right half 4: the
# cranium 5 / midface 4 / jaw 4 split of the blueprint is the sprite's lighting, and painted as
# bands it drew hard colour steps across the temples). Carved pads stay stone 5 and read by form.
def colour_edges(x, y):
    """The colour boundaries as level sets f(x, y) = 0 (lid lines, lids, sockets, seam, plate)."""
    out = [min(sd_cap(x, y, 15.9, 24.5, 21.8, 24.6, 0.42), sd_cap(x, y, 27.3, 24.7, 33.2, 24.8, 0.42))]
    # (fix 2: the lid ellipse is no colour edge any more: lid and socket are both pal_3, and
    # snapping the grid onto it across the eyeball's slope scattered its normals)
    out += [sd_ell(x, y, *sk) - 0.1 for sk in SOCKETS]
    return out


def snap(x, y, reach):
    """Move a grid point onto the nearest colour boundary within `reach` px, so the palette edges
    run along mesh edges as clean curves instead of a face staircase."""
    f = colour_edges(x, y)
    i = min(range(len(f)), key=lambda q: abs(f[q]))
    if abs(f[i]) > reach * 1.5:
        return x, y
    for _ in range(3):
        v = colour_edges(x, y)[i]
        e = 1e-3
        gx = (colour_edges(x + e, y)[i] - v) / e
        gy = (colour_edges(x, y + e)[i] - v) / e
        g2 = gx * gx + gy * gy
        if g2 < 1e-6:
            return x, y
        x, y = x - v * gx / g2, y - v * gy / g2
    return x, y


DECIMATE = 0.44   # fix 2: was 0.36; the spare budget keeps the cheek and jaw slopes smooth
# Fix 1: 55 deg (was 38): the carved stone is soft-filleted, and at 38 the collapsed triangles of the
# socket walls split their normals into streaks.
SHARP = 55.0
# The plate's bevel keeps the plate's colour: the sprite's 6/7 band above it is the crown's shading.
REGION_PAL = {"lidline": 2, "eyelid": 3, "socket": 3, "seam": 5, "plate": 5, "pad": 5, "cranium": 5,
              "midface": 5, "jaw": 5, "base": 4}


def base_z(x, y, hw, mid):
    u = clamp(abs(x - mid) / hw)
    return PROFILE(y) * ROLL(u if x >= mid else -u), u


# --------------------------------------------------------------------------------------------
def build(sprite, coll):
    mats, slot = [], {}
    for name, idx in REGION_PAL.items():
        if idx not in slot:
            slot[idx] = len(mats)
            mats.append(common.palette_material(sprite, idx, TAG, metallic=0.0, roughness=0.82))
    bm = bmesh.new()
    # rows: dense through the face, sampled so the ends close on the crown and chin points
    K = 200
    rows = [R0 + (R1 - R0) * (0.5 - 0.5 * math.cos(math.pi * k / K)) * 0.35 + (R1 - R0) * (k / K) * 0.65
            for k in range(K + 1)]
    N = 132
    grid = []
    for r in rows:
        left, right = _left(r), _right(r)
        mid, hw = (left + right) / 2, max((right - left) / 2, 0.05)
        row = []
        for j in range(N + 1):
            s = -1 + 2 * j / N
            u = 0.55 * s + 0.45 * math.sin(math.pi * s / 2)
            x, y = mid + u * hw, r
            rim = j in (0, N) or r in (R0, R1)
            if not rim and 9.5 < r < 29.5 and abs(x - MID) < 11:
                x, y = snap(x, y, 0.12)
            zb, uu = base_z(x, y, _half(y), MID)
            fade = clamp((1 - uu) / 0.4) * clamp((y - 6.0) / 3.0) * clamp((50.0 - y) / 2.5)
            c, region = carve(x, y)
            z = 0.0 if rim else max(zb + c * fade, 0.15)
            row.append((x, y, z))
        grid.append(row)
    verts = [[bm.verts.new(((x - 24) / 12, (28 - y) / 12, z / 12)) for x, y, z in row] for row in grid]
    for k in range(K):
        for j in range(N):
            f = bm.faces.new((verts[k][j], verts[k][j + 1], verts[k + 1][j + 1], verts[k + 1][j]))
            q = (grid[k][j], grid[k][j + 1], grid[k + 1][j + 1], grid[k + 1][j])
            cx, cy = sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4
            f.material_index = slot[REGION_PAL[carve(cx, cy)[1]]]
    # closing base at z 0 (ground structure: the underside is a plain flat floor)
    rim = ([verts[0][j] for j in range(N + 1)] + [verts[k][N] for k in range(1, K + 1)]
           + [verts[K][j] for j in range(N - 1, -1, -1)] + [verts[k][0] for k in range(K - 1, 0, -1)])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    rim = [v for v in rim if v.is_valid]
    seen, ring = set(), []
    for v in rim:
        if v not in seen:
            seen.add(v)
            ring.append(v)
    try:
        f = bm.faces.new(ring)
        f.material_index = slot[REGION_PAL["base"]]
    except ValueError:
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # Dense sampling keeps the carved edges crisp; a quadric collapse then brings it to budget
    # (the flat base head goes coarse, the creases keep their vertices). Fix 1: the carved face
    # (sockets, lids, nose, lips) is weighted 0 in the "plain" group so the collapse spends its
    # cuts on the plain skull (a collapse cost grows as the edge's weights fall below 1), which
    # removed the streaked socket walls and the faceted lids.
    vg = obj.vertex_groups.new(name="plain")
    for v in me.vertices:
        x, y = v.co.x * 12 + 24, 28 - v.co.y * 12
        c = abs(carve(x, y)[0]) if v.co.z > 0.02 else 0.0
        vg.add([v.index], clamp(1.0 - c / 0.35), "REPLACE")
    near = [v.index for v in me.vertices if abs(v.co.x * 12 + 24 - 30.3) < 4 and abs(28 - v.co.y * 12 - 25.6) < 3]
    print(f"socket verts before {len(near)}")
    dec = obj.modifiers.new("decimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = DECIMATE
    dec.use_collapse_triangulate = True
    dec.vertex_group = "plain"
    dec.vertex_group_factor = 6.0
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=dec.name)
    near = [v for v in me.vertices if abs(v.co.x * 12 + 24 - 30.3) < 4 and abs(28 - v.co.y * 12 - 25.6) < 3]
    print(f"socket verts after {len(near)} of {len(me.vertices)}")
    obj.vertex_groups.clear()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(SHARP))
    return obj


def in_carved_face(px, py):
    """The carved face (brow, sockets, nose, cheeks, mouth, chin), well inside the silhouette."""
    return (math.hypot((px - 24.6) / 11.0, (py - 33.5) / 15.5) < 1.0
            or sd_rrect(px, py, 13.6, 35.6, 19.4, 29.6, 2.5) < 0.0)


def mask_shell(shell):
    """Fix 2: the outline shell only draws the silhouette ring. The smoothed voxel hull bridged the
    concave carving (nose flanks, sockets, mouth, chin) and stood above it there, so its pushed-out
    faces drew as black cracks and specks across the face. Its top-facing faces over the carved
    face are removed (an inverted hull needs no top there: seen from above the face is never a
    silhouette); the crown, the flanks, the ring round the outline and the floor stay, so the ink
    contour round the head is unchanged. (Lowering the shell under the carving instead left
    folds where the drop faded out, which drew their own specks.)"""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.z > 0.3 and c.z > 0.02 and in_carved_face(c.x * 12 + 24, 28 - c.y * 12):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    print(f"shell: removed {len(kill)} top faces over the carved face")


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: no seams outlined)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def main():
    sprite = common.load_sprite(WT, "newshd-155")
    for n in PIECES:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    sprite["name"] = NAME
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll, voxel=0.014, faces=5000, smooth=6, inside=0.01)
    mask_shell(shell)
    layout = [(n, x0 + 12 - W / 2, y0 + 14 - H / 2) for n, (x0, y0) in PIECES.items()]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    tris = 0
    whole = []
    for name, cx, cy in layout:
        p, s = pieces[name], shells[name]
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(SHARP))
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        objs = [p] + ([s] if s.data.polygons else [])
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, objs, f"enemies/{name}", data["sprites"])
        for o in objs:
            o.location = (cx / 12, -cy / 12, 0)
        whole += objs
        p.data.calc_loop_triangles()
        tris += len(p.data.loop_triangles)
        print(f"piece {name}: {len(p.data.loop_triangles)} tris, shell {len(s.data.polygons)} faces")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--whole" in argv:   # review export of the assembled head (not a game asset)
        common.export_glb(whole, Path(argv[argv.index("--whole") + 1]))
    print(f"built {NAME}: {tris} triangles")


if __name__ == "__main__":
    main()
