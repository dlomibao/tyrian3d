"""Satellite Marlo (sidekick 30, tyrian.shp#8 frame 152): a 3D version of its sprite.

The cheapest sidekick of the first shop: a tiny glowing orb 8 px across, drawn as a ball of red
plasma with a dark-red rim, swirling from dark red at the upper left to orange and a yellow hot
spot at the lower right. As a small machine it is a plasma ball held in a dark metal satellite
cradle:

- The orb: one smooth sphere, 6.9 px across, coloured by a smooth heat field (a texture over the
  sprite's plasma shades, dark red 113 to yellow 125, glowing): a yellow hot spot at the lower
  right, red to red-orange elsewhere with soft swirling streaks, an orange swirl just left of the
  centre, a bright orange crescent at the upper-left edge with a dark red patch inside it (the
  sprite's dark streak), and dark red towards the rim. No per-face shades, no holes.
- The rim: a thin collar of dark metal (index 112) just below the orb's equator, 7.5 px across
  (the game draws its own outline), with four low clamp pads on its top inside its outline.
- The cradle: a shallow faceted dark bowl under the collar (index 113), ending in a short
  stub at the bottom, so from the side the orb sits in a mechanical mount rather than floating
  as a bare ball. It is under the collar, so the top view is the sprite.

Run: blender --background --python assets/blender/sidekicks/satellite-marlo.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Quaternion, Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-satellite-marlo"
MODEL = "sidekicks/satellite-marlo"
P = 1 / 12  # one sprite pixel
CX, CY = 6.0, 6.0  # the orb's centre in sprite px (column edge 6, row edge 6)
OX, OY = (CX - 6) * P, (7 - CY) * P  # in units: the 12x14 block is centred on the origin
R_ORB = 3.45 * P  # plasma ball radius (the outer shell)
R_RIM_OUT = 3.75 * P  # collar outer radius: a thin dark lip round the ball (the game adds its outline)
R_RIM_IN = 3.15 * P  # collar inner radius (tucked inside the ball)
RIM_H = 1.1 * P  # collar height
ORB_Z = 0.6 * P  # the ball's centre height above the model origin
RIM_Z = ORB_Z - 1.0 * P  # the collar sits a little below the ball's equator


def enc(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def plasma_sphere(bm, centre, radius, lon=64, lat=32, pole_v=0.0):
    """A lat-long sphere about Z with its own UVs (u round, v up): one shared vertex per point,
    so it shades smoothly, and per-corner UVs that run 0..1 across the seam. The poles' UVs stop
    `pole_v` short of the texture's edges, so a repeating sampler never blends in the other pole."""
    rings = [[bm.verts.new(centre + radius * Vector((math.sin(math.pi * j / lat) * math.cos(2 * math.pi * i / lon),
                                                    math.sin(math.pi * j / lat) * math.sin(2 * math.pi * i / lon),
                                                    -math.cos(math.pi * j / lat))))
              for i in range(lon)] for j in range(1, lat)]
    south = bm.verts.new(centre + Vector((0, 0, -radius)))
    north = bm.verts.new(centre + Vector((0, 0, radius)))
    uv = bm.loops.layers.uv.new("UVMap")
    faces = []
    for i in range(lon):
        i1 = (i + 1) % lon
        u0, u1, um = i / lon, (i + 1) / lon, (i + 0.5) / lon
        f = bm.faces.new((south, rings[0][i1], rings[0][i]))
        faces.append((f, [(um, pole_v), (u1, 1 / lat), (u0, 1 / lat)]))
        for j in range(lat - 2):
            v0, v1 = (j + 1) / lat, (j + 2) / lat
            f = bm.faces.new((rings[j][i], rings[j][i1], rings[j + 1][i1], rings[j + 1][i]))
            faces.append((f, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]))
        f = bm.faces.new((north, rings[-1][i], rings[-1][i1]))
        faces.append((f, [(um, 1.0 - pole_v), (u0, (lat - 1) / lat), (u1, (lat - 1) / lat)]))
    for f, uvs in faces:
        for loop, c in zip(f.loops, uvs):
            loop[uv].uv = c


