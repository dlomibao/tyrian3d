"""Mint-O-Ship (sidekick 16, tyrian.shp#8 frames 112, 131 and 150): a 3D version of its sprite.

A small green drone pod that flies beside the player's ship, nose up the screen. The sprite is an
egg 10 px wide and 13 px long (columns 2-11, rows 0-12 of its 12x14 block, centred on column
edge 7), blunt at the front and tapering more to the back, shaded round: a highlight streak at its
upper left (sheen on the polished shell, not geometry), shade to the lower right. In its middle
(columns 6-7, rows 5-6) sits a lens that charges up: bright green on frame 112, a white-hot spot
on 131 and mostly white on 150 (the animation runs 112, 131, 150, 131). A dark crescent below and
right of it (rows 7-9) is the shadow of its raised housing.

Built as a believable machine, close to an egg (about 10 px wide and 9.5 px tall): a polished
green upper shell, domed high and round in section, over a darker, rounded lower hull (a clean
belly, nothing hanging under it), the two parted by a shallow recessed seam round the equator with
a running light set in it on each flank; a glowing lens dome on top, nearly flush, in a thin dark
bezel that rises a little at its lower right; a muzzle and an exhaust sunk as dark dimples into the
nose and tail (nothing stands proud of the outline); a satin, darker aft cowl (the sprite's shaded
tail), rounded like the rest of the egg rather than a cone. The hull is lofted densely along a
smooth outline and smooth shaded; only the seam, the two panel grooves, the dimples and the bezel
keep crisp edges. One model covers all three frames: the lens changes colour per frame (palette_material frames=) and the white-hot spot
of frame 131 is its own part (frame_part).

Run: blender --background --python assets/blender/sidekicks/mint-o-ship.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-mint-o-ship"
MODEL = "sidekicks/mint-o-ship"
TAG = "mint-o-ship"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
AXIS = 7.0  # the pod's centreline: sprite column edge 7 (the block's centre is edge 6)
SHARP = math.radians(38)  # edges sharper than this stay crisp; the rest is smooth shaded
UPPER_SEGS, BELLY_SEGS = 28, 18  # points round the upper shell's and the lower hull's sections
SECTIONS = 42  # cross-sections along the hull (plus the grooves')


def X(col):
    """Sprite column edge -> x (the 12x14 block is centred on the origin)."""
    return (col - 6) * P


def Y(row):
    """Sprite row edge -> y (sprite up is +Y)."""
    return (7 - row) * P


# The hull's outline: (row edge, half width px), a smooth line through the sprite's outline steps
# (within half a pixel of each), blunt at the nose (row 0) and tapering to the tail (row 13).
OUTLINE = [(0.0, 0.0), (0.12, 1.3), (0.5, 2.3), (1.0, 3.05), (1.7, 3.75), (2.6, 4.3), (3.6, 4.7),
           (4.6, 4.95), (5.8, 5.05), (7.2, 5.05), (8.4, 4.85), (9.3, 4.45), (10.2, 3.75), (11.0, 3.0),
           (11.8, 2.15), (12.5, 1.3), (12.95, 0.5), (13.05, 0.0)]
TOP = 1.02  # the upper shell's height over its (rounded, see height_width) half width: a high dome
BOTTOM = 0.82  # the lower hull's depth over its half width (the pod is near an ellipsoid, ~9.5 px tall)
ROUND = 2.2  # superellipse exponent of the upper shell's section: round, with full shoulders
SEAM_Z = 0.35  # px: the seam sits just above the middle of the pod's height
SEAM_H = 0.6  # px: the recessed seam's height
SEAM_D = 0.3  # px: how deep it's recessed
# Panel grooves across the shell: (row edge, half width px, inset px). The nose cap ends at row
# 2.4, the aft engine cowl starts at row 9.6.
GROOVES = [(2.4, 0.09, 0.12), (9.6, 0.09, 0.12)]  # shallow: the sprite has no bands there


def arc(n, a0, a1):
    return [a0 + (a1 - a0) * i / n for i in range(n + 1)]


def _smooth_outline(per=24):
    """OUTLINE as a dense polyline of (row, half width): a centripetal Catmull-Rom spline through its
    points, so the hull has no creases where the straight pieces between them would meet."""
    pts = [OUTLINE[0]] + OUTLINE + [OUTLINE[-1]]
    pts[0] = (2 * OUTLINE[0][0] - OUTLINE[1][0], 2 * OUTLINE[0][1] - OUTLINE[1][1])
    pts[-1] = (2 * OUTLINE[-1][0] - OUTLINE[-2][0], 2 * OUTLINE[-1][1] - OUTLINE[-2][1])
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        def tj(a, b):
            return max(1e-6, math.dist(a, b) ** 0.5)
        t0 = 0.0
        t1 = t0 + tj(p0, p1)
        t2 = t1 + tj(p1, p2)
        t3 = t2 + tj(p2, p3)
        for k in range(per):
            t = t1 + (t2 - t1) * k / per
            def lerp(a, b, ta, tb):
                return tuple((tb - t) / (tb - ta) * u + (t - ta) / (tb - ta) * v for u, v in zip(a, b))
            a1, a2, a3 = lerp(p0, p1, t0, t1), lerp(p1, p2, t1, t2), lerp(p2, p3, t2, t3)
            b1, b2 = lerp(a1, a2, t0, t2), lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    out.append(OUTLINE[-1])
    for (r0, _), (r1, _) in zip(out, out[1:]):
        assert r1 > r0, "the smoothed outline must run steadily down the rows"
    return out


DENSE = _smooth_outline()


def half_width(row):
    """The hull outline's half width (px) at a row edge, on the smoothed outline."""
    for (r0, w0), (r1, w1) in zip(DENSE, DENSE[1:]):
        if r0 <= row <= r1:
            return w0 + (w1 - w0) * (row - r0) / (r1 - r0)
    return 0.0


