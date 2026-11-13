"""Red lava lump (newshl.shp 118): a 3D version of its sprite.

- newshl-118, lava lump: a red-hot stone egg, about 9 x 10 px, tilted from upper right to lower
  left, built with the asteroids' rock builder (lib_newshd_rock: body traced on the inner mask,
  fracture faces, the D175 facet ramp of the sprite's own 112-118 reds). The ramp's facets are few
  and large and ranked mostly by the art's light, so the lump is lit upper left and dark lower right.
  The hot spot (row 5: 123 at column 4, 121 at column 5, 118 below) is painted on the upper-left top
  facets themselves (HOT, cut finer there first), never left to the ramp: a 123 core in 121 in a
  118 rim, glowing (D126; metallic 1, rough, D173). The ramp's ink (1) facets go to 113 and its
  stray 121/123 to 118: ink belongs to the outline shell only.

Units: X = (u - 6) / 12, Y = (7 - v) / 12 for sprite edge coordinates (u right, v down), Z up.
Hard-surface build (D50-D53, D65, D189, D192); one frame; outline shell from a sealed copy.

Run: blender --background --python assets/blender/enemies/newshl-118.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402

NAME = "newshl-118"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
W, H = 12, 14


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def X(u):
    return (u - W / 2) * PX


def Y(v):
    return (H / 2 - v) * PX


# --- helpers (local; not shared) -----------------------------------------------------------------

def bridge(bm, rings, mats):
    """Faces between consecutive rings (lists of verts; a single vert is a pole). Band i (between
    ring i-1 and i) takes mats[i]."""
    for i in range(1, len(rings)):
        r0, r1, m = rings[i - 1], rings[i], mats[i]
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = m


def material(sprite, index, tag, metallic, roughness, glow=0.0, spec=None, coat=0.0, coat_rough=0.2):
    m = common.palette_material(sprite, index, tag, metallic=metallic, roughness=roughness, emission_strength=glow)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if spec is not None:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
    return m


def shell_of(obj, coll, name, **kw):
    """Outline shell (D51) from a sealed copy of the model, every outer island kept (D189)."""
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(closed, coll, islands="outer", **kw)
    sh.name = sh.data.name = f"{name}_outline"
    bpy.data.objects.remove(closed)
    assert len(sh.data.polygons) > 0, f"{name}: empty outline shell"
    return sh


def finish(obj, angle=38):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))


LAVA_SPEC = {
    "metallic": 0.0,
    "roughness": 0.8,
    "mid": 115,
    "h_top": 0.30,
    "h_bot": 0.10,
    "rise": 0.75,
    "fall": 0.8,
    "summit": (5.6, 6.2),
    "summit_gain": 0.10,
    "ridges": [((3.6, 8.6), 0.18, 1.3)],
    "bumps": [((4.8, 5.4), 0.16, 1.4), ((8.4, 7.6), -0.12, 1.6)],
    "crests": [],
    "tilt": 0.10,
    "lumps": 0.035,
    "grow": 0.1,
    "waist": 0.06,
    "seed": 118,
    "fine": 2,
    "rim_spalls": 6,
    "cuts": [
        (150, 48, 0.06), (210, 44, 0.06), (20, 42, 0.07), (300, 50, 0.05), (90, 58, 0.04),
        (240, 22, 0.035), (330, 22, 0.035), (50, 24, 0.035),
        (30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.06),
    ],
    "cracks": [],
    "pits": [],
    # fewer, larger facets ranked mostly by the art's light (D175): lit upper left, dark lower right
    "ramp": {"angle": 22.0, "size": 3.2, "chip": 3.0, "sprite": 0.15, "flat": True, "bias": 0.0},
}


#: The sprite's hot spot (row 5: 123 at column 4, 121 at column 5; 118 under it in row 6), as
#: ellipses in sprite edge coordinates ((u, v) centre, (ru, rv) radii px), hottest last. Painted on
#: the upper-left top facets themselves (cut finer there first), never left to the facet ramp.
HOT = [
    (118, (4.85, 5.75), (1.35, 0.8)),
    (121, (5.0, 5.5), (1.1, 0.62)),
    (123, (4.55, 5.5), (0.6, 0.48)),
]


def hot_spot(g, obj, slots):
    """Cut the top faces round the hot spot on a 0.25 px grid, then give the top-facing faces whose
    centres fall inside each HOT ellipse that shade's slot (outer to inner)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    (u0, v0), (ru, rv) = HOT[0][1], HOT[0][2]
    x0, x1 = g.x(u0 - ru - 0.5), g.x(u0 + ru + 0.5)
    y0, y1 = g.y(v0 + rv + 0.5), g.y(v0 - rv - 0.5)

    def near(f):
        c = f.calc_center_median()
        return f.is_valid and f.normal.z > 0.2 and x0 - 0.05 < c.x < x1 + 0.05 and y0 - 0.05 < c.y < y1 + 0.05

    step = 0.25 / 12
    for axis, lo, hi in ((Vector((1, 0, 0)), x0, x1), (Vector((0, 1, 0)), y0, y1)):
        t = lo
        while t <= hi:
            faces = [f for f in bm.faces if near(f)]
            geom = list({e for f in faces for e in (*f.verts, *f.edges)}) + faces
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * t, plane_no=axis)
            t += step
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    area = {}
    for f in bm.faces:
        if f.normal.z <= 0.25:
            continue
        c = f.calc_center_median()
        u, v = g.uv(c.x, c.y)
        for idx, (cu, cv), (a, b) in HOT:
            if ((u - cu) / a) ** 2 + ((v - cv) / b) ** 2 <= 1.0:
                f.material_index = slots[idx]
        if f.material_index in slots.values():
            k = next(i for i, s in slots.items() if s == f.material_index)
            area[k] = area.get(k, 0.0) + f.calc_area() * f.normal.z
    bm.to_mesh(me)
    bm.free()
    print("hot spot top-view px^2", {k: round(v * 144, 2) for k, v in sorted(area.items())})


