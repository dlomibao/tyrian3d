"""Satellite Marlo (sidekick option 30, tyrian.shp#8 frame 152): a 3D version of its sprite to
the player-ship hard-surface standard (DECISIONS D50-D53, D65, D74; D120/D122: model what it is).

What it is: the cheapest E1 sidekick, an orbiting satellite (style 4: it circles the ship at 20 px).
A ball of red plasma held in a small dark-metal containment cradle, always moving round the ship.

What the sprite shows (reference/models/sidekick-satellite-marlo, 12x14, palette 5):
- an 8 px round blob, rows 2-9, cols 2-9; its ring of 112/113 is the ink border (sprite_mask: 95 %
  ink), left to the game's own outline (D74), so the model's top view covers the 33 px inner mask:
  a disc of radius 3.2 px about column edge 6, row edge 6;
- inside it red plasma, the sprite's ramp 115-125: a yellow hot spot (125) at the lower right, an
  orange swirl (122) just left of the centre, a bright orange crescent (119-120) along the upper-left
  edge with a dark streak (112) inside it, darker red towards the rim. A self-lit plasma, so this is
  the plasma's own colour, not lighting; median of the inside pixels: 118.

Design: the orb is one smooth sphere (radius 3.2 px) glowing with the sprite's heat field: each inside
pixel's place on the plasma ramp at its direction seen from above, Gaussian-smoothed over the sphere
(back-fitted so the smoothed field passes through the pixel values), soft noise swirls on top, dark
red towards the rim; a lat-long emission texture over pal_125 (no lighting baked in: plasma is
self-lit, so its swirl is its colour, not shading). It sits in a dark machined
cradle that stays under the orb's silhouette, so from above the model is the sprite and from the
tilted camera the orb visibly sits in a mount:
- a containment collar just below the equator: a chamfered ring whose outer face carries a modelled
  panel groove and eight hex bolts, its lip 0.1 px proud of the orb;
- four clamp jaws at the diagonals rising from the collar up the orb's flank, each with a recessed
  pad line;
- a pchip bowl under the collar with eight radial cooling fins;
- a hub flange and a short stub at the bottom (underside: plain and closed).
Colours: collar, jaws and fins 113 and the bowl 112 (the sprite's dark ring colours), satin metal;
the orb pal_125 glowing (emission 0.9) through the heat texture.

Run: tools/build-models.sh assets/blender/sidekicks/satellite-marlo.py (exports public/models/sidekicks/satellite-marlo.glb
and src/render/spriteModels/satellite-marlo.json). Extra: -- [--nobake] [--renders DIR] writes review renders to DIR.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector, noise

WT = Path(__file__).resolve().parents[3]  # repository root
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip, frange  # noqa: E402

NAME = "satellite-marlo"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
FRAME = 152

# Sprite px: x = column edge - 6, y = row edge (down), z up. The orb's centre: column edge 6, row edge 6.
CY = 6.0
R = 3.2          # orb radius (fits the 33 px inner mask: grid IoU 32/33, the missing one is (8,8))
ZC = 0.8         # orb centre height
N = 48           # segments round the cradle

# Material slots (cradle part).
COLLAR, BOWL, JAW, FIN, BOLT, PAD = range(6)


def rs(z):
    """The orb's radius at height z."""
    return math.sqrt(max(0.0, R * R - (z - ZC) ** 2))


