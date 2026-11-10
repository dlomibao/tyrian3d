"""newsha-199: a glowing red glass orb held in a machined steel socket (newsha.shp 199,
201, 239, 277; boss-linked ground object). Blueprint-led: every part is built from the cross-
sections of blueprint/model.js (plan ellipse = the glass equator, traced to the D74 inner mask).

Reading of the sprite (24x28): one round red dome. The white-hot spot upper-left is the glint of
the light on glossy glass and the yellow crescent lower-right is light refracted through the glass
onto its far wall: both are lighting (rubric "a saturated colour with a near-white core is a light:
glowing glass set in a housing"), so the glass is one smooth emissive spheroid, nothing painted on.
The four frames are a palette pulse (+2/+3/+5 indices), so one model covers them through the glass
material's frame colours (D17). Body index: median of the inner-mask pixels without the darkest and
brightest 15 % = 116 on 199 (118/119/121 on 201/239/277).

Engineering where the top view can't see it (all inside the equator, s < 1): a revolved satin-steel
socket (plinth, machined groove, collar with a second groove, a bezel ring and a dark gasket gripping
the glass below its equator), six chamfered claws up the glass to latitude -18 deg on hinge pins,
bolted clamp blocks, access plates between the claws and a cable gland on the north side (the boss
link) with its armoured cable bending into the ground. Underside: the closed plinth disc only.

Why steel: palette 5's steel ramp (208-215) is used for the socket because the sprite itself shows
two index-208 pixels peeking out at the lower right (row 17 col 19, row 18 col 18): the ring the
glass sits in. The rest of the ramp (209-215) is the same metal in shade, hidden under the glass
overhang. 209 is the darker cradle accent (plinth groove band, gasket); 208 is the rear feed cable.
Claws stop at latitude -20 and every steel part stays inside s <= 0.98 of the equator, so no steel
shows outside the glass in the top view.

Run: Blender -b --factory-startup -P assets/blender/enemies/newsha-199.py -- [--no-bake] [--preview out.png]
(the glass-only frames 201/239/277 are a palette pulse: glass material frames=, D17)
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

NAME = "newsha-199"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
D2R = math.pi / 180

# Blueprint dims (sprite px; x = col + 0.5 - 12, y = 14 - (row + 0.5), z up).
CX, CY = 0.0, 0.5
RX, RY = 8.0, 7.5          # glass equator = top silhouette
ZC, RZ = 6.2, 6.8          # equator height and vertical semi-axis (top of the glass 13 px)
LAT_LIP = -42.0            # glass ends inside the socket here
LAT_CLAW = -20.0           # claw tips (outer face s <= .98: inside the equator)
SEG = 64
CLAW_ANG = [0, 60, 120, 180, 240, 300]   # none at north (gland) or due south (camera side)

# extra palette-5 colours the hidden socket uses (sprite.json lists only the ones the sprite shows)
STEEL = {208: (4, 28, 40), 209: (8, 40, 56), 210: (16, 52, 73), 211: (24, 65, 85), 212: (32, 81, 97),
         213: (44, 93, 113), 214: (56, 109, 125), 215: (73, 125, 142)}


def E(s, a, z):
    """Point of the plan ellipse scaled by s at angle a (rad, 0 = east, CCW), height z."""
    return Vector((CX + RX * s * math.cos(a), CY + RY * s * math.sin(a), z))


def glass(lat, a, off=0.0):
    """Glass surface point at latitude lat (deg) and angle a, pushed out by off px along its normal;
    also returns the normal and the circumferential tangent."""
    p = lat * D2R
    c, s = math.cos(p), math.sin(p)
    x, y, z = RX * c * math.cos(a), RY * c * math.sin(a), RZ * s
    n = Vector((x / RX ** 2, y / RY ** 2, z / RZ ** 2)).normalized()
    t = Vector((-RX * math.sin(a), RY * math.cos(a), 0)).normalized()
    return Vector((CX + x, CY + y, ZC + z)) + n * off, n, t


def glass_s(z):
    """Plan scale s of the glass at height z (below the equator)."""
    v = (z - ZC) / RZ
    return math.sqrt(max(0.0, 1 - v * v))


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def rings(self, R, mat, closed=True, cap0=False, cap1=False, smooth=True):
        """Quads between consecutive rings of points (px); optional fan caps."""
        V = [[self.bm.verts.new(p * PX) for p in r] for r in R]
        n = len(R[0])
        m = n if closed else n - 1
        fs = []
        for a, b in zip(V, V[1:]):
            for k in range(m):
                fs.append(self.bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])))
        for f in fs:
            f.material_index = mat
            f.smooth = smooth
        for ring, flip in ((V[0], True) if cap0 else (None, None), (V[-1], False) if cap1 else (None, None)):
            if ring is None:
                continue
            f = self.bm.faces.new(list(reversed(ring)) if flip else ring)
            f.material_index = mat
            f.smooth = False
        return V

    def revolve(self, prof, mat, cap0=True, cap1=True, seg=SEG, smooth_rows=None):
        """Revolve an (s, z) profile about the plan centre. Each profile corner gets its own ring
        pair (split normals) unless listed in smooth_rows."""
        R = [[E(s, 2 * math.pi * k / seg, z) for k in range(seg)] for s, z in prof]
        V = self.rings(R, mat, cap0=cap0, cap1=cap1)
        return V

    def box(self, o, u, v, w, hu, hv, hw, ch, mat):
        """Box in a local frame (u radial out, v tangent, w up), chamfered round its outer face."""
        def P(a, b, c):
            return o + u * a + v * b + w * c
        def sec(b, k):
            c = ch * k
            return [P(-hu, b, -hw), P(hu - c, b, -hw), P(hu, b, -hw + c), P(hu, b, hw - c),
                    P(hu - c, b, hw), P(-hu, b, hw)]
        R = [sec(-hv, 0.0), sec(-hv + ch, 1.0), sec(hv - ch, 1.0), sec(hv, 0.0)]
        R[0] = [o + (p - o) * 1.0 for p in R[0]]
        # outer face chamfer at the ends: shrink end sections toward the back face
        R[0] = [P(-hu, -hv, -hw + ch), P(hu - ch, -hv, -hw + ch), P(hu - ch, -hv, -hw + ch),
                P(hu - ch, -hv, hw - ch), P(hu - ch, -hv, hw - ch), P(-hu, -hv, hw - ch)]
        R[3] = [P(-hu, hv, -hw + ch), P(hu - ch, hv, -hw + ch), P(hu - ch, hv, -hw + ch),
                P(hu - ch, hv, hw - ch), P(hu - ch, hv, hw - ch), P(-hu, hv, hw - ch)]
        self.rings(R, mat, cap0=True, cap1=True, smooth=False)

    def cyl(self, b, ax, r, h, mat, sides=6, ch=0.06, smooth=False):
        ax = ax.normalized()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        v = ax.cross(u)
        def ring(rr, t):
            return [b + ax * t + (u * math.cos(2 * math.pi * (k + 0.5) / sides) +
                                  v * math.sin(2 * math.pi * (k + 0.5) / sides)) * rr for k in range(sides)]
        self.rings([ring(r - ch, 0), ring(r, ch), ring(r, h - ch), ring(r - ch, h)], mat,
                   cap0=True, cap1=True, smooth=smooth)


def materials(sprite):
    spr = dict(sprite)
    spr["colors"] = dict(sprite["colors"])
    for i, rgb in STEEL.items():
        spr["colors"].setdefault(str(i), list(rgb))
    mats = [
        common.palette_material(spr, 116, f"{NAME}-glass", metallic=0.0, roughness=0.28,
                                emission_strength=0.12, frames={201: 118, 239: 119, 277: 121}),  # 0 glass
        common.palette_material(spr, 211, NAME, metallic=0.6, roughness=0.42),  # 1 socket steel
        common.palette_material(spr, 212, NAME, metallic=0.6, roughness=0.38),  # 2 claws
        common.palette_material(spr, 210, NAME, metallic=0.6, roughness=0.48),  # 3 blocks, plates, gland
        common.palette_material(spr, 214, NAME, metallic=0.7, roughness=0.32),  # 4 bolts, pins (machined)
        common.palette_material(spr, 209, NAME, metallic=0.1, roughness=0.75),  # 5 gasket, cradle band
        common.palette_material(spr, 208, NAME, metallic=0.3, roughness=0.6),  # 6 feed cable
    ]
    return mats


GLASS, SOCK, CLAW, BLOCK, BOLT, DARK, CABLE = range(7)


def build_glass(M):
    """Spheroid from the lip latitude to the pole; flat disc under it, inside the socket."""
    lats = [LAT_LIP + (90 - LAT_LIP) * math.sin(k / 26 * math.pi / 2) ** 0.85 for k in range(26)]
    R = [[glass(lat, 2 * math.pi * k / SEG)[0] for k in range(SEG)] for lat in lats]
    V = M.rings(R, GLASS, cap0=True)
    pole = M.bm.verts.new(Vector((CX, CY, ZC + RZ)) * PX)
    for k in range(SEG):
        f = M.bm.faces.new((V[-1][k], V[-1][(k + 1) % SEG], pole))
        f.material_index = GLASS
        f.smooth = True


def build_socket(M):
    """Plinth, groove, collar (with a second groove), shoulder under the bezel: one revolved
    profile of chamfered stations. Then the bezel ring and gasket hugging the glass."""
    prof = [
        (0.00, 0.00),                              # bottom disc centre (closed underside)
        (0.900, 0.00), (0.900, 0.42),              # plinth wall
        (0.885, 0.50), (0.865, 0.56),              # chamfer
        (0.835, 0.58), (0.835, 0.74),              # machined groove (shadow line)
        (0.862, 0.77), (0.862, 1.08),              # collar band, lower
        (0.848, 1.11), (0.848, 1.19),              # second groove (panel line)
        (0.862, 1.22), (0.862, 1.52),              # collar band, upper
        (0.846, 1.62), (0.820, 1.66),              # chamfer to the shoulder
        (0.790, 1.66),                             # shoulder top, under the bezel
        (0.70, 1.66), (0.70, 1.30),                # inner, down into the glass
    ]
    R = []
    for s, z in prof:
        if s == 0.0:
            R.append([E(0, 0, z)] * 1)
            continue
        R.append([E(s, 2 * math.pi * k / SEG, z) for k in range(SEG)])
    # bottom: fan from the centre (closed plinth disc), then the profile rings
    V = M.rings(R[1:], SOCK, cap0=True, cap1=True, smooth=False)
    # darker cradle band seated in the plinth groove (pal_209) so the socket reads contrasty under the rim
    R = [[E(s, 2 * math.pi * k / SEG, z) for k in range(SEG)] for s, z in
         ((0.836, 0.585), (0.846, 0.60), (0.846, 0.72), (0.836, 0.735))]
    M.rings(R, DARK, smooth=False)
    # bezel: a ring hugging the glass from z 1.66 up to z 2.25, standing 0.22 px proud of it
    zs = [1.66, 1.74, 2.02, 2.20, 2.27]
    offs = [0.30, 0.34, 0.34, 0.26, 0.04]
    R = [[E(glass_s(z) + o / 7.75, 2 * math.pi * k / SEG, z) for k in range(SEG)] for z, o in zip(zs, offs)]
    R.insert(0, [E(0.78, 2 * math.pi * k / SEG, 1.66) for k in range(SEG)])
    R.append([E(glass_s(2.27) - 0.01, 2 * math.pi * k / SEG, 2.27) for k in range(SEG)])
    M.rings(R, SOCK, smooth=False)
    # gasket: a thin dark bead where the bezel meets the glass
    zs = [2.22, 2.32, 2.42]
    offs = [0.0, 0.10, 0.0]
    R = [[E(glass_s(z) + o / 7.75 - 0.004, 2 * math.pi * k / SEG, z) for k in range(SEG)] for z, o in zip(zs, offs)]
    M.rings(R, DARK)


def build_claws(M):
    """Six claws up the glass: chamfered sections stepped along a meridian (pchip taper), a hinge
    pin at the bezel, a clamp block with two hex bolts on the collar under each."""
    lat0 = -36.0
    lats = [lat0 + (LAT_CLAW - lat0) * t / 10 for t in range(11)]
    wid = T.pchip([0, 0.5, 0.85, 1.0], [0.62, 0.52, 0.42, 0.26])   # half width, px
    thk = T.pchip([0, 0.6, 0.9, 1.0], [0.40, 0.32, 0.24, 0.10])   # thickness, px
    for ad in CLAW_ANG:
        a = ad * D2R
        R = []
        for i, lat in enumerate(lats):
            t = i / 10
            w, th = wid(t), thk(t)
            p, n, tg = glass(lat, a, -0.06)
            ch = min(0.12, th * 0.4)
            R.append([p + tg * (-w), p + tg * w, p + tg * w + n * (th - ch + 0.06),
                      p + tg * (w - ch) + n * (th + 0.06), p + tg * (-w + ch) + n * (th + 0.06),
                      p + tg * (-w) + n * (th - ch + 0.06)])
        M.rings(R, CLAW, cap0=True, cap1=True, smooth=False)
        # spine rib down the claw's middle (machined ridge), stopping short of the tip
        R = []
        for lat in lats[1:8]:
            p, n, tg = glass(lat, a, 0.0)
            th = thk((lat - lat0) / (LAT_CLAW - lat0)) + 0.06
            R.append([p + n * th + tg * -0.14, p + n * th + tg * 0.14, p + n * (th + 0.1) + tg * 0.07,
                      p + n * (th + 0.1) + tg * -0.07])
        M.rings(R, BOLT, cap0=True, cap1=True, smooth=False)
        # hinge pin across the claw root, just above the bezel
        p, n, tg = glass(lat0 + 1.0, a, 0.42)
        M.cyl(p - tg * 0.85, tg, 0.26, 1.7, BOLT, sides=8, ch=0.05, smooth=True)
        # clamp block on the collar under the claw, two hex bolts on its face
        u = Vector((math.cos(a), math.sin(a), 0))
        v = Vector((-math.sin(a), math.cos(a), 0))
        o = E(0.862, a, 1.28) + u * 0.12
        M.box(o, u, v, Vector((0, 0, 1)), 0.36, 0.92, 0.50, 0.12, BLOCK)
        for sgn in (-1, 1):
            M.cyl(o + u * 0.30 + v * (sgn * 0.52), u, 0.19, 0.16, BOLT, sides=6, ch=0.04)
        # web joining claw root to block (a sloped gusset following the bezel)
        p0 = E(0.862, a, 1.78) + u * 0.18
        p1, n1, _ = glass(lat0, a, 0.08)
        R = [[p0 + v * -0.42, p0 + v * 0.42, p0 + v * 0.42 + Vector((0, 0, -0.5)), p0 + v * -0.42 + Vector((0, 0, -0.5))],
             [p1 + v * -0.5, p1 + v * 0.5, p1 + v * 0.5 - n1 * 0.4, p1 + v * -0.5 - n1 * 0.4]]
        M.rings(R, CLAW, cap0=True, cap1=True, smooth=False)


def build_plates(M):
    """Access plates on the collar between the claws, each held by four small bolts."""
    for ad in CLAW_ANG:
        a = (ad + 30) * D2R
        if abs(((ad + 30) % 360) - 90) < 1:   # the gland sits here
            continue
        u = Vector((math.cos(a), math.sin(a), 0))
        v = Vector((-math.sin(a), math.cos(a), 0))
        o = E(0.862, a, 1.15)
        M.box(o, u, v, Vector((0, 0, 1)), 0.05, 1.05, 0.30, 0.04, BLOCK)
        for sv in (-1, 1):
            for sz in (-1, 1):
                M.cyl(o + u * 0.04 + v * (sv * 0.85) + Vector((0, 0, sz * 0.18)), u, 0.08, 0.06, BOLT,
                      sides=6, ch=0.02)


def build_feed(M):
    """Cable gland on the north side of the plinth and the armoured cable bending into the ground
    (hidden from the top: max y ~7.8, inside s <= 0.98 of the glass)."""
    a = 90 * D2R
    u = Vector((0, 1, 0))
    b = E(0.80, a, 1.0)
    # flange, gland body, nut
    M.cyl(b, u, 0.72, 0.18, BLOCK, sides=12, ch=0.04, smooth=True)
    M.cyl(b + u * 0.16, u, 0.46, 0.42, BLOCK, sides=12, ch=0.06, smooth=True)
    M.cyl(b + u * 0.30, u, 0.52, 0.16, BOLT, sides=6, ch=0.04)
    # cable: a quarter bend from the gland mouth down into the ground
    rc, bend = 0.28, 0.45
    y0 = b.y + 0.56
    R = []
    for k in range(9):
        t = k / 8 * (math.pi / 2) * 1.15
        cy = y0 + bend * math.sin(min(t, math.pi / 2))
        cz = b.z - bend * (1 - math.cos(t))
        if t > math.pi / 2:
            cy = y0 + bend
            cz = b.z - bend - (t - math.pi / 2) * bend
        d = Vector((0, math.cos(min(t, math.pi / 2)), -math.sin(min(t, math.pi / 2))))
        side = Vector((1, 0, 0))
        up = side.cross(d)
        R.append([Vector((0, cy, cz)) + (side * math.cos(2 * math.pi * j / 8) + up * math.sin(2 * math.pi * j / 8)) * rc
                  for j in range(8)])
    R.insert(0, [p - Vector((0, 0.12, 0)) for p in R[0]])
    M.rings(R, CABLE, cap0=True, cap1=True)


def build(coll, sprite):
    mats = materials(sprite)
    M = Mesh()
    build_glass(M)
    build_socket(M)
    build_claws(M)
    build_plates(M)
    build_feed(M)
    bm = M.bm
    bm.normal_update()
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    # flat faces stay flat: sharp edges by angle, weighted normals (as usp_talon.finish/join)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj, mats


def bake_maps(obj, out_dir, nmats, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(1, nmats))  # the glass stays unbaked (smooth gloss; a UV seam showed as a ring)
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "orb199")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(obj, Path(tempfile.mkdtemp(prefix="newsha199_bake_")), len(mats))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=2000, smooth=6)
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