def height_width(row):
    """The half width (px) that sets the hull's height at a row: the outline's, eased up toward an
    egg's (an ellipse over the pod's length) where the outline tapers to the tail, so the aft cowl
    is rounded in side view instead of a straight cone."""
    w = half_width(row)
    r0, r1 = OUTLINE[0][0], OUTLINE[-1][0]
    c, L = (r0 + r1) / 2, (r1 - r0) / 2
    egg = 5.05 * math.sqrt(max(0.0, 1 - ((row - c) / L) ** 2))
    if row < c:
        return w
    d = max(0.0, egg - w)
    return w + 0.9 * d * d / (d + 0.3)


def hull_ring(w, hw, zone, inset=0.0):
    """One cross-section of the hull at half width w (px) and height half width hw (px), as
    (x px, z px, material key) points in order round it; each point's key is the material of the
    face from it to the next point. `inset` (px) sinks the upper shell for a panel groove, fading
    out just above the seam so the groove ends there and the lower hull stays whole."""
    s = min(1.0, w / 3.0)  # the seam shrinks to nothing at the nose and tail
    d, h = SEAM_D * s, SEAM_H * s
    zu, zl = SEAM_Z, SEAM_Z - h
    pts = []
    for a in arc(UPPER_SEGS, 0.0, math.pi):
        c, sn = math.cos(a), math.sin(a)
        k = inset * min(1.0, 3.0 * sn)
        x = (w - k) * math.copysign(abs(c) ** (2 / ROUND), c)
        z = zu + TOP * (hw - k) * abs(sn) ** (2 / ROUND)
        pts.append((x, z, zone))
    pts[-1] = (-w, zu, "seam")  # the lip of the upper shell, then into the seam
    pts += [(-(w - d), zu, "seam"), (-(w - d), zl, "seam")]
    wl = w - 0.12 * s  # the lower hull sits just inside the shell's lip
    pts.append((-wl, zl, "belly"))
    for a in arc(BELLY_SEGS, math.pi, 2 * math.pi)[1:-1]:
        pts.append((wl * math.cos(a), zl + BOTTOM * hw * math.sin(a), "belly"))
    pts += [(wl, zl, "seam"), (w - d, zl, "seam"), (w - d, zu, "seam")]
    return pts


