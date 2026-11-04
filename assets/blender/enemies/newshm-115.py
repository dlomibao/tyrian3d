"""Steel ball (newshm.shp frame 115, newsha.shp frames 165, 203, 241, 279): a hard-surface steel
mine that is its sprite in 3D, built the way the player ships are (usp_talon.py, D50-D53).

What the sprite shows (reference/models/newshm-115, 24x28, palette 5, a ground and air unit in six
levels across episodes 1 and 3):
- Plan: a ball, cols 3-20 x rows 5-21, centred on x 0 (column edge 12) and row edge 13.5.
- One colour ramp (48-63, steel blue). The white 2x3 cluster upper left (rows 9-12) and the bright
  crescent lower right (rows 16-20) are sheen and a rim reflection on a round polished body, not
  parts. No canopy, eye, light or hatch.
- Frames 165, 203 and 241 are the same ball drawn darker (every pixel 5, 3 and 2 steps down): a
  pulse. One model covers all five frames; every material takes the darker shade on those frames
  (palette_material frames=, D17).
- Edge (D74): the outer ring is 53 on 115/279 (the ramp's darkest step there, luma 41) and ink
  (48/50/51) on 165/203/241: the same ink border, pulsed by the palette. sprite_mask's palette-pulse
  rule (docs/agents/OUTLINE-BORDER.md) counts it as ink on every frame, so the plan goes to the
  INNER edge of that ring (RX/RY 8.13/7.67: rule grid IoU 1.0 on all five frames); with the game's
  ink the model lands on the sprite's outer edge.

Design: one continuous polished ball (a single closed lon/lat surface). Eight faint hairline gore
seams (0.15 px wide, 0.03 deep, the gores' own pal 57) run from a hairline groove over the belt up to
a plain crown (no hatch: the top view reads as a smooth ball). The equatorial belt is the ball's own
surface raised 0.10 px with rounded shoulders, so the plan outline stays a smooth circle; its eight
joints are short grooves on its upper and lower halves that leave the equator whole, with a low hex
bolt each side of every joint on the upper half. The underside is plain (no detail, by design).

Colours (median palette index per region, the ring and >= 61 highlights left out as lighting):
belt 55, gores/crown/seams 57, belt joints 54, bolts 57, lower 57. Satin steel (roughness 0.66,
metallic 0.35 of the parts' own) with one polished, clear-coated patch (0.20, coat 0.22, 26 degrees
round the sheen direction) where the sprite draws its sheen, so in game one clear white sheen sits at
the upper left instead of the four lobes a uniform roughness gives. Tuned at game scale (MINES,
tick 1640): coat 0.32 / patch 27 degrees read matte, coat 0.18 / 34 degrees split into wet glints
(see the SHEEN constants).

Texture: no concept projection; an ambient occlusion / roughness bake only (usp_talon.bake_maps,
the sheen patch added to its roughness map, and a clear-coat weight map),
Base Color = map x palette colour, so pal_<index>, fades and the hit flash still apply. An outline
shell (common.outline_shell, D51).

Layout: sprite px, x = column edge - 12, y = row edge, z up; usp_talon.finish maps X = x / 12,
Y = (14 - y) / 12, Z = z / 12.

Run: blender --background --factory-startup --python assets/blender/enemies/newshm-115.py
     [-- --preview out.png] [--no-bake] [--out x.glb]
"""

import math
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part  # noqa: E402

NAME = "newshm-115"
MODEL = f"enemies/{NAME}"

# --- shape (sprite px: x = column edge - 12, y = row edge, z up) -------------------------------
CX, CY, CZ = 0.0, 13.5, 0.0
RX, RY = 8.13, 7.67     # the plan half-widths at the equator (the belt's crown: the model's plan edge)
BELT_H = 0.10           # how far the belt's crown stands out of the ball, following its curve
RXB, RYB = RX - BELT_H, RY - BELT_H   # the ball's own equator
RZ = 7.6                # the ball's vertical half-height
BZ = 1.6                # the belt's half-height
LAT_B = math.asin(BZ / RZ)            # the belt's edge
SHOULDER = 0.07         # how far (radians) the belt's crown rounds down into the ball
CAP_R = 1.9             # the polar hatch's plan radius (about 23% of the diameter), flush
LAT_C = math.acos(CAP_R / RXB)
W_SEAM = 0.15           # hairline groove width, px
D_SEAM = 0.03           # hairline groove depth (shallow: a faint line, the ball reads smooth)
FL = 0.035              # the groove's wall run (floor = width - 2 FL)
JOINT_Z = 0.55          # belt joints run from the belt's edge in to |z| = this, the equator stays whole