# --- the plasma heat field (from the D49 script, retuned): 0 dark red (113) .. 1 yellow (125) over
# directions n from the orb's centre, in model axes (x right, y forward = up the screen, z up).
HOT = Vector((0.47, -0.47, 0.75)).normalized()  # px (7.5, 7.5), the 125 pixel: the swirls curl round it
RAMP = (113, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def swirl(n, scale, seed):
    q = Quaternion(HOT, 2.2 * n.dot(HOT)) @ n
    return noise.noise(q * scale + Vector((seed, seed * 0.7, -seed * 1.3)))


# The sprite's own plasma, read as a heat value per inside pixel (its place on RAMP, 112 below the
# ramp's start: the dark streak), at that pixel's direction on the orb seen from straight above.
SPRITE_HEAT = []


def sprite_heat(sprite):
    fr = sprite["frames"][0]
    rows = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in fr["pixels"]]
    inner = ["............", "............", "............", "....####....", "...######...", "...######...",
             "...######...", "...######...", "....#####...", "............"]  # sprite_mask's inner mask
    SPRITE_HEAT.clear()
    for r, line in enumerate(inner):
        for c, ch in enumerate(line):
            if ch != "#":
                continue
            i = rows[r][c]
            h = -0.12 if i == 112 else RAMP.index(i) / (len(RAMP) - 1)
            dx, dy = (c + 0.5 - 6) / R, (CY - (r + 0.5)) / R
            dz = math.sqrt(max(0.0, 1 - dx * dx - dy * dy))
            SPRITE_HEAT.append((Vector((dx, dy, dz)).normalized(), h))
    # Back-fit: the Gaussian smoothing flattens the peaks (125 read as 123); nudge each sample's value
    # until the smoothed field passes through the sprite's own values at the pixel centres.
    targets = [h for _, h in SPRITE_HEAT]
    for _ in range(6):
        outs = [smooth_heat(p) for p, _ in SPRITE_HEAT]
        SPRITE_HEAT[:] = [(p, h + 0.8 * (t - o)) for (p, h), t, o in zip(SPRITE_HEAT, targets, outs)]


def smooth_heat(n, sigma=0.16):
    ws = hs = 0.0
    for p, h in SPRITE_HEAT:
        w = math.exp(-(n - p).length_squared / (2 * sigma * sigma))
        ws += w
        hs += w * h
    return hs / ws if ws > 1e-9 else 0.2


def heat(n, sigma=0.16):
    """Smooth (Gaussian-weighted) the sprite's pixel heats over the upper hemisphere, soft swirling
    streaks on top, darkening to dark red towards the rim and under it (the cradle hides that)."""
    h = smooth_heat(n, sigma)
    h += 0.05 * swirl(n, 2.6, 3.0) + 0.02 * swirl(n, 5.0, 9.0)
    rim = smoothstep(-0.1, 0.35, n.z)
    h = h * rim + (0.18 + 0.06 * swirl(n, 2.0, 5.0)) * (1 - rim)
    return max(0.0, min(1.0, h))


def enc(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def ramp_colour(sprite, h):
    ramp = [common.srgb(*sprite["colors"][str(i)]) for i in RAMP]
    x = h * (len(ramp) - 1)
    k = min(int(x), len(ramp) - 2)
    t = x - k
    return [ramp[k][c] + (ramp[k + 1][c] - ramp[k][c]) * t for c in range(3)]


def plasma_image(sprite, name, scale, W=256, H=128):
    """The heat field as a lat-long texture (u round Z, v up from the bottom pole), stored as the
    wanted colour over palette colour 125's (the material colour multiplies it back), times scale."""
    base = common.srgb(*sprite["colors"]["125"])
    img = bpy.data.images.get(name) or bpy.data.images.new(name, W, H, alpha=False)
    px = [0.0] * (W * H * 4)
    for y in range(H):
        th = math.pi * (y + 0.5) / H
        for x in range(W):
            ph = 2 * math.pi * (x + 0.5) / W
            c = ramp_colour(sprite, heat(Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))))
            o = 4 * (y * W + x)
            px[o:o + 4] = [enc(scale * c[k] / base[k]) for k in range(3)] + [1.0]
    img.pixels = px
    img.pack()
    return img, H


