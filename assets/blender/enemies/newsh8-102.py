"""Red egg stone (newsh8.shp frame 102): a smooth, glossy egg lying on the ground.

Seen in episode 3 (IXMUCANE, SAWBLADES; tools/enemy_behaviour.mjs, D178): the red rockets
(assembly-newsh8-125 lying, -191 standing) drop it behind them every 10 / 30 ticks and it stays where
it falls (still, armour 20, no guns). Its sprite (12x14 px) is one smooth egg lit from the upper left:
the near-white glint at the upper left, the dark lower limb, a lighter crescent of reflected light round
the lower right. No breaks, no facets: D178's facet ramp read as cut gems in game (E3 QA L2), and the
user approved a smooth glossy egg.

An egg lying on its side, its widest girth a faired egg curve fitted to the sprite's inner mask (inside
the ink ring, D74), a full round crown (a stone egg, not a dome), the lower half tucked in under the
girth to a small flat contact patch (underside: a plausible closed shape only). One palette material,
the sprite's own median index (pal_69), no painted shading (art rule 2): the game's lights make the
glint and the dark limb on a glossy, smooth-shaded dielectric surface. The crown peaks toward the upper
left, where the sprite draws its glint, so the surface there faces the game's sun and room light. Two
generated finish maps (no colour) make the glint sheen where the sprite draws it: roughness, and the
dielectric's reflectance (F0, through Specular Tint and Specular IOR Level, D176), polished at the upper
left and along a narrow band of the lower-right limb, where the game's room light catches the sprite's
light crescent; elsewhere the stone stays low-reflectance, so its dark limb stays dark. D90's outline
shell from a sealed copy (D51). Its own body: only lib_newshd_rock's Grid (the sprite grid) and
radius_at are used, the facet ramp is not.

Run: blender --background --python assets/blender/enemies/newsh8-102.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402  (Grid and radius_at only)

NAME = "newsh8-102"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

PX = 1 / 12
SPEC = {
    "mid": 69,           # the sprite's median index inside its ink ring (trimmed median 69)
    "metallic": 0.0,
    "roughness": 0.45,   # the stone away from the glint: satin, so the room light doesn't wash it pink
    "specular": 4.0,     # Specular IOR Level (D176) with the reflectance map below as Specular Tint: F0
                         # 0.04 * 2 * 4 * map, 0.32 on the glint, 0.016 on the rest of the stone
    "crown": 5.0,        # crown height above the girth, sprite px (the half width is 5.4: a stone egg)
    "girth": 2.6,        # girth height above the ground, px: a whole egg lying on its side, not a dome
    "belly": 2.9,        # depth of the lower half below the girth, px (clamped flat at the ground)
    # The girth: a faired egg curve fitted to the inner mask (a fit of the curve below: best grid IoU, then the
    # fine IoU), not the pixel staircase traced (that gave a lumpy, boxy pebble): centre (sprite px), half
    # width, half length, superellipse exponent (2 = an ellipse) and the egg term (the half width grows
    # by this share toward the blunt upper end).
    "egg": {"cu": 6.0, "cv": 7.0, "a": 5.4, "b": 6.2, "n": 2.2, "e": 0.04},
    # The crown's peak, offset toward the sprite's glint (x right, y up, a share of the girth's half
    # width / length; length <= 0.5 keeps the warp inside the girth, so the outline doesn't change). A
    # centred crown put the game's glint in the middle of the egg (fix round 1).
    "apex": (-0.3, 0.4),
    "subdiv": 4,         # 1,280 triangles: smooth at the 12x14 px this shows, and the rockets drop dozens
    # The glint (art rule 2: sheen, not paint): one palette index everywhere, but the stone is polished
    # and reflective where the sprite draws its pink-to-white highlight (the 79s round sprite px 4.5, 4.5;
    # the centre sits a little higher, as the tilted camera sees the crown) and satin, low-reflectance
    # elsewhere. Gaussian falloffs of these radii (top-view sprite px): roughness "roughness" ->
    # "rough_min" (radius "rough_r"); the reflectance map "base" -> 1 (radius "spec_r"). Stepped rings of
    # materials showed their edges as jagged glints in the viewer.
    "glint": {"u": 4.3, "v": 4.0, "rough_min": 0.3, "rough_r": 3.8, "spec_r": 3.8, "base": 0.05},
    # The light crescent round the lower right (lighting in the sprite, so not painted): a narrow
    # polished, reflective band along that limb, where the room light's reflection lands. "w" is its width
    # as a share of the radius in from the girth, "ang" its centre (degrees, 0 = right, y up), "spread" its
    # angular falloff (degrees).
    "rim": {"w": 0.3, "ang": -28, "spread": 45, "rough": 0.08},
}
SHELL = {"voxel": 0.02, "inside": 0.004, "faces": 700, "smooth": 8}


def egg_radius(ang, egg):
    """Distance from the egg's centre to its girth curve along `ang` (radians, y up), sprite px."""
    a, b, n, e = egg["a"], egg["b"], egg["n"], egg["e"]
    c, s = math.cos(ang), math.sin(ang)
    lo, hi = 0.0, 2 * max(a, b)
    for _ in range(40):
        r = (lo + hi) / 2
        x, y = r * c, r * s
        if abs(x / (a * (1 + e * y / b))) ** n + abs(y / b) ** n <= 1:
            lo = r
        else:
            hi = r
    return lo