NG = 8                  # gores (and belt segments)
G0 = math.radians(22.5)  # first seam: gore centres at 0, 45, 90 (front) ...
NLON = 64               # base longitude samples


def lin(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def surf(lon, lat, off):
    c = math.cos(lat)
    p = Vector((RXB * c * math.cos(lon), RYB * c * math.sin(lon), RZ * math.sin(lat)))
    n = Vector((p.x / RXB ** 2, p.y / RYB ** 2, p.z / RZ ** 2)).normalized()
    return tuple(Vector((CX, CY, CZ)) + p + n * off)


def belt_off(lat):
    """The belt's crown: BELT_H at the equator band, rounding down to the ball over SHOULDER."""
    a = abs(lat)
    if a <= LAT_B - SHOULDER:
        return BELT_H
    if a >= LAT_B:
        return 0.0
    t = (LAT_B - a) / SHOULDER
    return BELT_H * math.sin(t * math.pi / 2)


# --- materials ------------------------------------------------------------------------------------
BELT, GORE, CAP, SEAM, JOINT, BOLT, LOWER = range(7)
PAL_OF = {BELT: 55, GORE: 57, CAP: 57, SEAM: 57, JOINT: 54, BOLT: 57, LOWER: 57}
# The pulse: frames 165, 203, 241 are every shade 5, 3 and 2 steps darker.
PULSE = {165: -5, 203: -3, 241: -2}
TEXTURED = (BELT, GORE, CAP, SEAM, JOINT, BOLT, LOWER)
TINT = (1.0, 0.93, 0.84)  # game capture: blue/red 3.3 vs the sprite's 2.6 untinted; this pulls it back
METAL = 0.35
# The sheen (game lighting: view.ts sun from the left and the camera's side, RoomEnvironment panels).
# A sphere's highlights sit where the lights put them, and a uniform roughness gives the game's four
# light lobes (0.40: lower centre, left, top, right; 0.52: none, satin). So the steel is satin
# (R_HI) except a polished patch where the sprite draws its sheen, upper left as the tilted game
# camera sees it (SHEEN_DIR, object space x right / y screen-up / z up), and a clear coat on that
# patch makes the room's upper-left panels read as one broad white sheen. Roughness is baked into
# the metallic-roughness map (aim_sheen), the coat into its own weight map (add_coat).
ROUGH = 0.40            # the materials' base roughness (the bake adds occlusion and edge terms)
R_LO, R_HI = 0.20, 0.66  # patch / elsewhere
COAT, COAT_ROUGH = 1.0, 0.22
SHEEN_PATCHES = [  # (direction, outer angle, inner angle, weight)
    (Vector((-0.42, 0.10, 0.90)).normalized(), 26, 9, 1.0),
]


def materials(sprite):
    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.palette_material(sprite, i, f"ball115_{tag}", metallic=metallic * METAL, roughness=roughness,
                                       frames={f: i + d for f, d in PULSE.items()})
    return [
        pal(BELT, "belt", 0.6, ROUGH),
        pal(GORE, "gore", 0.6, ROUGH),
        pal(CAP, "cap", 0.6, ROUGH),
        pal(SEAM, "seam", 0.5, 0.4),
        pal(JOINT, "joint", 0.5, 0.4),
        pal(BOLT, "bolt", 0.7, 0.48),
        pal(LOWER, "lower", 0.5, ROUGH),
    ]


# --- the ball: one closed lon/lat grid, the grooves pressed into it --------------------------------
def rows():
    """(lat, groove_floor) from south to north, with rows at every groove and zone edge."""
    out = []
    out += [(la, False) for la in lin(-math.radians(80), -LAT_B, 4)]
    out += [(la, False) for la in lin(-LAT_B, -LAT_B + SHOULDER, 2)[1:]]
    out += [(-JOINT_Z / RZ - 0.004, False), (-JOINT_Z / RZ, False)]
    out += [(la, False) for la in lin(-JOINT_Z / RZ, JOINT_Z / RZ, 2)[1:]]
    out += [(JOINT_Z / RZ + 0.004, False)]
    out += [(la, False) for la in lin(LAT_B - SHOULDER, LAT_B, 2)]
    # the hairline groove round the belt's top edge
    g = LAT_B + 0.01
    w, f = W_SEAM / RZ, FL / RZ
    out += [(g, False), (g + f, True), (g + w - f, True), (g + w, False)]
    gore0 = g + w
    out += [(la, False) for la in lin(gore0, LAT_C - w, 6)[1:]]
    out += [(LAT_C - w + f, False), (LAT_C - f, False), (LAT_C, False)]   # no hatch groove: a plain crown
    out += [(la, False) for la in lin(LAT_C, math.radians(86), 3)[1:]]
    return out, gore0


def zone(lat, gore0):
    if lat >= LAT_C:
        return CAP
    if lat >= gore0:
        return GORE
    if abs(lat) < LAT_B:
        return BELT
    return LOWER if lat < 0 else GORE


def columns():
    """[(base lon, px offset, seam floor)]: the seam/joint grooves as columns whose longitude keeps the
    groove's width in px at every latitude; base samples kept clear of them."""
    seams = [G0 + k * 2 * math.pi / NG for k in range(NG)]
    cols = []
    for i in range(NLON):
        lo = 2 * math.pi * i / NLON
        if min(abs((lo - s + math.pi) % (2 * math.pi) - math.pi) for s in seams) > 0.06:
            cols.append((lo, 0.0, False))
    for s in seams:
        h = W_SEAM / 2
        cols += [(s, -h, False), (s, -h + FL, True), (s, h - FL, True), (s, h, False)]
    return sorted(cols, key=lambda c: (c[0] % (2 * math.pi), c[1]))


def build_ball(Pt):
    rs, gore0 = rows()
    cs = columns()
    jz = JOINT_Z / RZ
    grid = []
    for la, rfloor in rs:
        r = max(0.6, RXB * math.cos(la))
        seam_on = (gore0 <= la <= LAT_C) or (jz + 0.002 < abs(la) <= LAT_B + 1e-6)
        row = []
        for lo, px, cfloor in cs:
            off = belt_off(la)
            if rfloor or (cfloor and seam_on):
                off -= D_SEAM
            row.append(Pt.v(surf(lo + px / r, la, off)))
        grid.append(row)
    centre = (CX, CY, CZ)
    nc = len(cs)
    for k in range(len(rs) - 1):
        la = 0.5 * (rs[k][0] + rs[k + 1][0])
        lat_groove = rs[k][1] or rs[k + 1][1]
        in_seam = (gore0 <= la <= LAT_C)
        in_joint = jz < abs(la) < LAT_B
        for i in range(nc):
            j = (i + 1) % nc
            col_groove = cs[i][2] and cs[j][2] or (cs[i][2] != cs[j][2])
            mat = zone(la, gore0)
            if lat_groove:
                mat = SEAM if la > LAT_B else mat
            elif col_groove and in_seam:
                mat = SEAM
            elif col_groove and in_joint:
                mat = JOINT
            Pt.f((grid[k][i], grid[k][j], grid[k + 1][j], grid[k + 1][i]), mat, away=centre)
    for k, sgn, mat in ((0, -1, LOWER), (len(rs) - 1, 1, CAP)):
        pole = Pt.v(surf(0, sgn * math.pi / 2, 0.0))
        for i in range(nc):
            j = (i + 1) % nc
            Pt.f((grid[k][i], grid[k][j], pole), mat, away=centre)


def hexbolt(Pt, lon, z, r=0.3):
    """A low hex head on the belt's crown, sunk into it, its top 0.05 proud."""
    la = math.asin(z / RZ)
    c = Vector(surf(lon, la, belt_off(la)))
    n = (c - Vector(surf(lon, la, belt_off(la) - 1.0))).normalized()
    t = Vector((-n.y, n.x, 0)).normalized()
    up = n.cross(t).normalized()
    seg = 6
    ring = []
    for rad, h in ((r, -0.12), (r, 0.03), (r * 0.8, 0.05)):
        ring.append([Pt.v(tuple(c + n * h + (t * math.cos(2 * math.pi * k / seg) + up * math.sin(2 * math.pi * k / seg)) * rad))
                     for k in range(seg)])
    for r0, r1 in zip(ring, ring[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            Pt.f((r0[k], r0[j], r1[j], r1[k]), BOLT, away=tuple(c - n * 0.5))
    Pt.f(ring[-1], BOLT, out=tuple(n))


def build_bolts(Pt):
    """A bolt each side of every belt joint, on the belt's upper half (the camera's side)."""
    for k in range(NG):
        s = G0 + k * 2 * math.pi / NG
        for sgn in (-1, 1):
            hexbolt(Pt, s + sgn * 0.75 / RXB, 0.95)


def build(coll, sprite):
    mats = materials(sprite)
    ball = Part("ball115_ball", smooth_angle=35)
    build_ball(ball)
    det = Part("ball115_bolts", smooth_angle=40)
    build_bolts(det)
    return [T.finish(p, mats, coll) for p in (ball, det)]


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "ball115")
    aim_sheen(obj, bpy.data.images["ball115_rm"], out_dir)


def _smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def sheen_weight(n):
    w = 0.0
    for d, a0, a1, k in SHEEN_PATCHES:
        w = max(w, k * _smooth(math.cos(math.radians(a0)), math.cos(math.radians(a1)), n.dot(d)))
    return w


def sheen_rough(n):
    """Roughness by surface direction (object space: x right, y screen-up, z up): polished (R_LO) where
    the sprite draws its sheen (upper left) and its rim crescent (lower right), satin (R_HI) elsewhere,
    so of the game's lights only the ones reflected there read as highlights."""
    return R_HI - (R_HI - R_LO) * sheen_weight(n)


def aim_sheen(obj, img, out_dir):
    """Shift the baked roughness map (G) by sheen_rough(normal) - ROUGH, keeping its occlusion and edge
    terms. Rasterised per triangle in the 'bake' UVs, then the shift is grown into the bake margin."""
    import numpy as np
    W, H = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
    delta = np.zeros((H, W), np.float32)
    coat_w = np.zeros((H, W), np.float32)
    have = np.zeros((H, W), bool)
    me = obj.data
    me.calc_loop_triangles()
    uv = me.uv_layers["bake"].data
    rot = obj.matrix_world.to_3x3()
    corner_n = getattr(me, "corner_normals", None)
    for tri in me.loop_triangles:
        P = [Vector(uv[li].uv) * Vector((W, H)) for li in tri.loops]
        N = [(rot @ (corner_n[li].vector if corner_n is not None else me.loops[li].normal)).normalized()
             for li in tri.loops]
        x0, x1 = int(max(0, min(p.x for p in P) - 1)), int(min(W - 1, max(p.x for p in P) + 1))
        y0, y1 = int(max(0, min(p.y for p in P) - 1)), int(min(H - 1, max(p.y for p in P) + 1))
        den = (P[1].y - P[2].y) * (P[0].x - P[2].x) + (P[2].x - P[1].x) * (P[0].y - P[2].y)
        if abs(den) < 1e-12:
            continue
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                cx, cy = xx + 0.5, yy + 0.5
                a = ((P[1].y - P[2].y) * (cx - P[2].x) + (P[2].x - P[1].x) * (cy - P[2].y)) / den
                b = ((P[2].y - P[0].y) * (cx - P[2].x) + (P[0].x - P[2].x) * (cy - P[2].y)) / den
                c = 1 - a - b
                if min(a, b, c) < -0.02:
                    continue
                n = (N[0] * a + N[1] * b + N[2] * c).normalized()
                delta[yy, xx] = sheen_rough(n) - ROUGH
                coat_w[yy, xx] = sheen_weight(n)
                have[yy, xx] = True
    for _ in range(8):  # grow into the margin
        grow = ~have
        cnt = np.zeros_like(delta)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cnt += np.roll(have.astype(np.float32), (dy, dx), (0, 1))
        fill = grow & (cnt > 0)
        for arr in (delta, coat_w):
            acc = np.zeros_like(arr)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                acc += np.roll(np.where(have, arr, 0), (dy, dx), (0, 1))
            arr[fill] = acc[fill] / cnt[fill]
        have |= fill
    px[..., 1] = np.clip(px[..., 1] + delta, 0.05, 1.0)
    img.pixels[:] = px.ravel()
    img.update()
    img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
    img.file_format = "PNG"
    img.save()
    if COAT > 0:
        add_coat(obj, coat_w, out_dir)


def add_coat(obj, w, out_dir):
    """A clear coat (white specular layer, COAT_ROUGH) weighted by the sheen patch."""
    import numpy as np
    H, W = w.shape
    img = bpy.data.images.new("ball115_coat", W, H, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    px = np.zeros((H, W, 4), np.float32)
    px[..., 0] = px[..., 1] = px[..., 2] = np.clip(w * COAT, 0, 1)
    px[..., 3] = 1
    img.pixels[:] = px.ravel()
    img.update()
    img.filepath_raw = str(Path(out_dir) / "ball115_coat.png")
    img.file_format = "PNG"
    img.save()
    for m in obj.data.materials:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[0], bsdf.inputs["Coat Weight"])
        bsdf.inputs["Coat Roughness"].default_value = COAT_ROUGH


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, voxel=0.014, faces=1500, smooth=12)
    shell.name = shell.data.name = f"{NAME}_outline"
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