# --- The plasma's heat field: 0 (dark red, 113) to 1 (yellow, 125) over directions n from the orb's
# centre. It follows the sprite: a yellow hot spot at the lower right, mostly facing up; a red to
# red-orange middle with an orange swirl just left of centre; a bright orange crescent along the
# upper-left edge with a dark red patch inside it; dark red towards the rim. Smooth mathutils noise
# twisted round the hot axis adds soft swirling streaks. Everything is smooth in n, so the colour is.
HOT = Vector((0.43, -0.43, 0.79)).normalized()  # sprite px (7.5, 7.5): the yellow pixel
CRESCENT = Vector((-0.6, 0.55, 0.58)).normalized()  # the orange arc at the upper-left edge
DARK_SPOT = Vector((-0.4, 0.4, 0.82)).normalized()  # the dark pixel just inside it (col 4, row 4)
MID = Vector((-0.12, 0.12, 0.98)).normalized()  # the orange pixel just left of centre (122)
RAMP = (113, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125)  # the sprite's plasma shades, dark to hot


def swirl(n, scale, seed):
    """Noise sampled along n twisted round the hot axis: streaks that curl round the hot spot."""
    q = Quaternion(HOT, 2.2 * n.dot(HOT)) @ n
    return noise.noise(q * scale + Vector((seed, seed * 0.7, -seed * 1.3)))


def blob(n, d, width):
    return math.exp(-((1 - n.dot(d)) / width) ** 2)


def heat(n):
    g = 0.5 + 0.5 * n.dot(HOT)  # 1 at the hot spot, 0 opposite
    h = 0.2 + 0.8 * g ** 11
    h += 0.09 * swirl(n, 2.4, 3.0) + 0.025 * swirl(n, 4.5, 9.0)
    h += 0.25 * blob(n, MID, 0.05)
    h += 0.36 * math.exp(-((n.dot(CRESCENT) - 0.9) / 0.07) ** 2) * smoothstep(0.1, 0.45, n.z)
    h -= 0.3 * blob(n, DARK_SPOT, 0.04)
    h -= 0.22 * (1 - smoothstep(0.1, 0.55, n.z))  # dark red towards the rim
    return max(0.0, min(1.0, h))


def plasma_image(sprite, name, scale, W=256, H=128):
    """The heat field as a lat-long texture (u round Z, v from the bottom pole up), stored as the
    wanted colour divided by palette colour 125's (the material's own colour multiplies it back),
    times `scale`."""
    ramp = [common.srgb(*sprite["colors"][str(i)]) for i in RAMP]
    base = common.srgb(*sprite["colors"]["125"])

    def colour(h):
        x = h * (len(ramp) - 1)
        k = min(int(x), len(ramp) - 2)
        t = x - k
        return [ramp[k][c] + (ramp[k + 1][c] - ramp[k][c]) * t for c in range(3)]

    img = bpy.data.images.get(name) or bpy.data.images.new(name, W, H, alpha=False)
    if tuple(img.size) != (W, H):
        img.scale(W, H)
    px = [0.0] * (W * H * 4)
    for y in range(H):
        th = math.pi * (y + 0.5) / H
        for x in range(W):
            ph = 2 * math.pi * (x + 0.5) / W
            c = colour(heat(Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))))
            o = 4 * (y * W + x)
            px[o:o + 4] = [enc(scale * c[k] / base[k]) for k in range(3)] + [1.0]
    img.pixels = px
    img.pack()
    return img, H