def finish_material(sprite, g, res=64):
    """pal_<mid> with the glint's finish maps: roughness (G; B metallic 0) and reflectance (Specular Tint)."""
    import numpy as np
    gl, rm, egg = SPEC["glint"], SPEC["rim"], SPEC["egg"]
    mat = common.palette_material(sprite, int(SPEC["mid"]), NAME, metallic=SPEC["metallic"], roughness=SPEC["roughness"])
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = SPEC["specular"]
    w, h = res, int(round(res * g.h / g.w))
    ys, xs = np.mgrid[0:h, 0:w]
    u = (xs + 0.5) / w * g.w
    v = (1 - (ys + 0.5) / h) * g.h  # image rows run bottom-up in Blender
    d2 = (u - gl["u"]) ** 2 + (v - gl["v"]) ** 2
    du, dv = u - egg["cu"], egg["cv"] - v
    ang = np.arctan2(dv, du)
    edge = np.clip(1 - np.hypot(du, dv) / np.vectorize(lambda a: egg_radius(a, egg))(ang), 0, 1)  # 0 on the girth
    dang = np.angle(np.exp(1j * (ang - math.radians(rm["ang"]))))
    rim = np.exp(-(edge / rm["w"]) ** 2) * np.exp(-(dang / math.radians(rm["spread"])) ** 2)
    rough = SPEC["roughness"] - (SPEC["roughness"] - gl["rough_min"]) * np.exp(-d2 / gl["rough_r"] ** 2)
    rough = np.where(rough > rm["rough"], rough - (rough - rm["rough"]) * rim, rough)
    spec = gl["base"] + (1 - gl["base"]) * np.maximum(np.exp(-d2 / gl["spec_r"] ** 2), rim)
    spec = np.where(spec <= 0.0031308, 12.92 * spec, 1.055 * spec ** (1 / 2.4) - 0.055)  # glTF reads it as sRGB

    def image(suffix, rgb):
        px = np.stack([*rgb, np.ones_like(rough)], -1).astype(np.float32)
        img = bpy.data.images.get(f"{NAME}_{suffix}") or bpy.data.images.new(f"{NAME}_{suffix}", w, h, alpha=False)
        img.scale(w, h)
        img.colorspace_settings.name = "Non-Color"
        img.pixels[:] = px.ravel()
        img.pack()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        return tex

    zero = np.zeros_like(rough)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(image("finish", (zero, rough, zero + SPEC["metallic"])).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nt.links.new(image("spec", (spec, spec, spec)).outputs["Color"], bsdf.inputs["Specular Tint"])
    return mat


def body(sprite, coll):
    g = R.Grid(sprite, NAME)
    egg = SPEC["egg"]
    cu, cv = egg["cu"], egg["cv"]
    radii = [egg_radius(2 * math.pi * i / 360, egg) for i in range(360)]
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=SPEC["subdiv"], radius=1.0)
    for v in bm.verts:
        d = v.co.normalized()
        # Move the crown's peak toward "apex": the girth (rho 1) stays where it is.
        k = 1 - (d.x * d.x + d.y * d.y)
        qx, qy = d.x + SPEC["apex"][0] * k, d.y + SPEC["apex"][1] * k
        a = math.atan2(qy, qx)
        rho = math.hypot(qx, qy)
        r = rho * R.radius_at(radii, a)
        if d.z >= 0:
            z = SPEC["girth"] + d.z * SPEC["crown"]
        else:
            z = max(SPEC["girth"] + d.z * SPEC["belly"], 0.0)
        v.co = Vector((g.x(cu + r * math.cos(a)), g.y(cv - r * math.sin(a)), z * PX))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(finish_material(sprite, g))
    # UVs: the top view on the sprite grid (u, v / sprite size), the finish map's frame.
    uvl = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        u, v = g.uv(co.x, co.y)
        uvl.data[loop.index].uv = (u / g.w, 1 - v / g.h)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    obj.data.shade_smooth()
    return obj


def shell(obj, coll):
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    s = common.outline_shell(closed, coll, **SHELL)
    s.name = s.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    return s


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    b = body(sprite, coll)
    s = shell(b, coll)
    common.export_sprite_model(ROOT, [b, s], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([b], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