def hull_sections():
    """(row, half width, height half width, zone of the band behind it, groove inset) along the hull: sections
    spaced evenly along the smoothed outline (closer where it turns fast, at the nose and tail),
    from the muzzle's rim (row 0.12) to the exhaust's (row 12.95), with the panel grooves cut in as
    steps down and up again."""
    first, last = OUTLINE[1][0], OUTLINE[-2][0]
    line = [(r, w) for r, w in DENSE if first <= r <= last]
    line = [(first, half_width(first))] + line + [(last, half_width(last))]
    acc = [0.0]
    for a, b in zip(line, line[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    rows = []
    for i in range(SECTIONS + 1):
        target = acc[-1] * i / SECTIONS
        k = next(k for k in range(1, len(acc)) if acc[k] >= target - 1e-9)
        f = (target - acc[k - 1]) / max(1e-9, acc[k] - acc[k - 1])
        rows.append(line[k - 1][0] + (line[k][0] - line[k - 1][0]) * f)
    # keep sections clear of the grooves so no sliver of shell sits beside one
    rows = [r for r in rows if all(abs(r - g) > gw + 0.18 for g, gw, _ in GROOVES)]
    secs = [(r, None) for r in rows]
    for g, gw, inset in GROOVES:
        secs += [(g - gw, None), (g + gw, None), (g - gw + 1e-4, inset), (g + gw - 1e-4, inset)]
    secs.sort(key=lambda t: t[0])
    out = []
    for r, inset in secs:
        if inset:
            zone = "groove"
        else:
            zone = "nose" if r < GROOVES[0][0] else "cowl" if r >= GROOVES[1][0] else "shell"
        out.append((r, half_width(r), height_width(r), zone, inset or 0.0))
    # a groove's walls: the band from the outer ring into the groove takes the groove's colour
    for i in range(len(out) - 1):
        if out[i + 1][3] == "groove":
            out[i] = out[i][:3] + ("groove", out[i][4])
    return out


def build_hull(bm, M):
    secs = hull_sections()
    rings, keys = [], []
    for row, w, hw, zone, inset in secs:
        pts = hull_ring(w, hw, zone, inset)
        rings.append([bm.verts.new((X(AXIS) + x * P, Y(row), z * P)) for x, z, _ in pts])
        keys.append([k for _, _, k in pts])
    n = len(rings[0])
    for (r0, r1), k in zip(zip(rings, rings[1:]), keys):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = M[k[i]]
    # Nose and tail: each closes in a shallow dark dimple sunk into the end of the hull (the muzzle
    # in the nose, the exhaust in the tail), so nothing stands proud of the sprite's outline.
    for ring, side in ((rings[0], 1), (rings[-1], -1)):
        y = ring[0].co.y - side * 0.3 * P
        zc = sum(v.co.z for v in ring) / n
        tip = bm.verts.new((X(AXIS), y, zc))
        for i in range(n):
            j = (i + 1) % n
            face = (ring[j], ring[i], tip) if side == 1 else (ring[i], ring[j], tip)
            bm.faces.new(face).material_index = M["dimple"]
    return [sum(v.co.z for v in rings[0]) / n, sum(v.co.z for v in rings[-1]) / n]


def shell_z(col, row):
    """Height (px) of the upper shell's top at a sprite point."""
    w = half_width(row)
    u = min(1.0, abs(col - AXIS) / w)
    return SEAM_Z + TOP * height_width(row) * (1 - u ** ROUND) ** (1 / ROUND)


def disc_loft(bm, centre, rings, sides, mats, axis="z", cap_end=True):
    """Rings round an axis through `centre` (x, y, z units): each ring is (offset px along the
    axis, radius px); mats[i] is the material of the band from ring i to ring i+1 (and the cap)."""
    cx, cy, cz = centre
    verts = []
    for off, r in rings:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            u, v = r * math.cos(a) * P, r * math.sin(a) * P
            if axis == "z":
                ring.append(bm.verts.new((cx + u, cy + v, cz + off * P)))
            else:  # along y
                ring.append(bm.verts.new((cx + u, cy + off * P, cz + v)))
        verts.append(ring)
    for i, (r0, r1) in enumerate(zip(verts, verts[1:])):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mats[i]
    if cap_end:
        last = verts[-1]
        if rings[-1][1] > 0:
            f = bm.faces.new(last)
            f.material_index = mats[-1]
    return verts


def dome(bm, centre, radius, height, sides, mat, segs=4):
    """A shallow dome (radius, height px) on a base ring at `centre`, pointing up."""
    rings = []
    for i in range(segs + 1):
        t = i / segs * (math.pi / 2)
        rings.append((height * math.sin(t), radius * math.cos(t) if i < segs else 0.0))
    cx, cy, cz = centre
    verts = []
    for off, r in rings[:-1]:
        verts.append([bm.verts.new((cx + r * math.cos(2 * math.pi * (k + 0.5) / sides) * P,
                                    cy + r * math.sin(2 * math.pi * (k + 0.5) / sides) * P, cz + off * P))
                      for k in range(sides)])
    top = bm.verts.new((cx, cy, cz + height * P))
    for r0, r1 in zip(verts, verts[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((verts[-1][k], verts[-1][j], top)).material_index = mat
    f = bm.faces.new(list(reversed(verts[0])))
    f.material_index = mat


def bezel(bm, centre, base, r_in, r_out, mat, sides=28):
    """A thin ring round the lens, sunk so it barely stands out of the shell: its top follows the
    shell's curve, a hair (0.07 px) over it at the upper left, rising to 0.32 px at the lower right;
    its foot is sunk well into the shell. `centre` is in sprite px (col, row)."""
    col, row = centre
    cx, cy = X(col), Y(row)
    rings = [[], [], [], []]
    for k in range(sides):
        a = 2 * math.pi * k / sides
        c, s = math.cos(a), math.sin(a)
        lr = max(0.0, (c - s) / math.sqrt(2))  # 1 toward the lower right (+x, -y)
        lift = 0.07 + 0.25 * lr ** 1.5
        h_out = shell_z(col + r_out * c, row - r_out * s) + lift
        h_in = shell_z(col + r_in * c, row - r_in * s) + lift
        top = max(h_out, h_in)
        for ring, r, z in zip(rings, (r_out, r_out, r_in, r_in), (base - 1.0, top - 0.08, top, base - 0.3)):
            ring.append(bm.verts.new((cx + r * c * P, cy + r * s * P, z * P)))
    # the outer wall's top edge sits a hair inside, giving a small chamfer
    for v, k in zip(rings[1], range(sides)):
        a = 2 * math.pi * k / sides
        v.co.x -= 0.12 * math.cos(a) * P
        v.co.y -= 0.12 * math.sin(a) * P
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat


def crisp(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False


def prism(bm, profile, rows, mat):
    """A crisp bar along Y: `profile` is its section, (x px, z px) points counter-clockwise seen
    from the front; `rows` (front row, back row) can be a function of the point's x px, to slant
    its ends."""
    rings = []
    for k in (0, 1):
        ring = []
        for x, z in profile:
            r = rows(x)[k] if callable(rows) else rows[k]
            ring.append(bm.verts.new((X(AXIS) + x * P, Y(r), z * P)))
        rings.append(ring)
    n = len(profile)
    bm.faces.new(rings[0]).material_index = mat
    bm.faces.new(list(reversed(rings[1]))).material_index = mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][j], rings[0][i], rings[1][i], rings[1][j])).material_index = mat


def build(sprite):
    coll = common.reset_collection(TAG)
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    mats = [
        pal(201, metallic=0.55, roughness=0.36),  # shell: polished green
        # the aft cowl: the shell's metal one shade darker; the groove marks the panel and the light
        # darkens the tail (the sprite's dark tail pixels are shading, not paint)
        common.palette_material(sprite, 199, f"{TAG}-cowl", metallic=0.55, roughness=0.36),
        pal(192, metallic=0.4, roughness=0.55),  # the recessed seam and panel grooves, vents
        pal(196, metallic=0.7, roughness=0.5),  # the lower hull
        pal(194, metallic=0.7, roughness=0.3),  # bezel, nose and tail dimples: dark green metal
        common.palette_material(sprite, 207, f"{TAG}-lens", emission_strength=0.6,
                                frames={150: 127}),  # the lens: bright green, white on frame 150
        pal(205, emission_strength=0.8),  # muzzle bore, running lights
        common.palette_material(sprite, 47, f"{TAG}-hot", emission_strength=4.0),  # frame 131's spot
        pal(201, metallic=0.55, roughness=0.36),  # the nose cap: the shell's green; the groove is the boundary
        pal(193, metallic=0.6, roughness=0.5),  # the panel grooves: dark lines, darker than either side
    ]
    M = {"shell": 0, "cowl": 1, "seam": 2, "groove": 9, "belly": 3, "nose": 8, "dimple": 4}
    TRIM, LENS, GLOW, HOT, DARK = 4, 5, 6, 7, 2

    bm = bmesh.new()
    nose_z, _ = build_hull(bm, M)

    # The lens on top, centred on columns 6-7 / rows 5-6 (edge 7, 6): a glowing dome in a thin dark
    # bezel, sunk nearly flush, that rises a little into a lip at its lower right,
    # the sprite's dark crescent there.
    lx, ly = 7.0, 6.0
    base = shell_z(lx, ly)
    bezel(bm, (lx, ly), base, 1.05, 1.4, TRIM)
    dome(bm, (X(lx), Y(ly), (base - 0.08) * P), 1.05, 0.42, 20, LENS, segs=5)

    # The muzzle's bore: a small dim-glowing disc sunk in the nose dimple, facing forward.
    disc_loft(bm, (X(AXIS), Y(0.0), nose_z), [(-0.32, 0.45), (-0.32, 0.0)], 10, [GLOW], axis="y",
              cap_end=False)

    # A running light set into the seam on each flank (rows 7.6-8.4), inside the outline.
    for side in (1, -1):
        w = half_width(8.0)
        x0, x1 = w - SEAM_D - 0.05, w - 0.08
        zl, zu = SEAM_Z - SEAM_H + 0.12, SEAM_Z - 0.12
        lp = [(x0, zl), (x1, zl), (x1, zu), (x0, zu)]
        if side < 0:
            lp = [(-x, z) for x, z in reversed(lp)]
        prism(bm, lp, (7.6, 8.4), GLOW)

    crisp(bm)
    body = common.mesh_object(TAG, bm, mats, coll, smooth=True)

    # Frame 131's white-hot spot (the sprite's pixel at column 6, row 5): a small bright bead on
    # the lens, up and left of its centre.
    hb = bmesh.new()
    dome(hb, (X(6.6), Y(5.6), (base + 0.12) * P), 0.5, 0.4, 12, HOT, segs=3)
    crisp(hb)
    hot = common.frame_part(common.mesh_object(f"{TAG}-hot-131", hb, mats, coll, smooth=True), [131])
    return [body, hot]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        common.render_frame_previews(objects, out, sprite, ROOT)


if __name__ == "__main__":
    main()