def lava(sprite, coll):
    name = "newshl-118"
    obj, mat, g = R.rock(sprite, name, LAVA_SPEC, coll)
    # Hot shades glow (D126), with metallic 1 / rough so the glow is not an environment reflection
    # (D173). Put them in first so the facet ramp shares them (it reuses existing pal_<i>_ slots).
    me = obj.data
    slots = {}
    for idx, glow in ((118, 0.3), (121, 1.0), (123, 1.2)):
        slots[idx] = len(me.materials)
        hot = idx >= 121
        me.materials.append(material(sprite, idx, f"{name}-hot{idx}", 1.0 if hot else 0.0, 0.9 if hot else 0.8, glow=glow))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    hot_spot(g, obj, slots)
    R.facet_ramp(sprite, g, obj, LAVA_SPEC)
    # The ramp ranks the sprite's ink (1) as its darkest shade and its 121/123 as its brightest; ink
    # belongs to the outline shell only, and the hot colours only to the hot spot: remap them.
    remap = {1: 113, 121: 118, 123: 118}
    hot_faces = set()
    slot_of = {}
    for k, m in enumerate(me.materials):
        i = int(m.name.split("_")[1])
        slot_of.setdefault(i, k)
    if 113 not in slot_of:
        slot_of[113] = len(me.materials)
        me.materials.append(common.palette_material(sprite, 113, f"{name}-r113", metallic=0.0, roughness=0.8))
    attr = me.attributes.get("facet_n")
    for p in me.polygons:
        i = int(me.materials[p.material_index].name.split("_")[1])
        ramped = attr is not None and attr.data[p.index].vector.length > 0.5
        if i in remap and (i == 1 or ramped):
            p.material_index = slot_of[remap[i]]
    # Sit it on the ground: the waist was z = 0, the underside dome below.
    obj.location.z = LAVA_SPEC["h_bot"] * 0.85
    bpy.context.view_layer.update()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    # drop unused material slots
    used = {p.material_index for p in me.polygons}
    keep = [k for k in range(len(me.materials)) if k in used]
    new_index = {k: n for n, k in enumerate(keep)}
    idxs = [new_index[p.material_index] for p in me.polygons]
    mats = [me.materials[k] for k in keep]
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    for p, k in zip(me.polygons, idxs):
        p.material_index = k
    R.set_facet_normals(obj)
    area = {}
    for p in me.polygons:
        area[me.materials[p.material_index].name] = area.get(me.materials[p.material_index].name, 0) + p.area
    tot = sum(area.values())
    print("lava materials", {k: round(v / tot, 3) for k, v in sorted(area.items())})
    sh = R.d90_shell(obj, coll, name)
    return obj, sh


# --- newshl-134: red-banded canister -------------------------------------------------------------

def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, sh = lava(sprite, coll)
    common.export_sprite_model(ROOT, [obj, sh], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][0]
        common.render_preview([obj, sh], out, ROOT / "reference" / "models" / NAME / f["image"], size=f["size"])


if __name__ == "__main__":
    main()