def build_orb(sprite, coll, lon=40, lat=20):
    plasma = common.palette_material(sprite, 125, f"sm_plasma", metallic=0.0, roughness=0.3, emission_strength=0.9)
    glow_img, H = plasma_image(sprite, "sm_plasma_glow", 1.0)
    base_img, _ = plasma_image(sprite, "sm_plasma_base", 0.5)
    base = common.srgb(*sprite["colors"]["125"])
    nt = plasma.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    for img, sock in ((base_img, "Base Color"), (glow_img, "Emission Color")):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = (*base, 1.0)
        nt.links.new(mul.outputs[2], bsdf.inputs[sock])
    plasma["tyrian_base_rgb"] = list(base)

    bm = bmesh.new()
    centre = Vector((0.0, (7 - CY) * PX, ZC * PX))
    rad = R * PX
    pole_v = 0.5 / H
    rings = [[bm.verts.new(centre + rad * Vector((math.sin(math.pi * j / lat) * math.cos(2 * math.pi * i / lon),
                                                 math.sin(math.pi * j / lat) * math.sin(2 * math.pi * i / lon),
                                                 -math.cos(math.pi * j / lat))))
              for i in range(lon)] for j in range(1, lat)]
    south = bm.verts.new(centre + Vector((0, 0, -rad)))
    north = bm.verts.new(centre + Vector((0, 0, rad)))
    uv = bm.loops.layers.uv.new("UVMap")
    faces = []
    for i in range(lon):
        i1 = (i + 1) % lon
        u0, u1, um = i / lon, (i + 1) / lon, (i + 0.5) / lon
        faces.append((bm.faces.new((south, rings[0][i1], rings[0][i])), [(um, pole_v), (u1, 1 / lat), (u0, 1 / lat)]))
        for j in range(lat - 2):
            v0, v1 = (j + 1) / lat, (j + 2) / lat
            faces.append((bm.faces.new((rings[j][i], rings[j][i1], rings[j + 1][i1], rings[j + 1][i])),
                          [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]))
        faces.append((bm.faces.new((north, rings[-1][i], rings[-1][i1])), [(um, 1 - pole_v), (u0, (lat - 1) / lat), (u1, (lat - 1) / lat)]))
    for f, uvs in faces:
        for loop, c in zip(f.loops, uvs):
            loop[uv].uv = c
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}-orb")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(plasma)
    me.shade_smooth()
    obj = bpy.data.objects.new(f"{NAME}-orb", me)
    coll.objects.link(obj)
    return obj


# --- the cradle (sprite px) ---------------------------------------------------------------------

def revolve(part, prof, n=N, phase=0.0):
    """A solid of revolution round the vertical axis through (0, CY). prof = [(r, z, mat)] along the
    surface; mat colours the segment to the next point. Faces oriented by the profile's normal,
    taken as pointing to the right of the walk (walk top-down on the outside)."""
    def ring(r, z):
        if r <= 1e-6:
            return [part.v((0.0, CY, z))]
        return [part.v((r * math.cos(phase + 2 * math.pi * i / n), CY + r * math.sin(phase + 2 * math.pi * i / n), z))
                for i in range(n)]
    rings = [ring(r, z) for r, z, _ in prof]
    for k in range(len(prof) - 1):
        (r0, z0, m), (r1, z1, _) = prof[k], prof[k + 1]
        nr, nz = (z0 - z1), (r1 - r0)  # outward normal for a walk going down the outside
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = phase + 2 * math.pi * (i + 0.5) / n
            out = (nr * math.cos(ang), nr * math.sin(ang), nz)
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)


Z_CT = -0.25           # collar top (orb radius there 2.99)
Z_CB = -1.55           # collar bottom
R_C = 3.02             # collar outer face (hidden under the orb's 3.2 silhouette from above)
Z_HUB = -3.05


def cradle_profile():
    P = []
    # Collar: inner edge tucked inside the orb, top face, chamfer, outer face with a groove, chamfer.
    P += [(2.5, Z_CT, COLLAR), (2.98, Z_CT, COLLAR), (R_C, Z_CT - 0.12, COLLAR), (R_C, -0.82, COLLAR),
          (R_C - 0.1, -0.86, COLLAR), (R_C - 0.1, -0.96, COLLAR), (R_C, -1.0, COLLAR),
          (R_C, Z_CB + 0.13, COLLAR), (R_C - 0.13, Z_CB, COLLAR), (2.72, Z_CB, BOWL)]
    # Bowl: a pchip curve in to the hub.
    zs = [Z_CB, -1.9, -2.3, -2.7, Z_HUB + 0.05]
    rr = [2.72, 2.62, 2.32, 1.85, 1.5]
    f = pchip([-z for z in zs], rr)
    for z in frange(Z_CB - 0.12, Z_HUB + 0.05, 0.18)[:-1]:
        P.append((f(-z), z, BOWL))
    # Hub flange (a chamfered step ring), the stub and its flat bottom.
    P += [(1.5, Z_HUB + 0.05, BOWL), (1.72, Z_HUB, COLLAR), (1.72, Z_HUB - 0.28, COLLAR),
          (1.55, Z_HUB - 0.4, COLLAR), (1.05, Z_HUB - 0.4, BOWL), (1.0, Z_HUB - 0.85, BOWL),
          (0.82, Z_HUB - 0.98, BOWL), (0.0, Z_HUB - 0.98, BOWL)]
    return P


