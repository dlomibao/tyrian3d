"""newshk-195: the red energy orb of FLEET (3.6) as a two-part glossy shell with a glowing seam.

What it is (behaviour, tyrian-scratch/e3-enemies-1/behaviour.json and a probe of the running level):
five of these spawn 5 ticks apart at the yoke mid-boss's centre column (x 124, link 59) at ticks
1-25 and 3300-3310, as the yoke (assembly-newshk-237) spawns, and ride 8-10 px apart above its
hub: they ARE the yoke's segmented neck, a chain of energy balls (red in the level's first palette,
steel blue once it changes). Free-flying, nothing mounts one: a closed ball.

What the sprite shows (reference/models/newshk-195, 24x28, one frame, palette 5, red ramp 112-127):
- Plan: a round ball, the D74 inner mask cols 3-21 x rows 3-21 (19 px), centre pixel (12, 12),
  inside a closed 1 px ink ring (sprite_mask: 100% ink). The model's plan goes to the inner edge.
- Body: 112-116 with 112 the shadow side; median 113, 114 with the darkest shading left out (the
  rubric's rule). 114 is used: at 113 the game render read plum-grey (measured below).
- A white glint upper left (cols 7-11, rows 7-11): sheen on a glossy ball, not a part (art rule 2):
  a polished, clear-coated patch of the shell where the sprite draws it.
- A hot orange crescent hugging the lower-right rim (crest 118-122 at 8.5-9.3 px from the centre,
  flanks 116-117), from the right edge (row 12) round to the bottom (col 14).

Design: the crescent is the top-view arc of a glowing SEAM: the shell is a ball with a cap on its
lower-right underside (a small circle 58 deg round an axis pointing down and to the lower right),
and the energy inside shows through the seam between them. The seam's highest point is at plan
azimuth -45 deg, latitude 28 deg (8.5 px from the centre in plan, where the sprite's crest is); it
dips under the equator at azimuth -97 and +7 deg, the crescent's two horns; the rest of the ring
runs round the underside, out of the top view. Seen from the side it is a seam line, not a window
or a mouth (a crescent window cut on top read as a grin from the front: iter1/). The seam is a
chamfered groove (core 121, walls 120), with a hot rim either side (118 glowing, then 117 at half
glow) for the sprite's crest and flanks. The sphere is built round the seam's axis, so every band
edge is a grid row (exact circles, no stair-steps); the sheen patch edges are exact circles (plane
cuts). The underside is the plain ball.

Materials: satin-gloss dielectric shell (pal 114, roughness 0.56: at 0.36 the game's four lights
made four highlight lobes; part glow 0.35 for the energy inside
so the red stays saturated under the game's grey reflections), the sheen patch graded to
roughness 0.08 with a clear coat (one glint, upper left); glows metallic 1, rough 0.9 (D126/D173). No bake (a smooth ball
has no occlusion to speak of; no textures folder exists for this model). Outline shell D51/D90.

Run: blender --background --python assets/blender/enemies/newshk-195.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "newshk-195"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
D2R = math.pi / 180

# --- shape, sprite px: x = col + 0.5 - 12, y = 14 - (row + 0.5), z up -----------------------------
C0 = Vector((0.5, 1.5, 0.0))   # centre pixel (12, 12); z 0 like the current model
R = 9.62                       # ball radius: the inner mask (fitted: grid IoU 1.0)
NSEG = 64                      # segments round the seam axis

# The seam: a small circle round AXIS. Its plane tilts TILT deg from level toward the lower right;
# with D = cos(SEAM) its highest point is at latitude TILT - (90 - SEAM) on azimuth -45.
TILT = 60.0
SEAM = 58.0                    # angular radius of the cap, deg (horns at azimuth -97 / +7)
_az, _el = -45 * D2R, -(90 - TILT) * D2R
AXIS = Vector((math.cos(_el) * math.cos(_az), math.cos(_el) * math.sin(_az), math.sin(_el)))
# Bands either side of the seam (deg of arc from it): groove floor, groove wall, hot rim, glow spill.
FLOOR, WALLW, RIM, SPILL = 2.0, 3.0, 6.5, 10.0
DEPTH = 0.15                   # groove depth, px

# Sheen patch (unit direction): where the sprite draws its glint, col 9 row 9.
SHEEN_DIR = Vector(((9 + 0.5 - 12 - C0.x) / R, (14 - 9.5 - C0.y) / R, 0.0))
SHEEN_DIR.z = math.sqrt(1 - SHEEN_DIR.x ** 2 - SHEEN_DIR.y ** 2)
SHEEN_DIR.normalize()
# The patch is a smooth gradient, not rings (stepped rings read as a porthole): roughness and clear
# coat by angle from SHEEN_DIR, from a small texture on a "sheen" UV (u = angle / SHEEN_SPAN).
SHEEN_SPAN = 40.0              # deg covered by the texture's u
SHEEN_IN, SHEEN_OUT = 3.0, 20.0  # deg: fully polished inside, plain shell beyond
SHEEN_ROUGH, SHEEN_COAT = 0.07, 0.8
SHEEN_CUTS = (3, 6, 9, 12, 15, 18, 22)  # plane cuts round SHEEN_DIR, so the gradient has vertices to follow
SHELL_ROUGH = 0.62
SHELL_GLOW = 0.35
SHELL_SPEC = 0.22              # Specular IOR Level of the shell (0.5 = F0 0.04)

BODY, CORE, WALL, RIMM, SPILLM = range(5)


def smooth01(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lin(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def rows():
    """[(colatitude from AXIS deg, radial offset px, material of the band above)] pole to pole."""
    s = SEAM
    out = [(c, 0.0, BODY) for c in lin(3.0, s - SPILL - 4, 9)]
    out += [
        (s - SPILL, 0.0, SPILLM), (s - RIM, 0.0, RIMM), (s - WALLW, 0.0, WALL), (s - FLOOR, -DEPTH, CORE),
        (s, -DEPTH, CORE), (s + FLOOR, -DEPTH, WALL), (s + WALLW, 0.0, RIMM), (s + RIM, 0.0, SPILLM),
        (s + SPILL, 0.0, BODY),
    ]
    out += [(c, 0.0, BODY) for c in lin(s + SPILL + 4, 177.0, 18)]
    return out


def frame():
    e3 = AXIS.normalized()
    e1 = Vector((0, 0, 1)).cross(e3).normalized()
    e2 = e3.cross(e1).normalized()
    return e1, e2, e3


def point(colat, lon, off):
    e1, e2, e3 = frame()
    t, p = colat * D2R, lon * D2R
    n = e3 * math.cos(t) + (e1 * math.cos(p) + e2 * math.sin(p)) * math.sin(t)
    return C0 + n * (R + off)


def materials(sprite):
    pm = common.palette_material
    mats = [
        pm(sprite, 114, f"{NAME}_shell", metallic=0.0, roughness=SHELL_ROUGH, emission_strength=SHELL_GLOW),
        pm(sprite, 121, f"{NAME}_core", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pm(sprite, 120, f"{NAME}_wall", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pm(sprite, 118, f"{NAME}_rim", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pm(sprite, 117, f"{NAME}_spill", metallic=1.0, roughness=0.9, emission_strength=0.45),
    ]
    sheen_textures(mats[BODY])
    return mats


def sheen_textures(m):
    """Roughness (G of a metallic-roughness map, as usp_talon wires its bake) and clear-coat weight by
    angle from SHEEN_DIR, on the "sheen" UV. Packed into the .glb."""
    W = 128
    rm = bpy.data.images.new(f"{NAME}_sheen_rm", W, 2, alpha=False)
    coat = bpy.data.images.new(f"{NAME}_sheen_coat", W, 2, alpha=False)
    rpx, cpx = [], []
    for _ in range(2):
        for i in range(W):
            a = (i + 0.5) / W * SHEEN_SPAN
            k = 1 - smooth01(SHEEN_IN, SHEEN_OUT, a)
            rpx += [1.0, SHEEN_ROUGH + (SHELL_ROUGH - SHEEN_ROUGH) * (1 - k), 0.0, 1.0]
            w = SHEEN_COAT * (1 - smooth01(SHEEN_IN, SHEEN_OUT * 0.8, a))
            cpx += [w, w, w, 1.0]
    for img, px in ((rm, rpx), (coat, cpx)):
        img.colorspace_settings.name = "Non-Color"
        img.pixels[:] = px
        img.update()
        img.pack()
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = SHELL_SPEC
    bsdf.inputs["Coat Roughness"].default_value = 0.12
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "sheen"
    for img, outs in ((rm, ((1, "Roughness"), (2, "Metallic"))), (coat, ((0, "Coat Weight"),))):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.extension = "EXTEND"
        nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs[0])
        for ch, name in outs:
            nt.links.new(sep.outputs[ch], bsdf.inputs[name])


def build(coll, sprite):
    mats = materials(sprite)
    bm = bmesh.new()
    rs = rows()
    grid = [[bm.verts.new(point(c, 360.0 * i / NSEG, off)) for i in range(NSEG)] for c, off, _ in rs]
    for k in range(len(rs) - 1):
        m = rs[k][2]
        for i in range(NSEG):
            j = (i + 1) % NSEG
            f = bm.faces.new((grid[k][i], grid[k][j], grid[k + 1][j], grid[k + 1][i]))
            f.material_index = m
            f.smooth = m != WALL
    e3 = frame()[2]
    for pole, k in ((bm.verts.new(C0 + e3 * R), 0), (bm.verts.new(C0 - e3 * R), len(rs) - 1)):
        for i in range(NSEG):
            j = (i + 1) % NSEG
            f = bm.faces.new((grid[k][i], grid[k][j], pole))
            f.material_index = BODY
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Rings of vertices round SHEEN_DIR (plane cuts) for the sheen gradient, and its UV.
    for ang in SHEEN_CUTS:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=C0 + SHEEN_DIR * R * math.cos(ang * D2R),
                               plane_no=SHEEN_DIR)
    uv = bm.loops.layers.uv.new("sheen")
    for f in bm.faces:
        for lp in f.loops:
            a = math.degrees((lp.vert.co - C0).normalized().angle(SHEEN_DIR))
            lp[uv].uv = (min(0.995, max(0.005, a / SHEEN_SPAN)), 0.5)
    for v in bm.verts:
        v.co *= PX
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    return obj, mats


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    obj.data.calc_loop_triangles()
    print(f"{NAME}: {len(obj.data.polygons)} faces, {len(obj.data.loop_triangles)} triangles")
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=1500, smooth=8, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    lib.preview([obj, shell], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