def build(sprite):
    coll = common.reset_collection(NAME)
    DARK, SHADE = 1, 2
    plasma = common.palette_material(sprite, 125, f"{NAME}-plasma", metallic=0.0, roughness=0.3, emission_strength=1.0)
    mats = [plasma,
            common.palette_material(sprite, 112, NAME, metallic=0.8, roughness=0.35),
            common.palette_material(sprite, 113, NAME, metallic=0.8, roughness=0.4)]

    # --- The plasma orb: one smooth sphere coloured by the heat field through smooth textures over
    # the sprite's plasma ramp, never per-face shades. The material is palette colour 125 (the
    # brightest) times a texture: Emission = the full heat colour, so it glows like the sprite;
    # Base Color = the same at half strength, so lighting adds sheen without washing it out. In
    # game the live palette still drives it (the game sets the colour and emissive from index 125).
    glow_img, H = plasma_image(sprite, f"{NAME}-plasma-glow", 1.0)
    base_img, _ = plasma_image(sprite, f"{NAME}-plasma-base", 0.5)
    base = common.srgb(*sprite["colors"]["125"])
    nt = plasma.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for img, sock in ((base_img, "Base Color"), (glow_img, "Emission Color")):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = (*base, 1.0)
        nt.links.new(mul.outputs[2], bsdf.inputs[sock])

    bm = bmesh.new()
    plasma_sphere(bm, Vector((OX, OY, ORB_Z)), R_ORB, pole_v=0.5 / H)
    orb = common.mesh_object(f"{NAME}-orb", bm, mats, coll, smooth=True)

    # --- The collar: a hard ring with a rectangular, bevelled section round the orb's equator.
    bm = bmesh.new()
    seg = 32
    # Section (radius, z) points going round the profile: inner bottom, outer bottom (bevelled),
    # outer top (bevelled), inner top.
    b = 0.3 * P
    zb, zt = RIM_Z - RIM_H * 0.5, RIM_Z + RIM_H * 0.5
    prof = [(R_RIM_IN, zb), (R_RIM_OUT - b, zb), (R_RIM_OUT, zb + b), (R_RIM_OUT, zt - b),
            (R_RIM_OUT - b, zt), (R_RIM_IN, zt)]
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((OX + r * ca, OY + r * sa, z)) for r, z in prof])
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for k in range(len(prof)):
            k1 = (k + 1) % len(prof)
            bm.faces.new((r0[k], r1[k], r1[k1], r0[k1])).material_index = DARK

    # Four clamp blocks on the collar at the diagonals, bridging collar and ball.
    for i in range(4):
        a = math.radians(45 + 90 * i)
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        r0, r1 = R_RIM_IN + 0.15 * P, R_RIM_OUT - 0.1 * P  # inside the collar's outline
        hw = 0.45 * P
        z0, z1 = zt - 0.1 * P, zt + 0.3 * P  # low pads on the collar's top
        centre = Vector((OX, OY, 0))
        corners = []
        for r in (r0, r1):
            for s in (-hw, hw):
                p = centre + d * r + t * s
                corners.append((p.x, p.y))
        # outline in XY counter-clockwise: inner-left, outer-left, outer-right, inner-right
        ccw = [corners[0], corners[2], corners[3], corners[1]]
        common.slab(bm, ccw, z1 - z0, z=(z0 + z1) / 2, mat_index=SHADE)
    collar = common.mesh_object(f"{NAME}-collar", bm, mats, coll, smooth=False)

    # --- The cradle: a faceted bowl under the collar ending in a short stub.
    bm = bmesh.new()
    sections = [  # (z, radius)
        (zb, R_RIM_OUT - 0.4 * P),
        (zb - 0.7 * P, 3.2 * P),
        (zb - 1.4 * P, 2.3 * P),
        (zb - 1.8 * P, 1.2 * P),
        (zb - 2.5 * P, 0.9 * P),
        (zb - 2.7 * P, 0.6 * P),
    ]
    sides = 12
    rings = []
    for z, r in sections:
        rings.append([bm.verts.new((OX + r * math.cos(2 * math.pi * (i + 0.5) / sides),
                                    OY + r * math.sin(2 * math.pi * (i + 0.5) / sides), z)) for i in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = SHADE
    bm.faces.new(list(reversed(rings[-1]))).material_index = SHADE
    bm.faces.new(rings[0]).material_index = SHADE
    cradle = common.mesh_object(f"{NAME}-cradle", bm, mats, coll, smooth=False)

    return [orb, collar, cradle]


if __name__ == "__main__":
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    objects = build(sprite)
    common.export_sprite_model(root, objects, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / NAME / frame["image"]
        common.render_preview(objects, out, ref, size=frame["size"])