def build_cradle(part):
    revolve(part, cradle_profile(), phase=math.pi / N)
    # Inner lining under the orb (closes the collar's inner edge to the bowl).
    # Eight hex bolts on the collar's outer face, between the jaws and fins.
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for i in range(6):
            t = 2 * math.pi * i / 6
            u, w = 0.15 * math.cos(t), 0.15 * math.sin(t)
            for d, s in ((-0.05, 1.0), (0.08, 1.0), (0.12, 0.7)):
                r = R_C + d
                pts.append((r * ca - s * u * sa, CY + r * sa + s * u * ca, -1.25 + s * w))
        hull(part, pts, BOLT)
    # Four clamp jaws at the diagonals: a curved plate hugging the orb's flank from the collar top up
    # to just below the equator, its outer face inside the orb's top-view silhouette.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        hw = 0.5  # half width (px) along the tangent
        z0, z1 = Z_CT - 0.05, ZC - 0.7
        ring_pts = []
        for z in (z0, (z0 + z1) / 2, z1):
            ri = rs(z) - 0.15
            ro = min(rs(z) + 0.16, 3.16) if z > z0 else R_C - 0.02
            for r in (ri, ro):
                for s in (-hw, hw):
                    sh = 0.0 if r == ri else 0.06 * (1 if s < 0 else -1)
                    ss = s + sh
                    ring_pts.append((r * math.cos(a) - ss * math.sin(a), CY + r * math.sin(a) + ss * math.cos(a), z))
        # top bevel
        zt = z1 + 0.12
        rt = rs(zt) - 0.05
        for s in (-hw + 0.08, hw - 0.08):
            ring_pts.append((rt * math.cos(a) - s * math.sin(a), CY + rt * math.sin(a) + s * math.cos(a), zt))
        hull(part, ring_pts, JAW)
        # A dark rubber pad line across the jaw's face (a recess read as a seam).
        zp = (z0 + z1) / 2 + 0.05
        rp = min(rs(zp) + 0.16, 3.16) + 0.02
        pad = []
        for s in (-hw + 0.06, hw - 0.06):
            for dz in (-0.05, 0.05):
                for dr in (-0.06, 0.0):
                    r = rp + dr
                    pad.append((r * math.cos(a) - s * math.sin(a), CY + r * math.sin(a) + s * math.cos(a), zp + dz))
        hull(part, pad, PAD)
    # Eight radial cooling fins on the bowl.
    f_out = pchip([1.55, 1.9, 2.3, 2.7, 3.0], [2.72, 2.62, 2.32, 1.85, 1.5])
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8 + math.pi / 8
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for z, ext in ((Z_CB - 0.02, 0.0), (-1.85, 0.32), (-2.35, 0.36), (-2.75, 0.25), (Z_HUB + 0.02, 0.05)):
            r_in = f_out(-z) - 0.25
            r_out = f_out(-z) + ext
            for r in (r_in, r_out):
                for s in (-0.1, 0.1):
                    ss = s * (0.6 if r == r_out and ext > 0 else 1.0)
                    pts.append((r * ca - ss * sa, CY + r * sa + ss * ca, z))
        hull(part, pts, FIN)


def materials(sprite):
    def steel(i, tag, rough=0.42, metal=0.6):
        return common.palette_material(sprite, i, f"sm_{tag}", metallic=metal, roughness=rough)
    return [steel(113, "collar", 0.32, 0.7), steel(112, "bowl", 0.38, 0.7), steel(113, "jaw", 0.3, 0.7),
            steel(113, "fin", 0.34, 0.7), steel(113, "bolt", 0.28, 0.75), steel(112, "pad", 0.7, 0.1)]


def finish(part, mats, coll):
    """Sprite px to Blender for a 12x14 sprite: X = x / 12, Y = (7 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


# --- bake (from charge-cannon A / newshm-117: AO/roughness only) ----------------------------------

def bake_maps(obj, out_dir, tag, size=512, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(24), island_margin=0.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list({m.name: m for m in me.materials}.values())
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.012
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.05
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- renders -----------------------------------------------------------------------------------

def camera(scene, name, location, look_at, ortho=None, lens=50, up="Y"):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = location
    direction = Vector(look_at) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", up).to_euler()
    return cam


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [e for e in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if e.isupper()]
        key = "WORKBENCH" if "WORKBENCH" in want else "EEVEE"
        scene.render.engine = next(e for e in names if key in e)


def render_top_mask(scene, out):
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 12 * 16, 14 * 16
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    cam = camera(scene, "sm_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.filepath = str(out / f"top_{FRAME}.png")
    bpy.ops.render.render(write_still=True)
    return cam


def render_top_colour(scene, cam, out):
    """The orb's own glow seen from straight above, unlit (for the per-pixel colour check)."""
    set_engine(scene, "BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    for o in scene.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[1].default_value = 0.0
    plasma = bpy.data.materials.get("pal_125_sm_plasma")
    bsdf = next(n for n in plasma.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    keep = bsdf.inputs["Emission Strength"].default_value
    bsdf.inputs["Emission Strength"].default_value = 1.0
    scene.camera = cam
    scene.render.filepath = str(out / f"topcol_{FRAME}.png")
    bpy.ops.render.render(write_still=True)
    bsdf.inputs["Emission Strength"].default_value = keep


def render_views(scene, out):
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.09, 0.095, 0.11, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("sm_sun", bpy.data.lights.new("sm_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (Vector((0.45, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("sm_fill", bpy.data.lights.new("sm_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = (Vector((-0.6, 0.6, -0.3))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D = 3.0
    ext = 0.78
    zc = -0.6 * PX
    t15, t32 = math.radians(15), math.radians(32)
    c0 = (0, PX, zc)
    views = {
        "top": camera(scene, "v_top", (0, PX, D), c0, ortho=ext),
        "side": camera(scene, "v_side", (D, PX, zc), c0, ortho=ext, up="Y"),
        "front": camera(scene, "v_front", (0, D, zc), c0, ortho=ext, up="Y"),
        "rear": camera(scene, "v_rear", (0, -D, zc), c0, ortho=ext, up="Y"),
        "q34": camera(scene, "v_q34", (1.3, 1.1, 1.05), c0, lens=80, up="Y"),
        "q34r": camera(scene, "v_q34r", (-1.3, -1.2, 0.9), c0, lens=80, up="Y"),
        "game15": camera(scene, "v_game15", (0, PX - 2.5 * math.sin(t15), 2.5 * math.cos(t15)), c0, lens=80),
        "game32": camera(scene, "v_game32", (0, PX - 2.5 * math.sin(t32), 2.5 * math.cos(t32)), c0, lens=80),
        "under": camera(scene, "v_under", (0, PX, -D), c0, ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for k, cam in views.items():
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{k}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rdir = Path(argv[argv.index("--renders") + 1]) if "--renders" in argv else None
    bake = "--nobake" not in argv
    if rdir:
        renders = rdir / "renders"
        renders.mkdir(parents=True, exist_ok=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection("satellite_marlo_A")
    sprite = common.load_sprite(WT, REF)
    sprite_heat(sprite)
    orb = build_orb(sprite, coll)
    mats = materials(sprite)
    P = Part(f"{NAME}-cradle", smooth_angle=32.0)
    build_cradle(P)
    cradle = finish(P, mats, coll)
    # Outline shell from the orb and cradle together (one clean contour, D51).
    tmp_me = orb.data.copy()
    tmp = bpy.data.objects.new("sm_join", tmp_me)
    coll.objects.link(tmp)
    c2 = bpy.data.objects.new("sm_join2", cradle.data.copy())
    coll.objects.link(c2)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    tmp.select_set(True)
    c2.select_set(True)
    bpy.context.view_layer.objects.active = tmp
    bpy.ops.object.join()
    shell = common.outline_shell(tmp, coll, voxel=0.008, faces=900, smooth=6, inside=0.003)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(tmp, do_unlink=True)
    T.cull_hidden(cradle)
    if bake:
        shell.hide_render = True
        bake_maps(cradle, tempfile.mkdtemp(prefix="sm_bake_"), "satellite_marlo")
    objs = [orb, cradle, shell]
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris)
    common.export_sprite_model(WT, objs, "sidekicks/satellite-marlo", sprite["sprites"],
                               image_format="WEBP" if bake else "AUTO")
    if not rdir:
        return
    shell.hide_render = True
    cam = render_top_mask(scene, renders)
    render_top_colour(scene, cam, renders)
    render_views(scene, renders)
    (renders / "stats.json").write_text(json.dumps({"triangles": tris}, indent=1))


main()
