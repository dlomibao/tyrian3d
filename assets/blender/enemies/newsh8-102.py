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

Its damaged frame, newsh8.shp 140 (the egg's dgr), is a second frame of this model (D17): a cracked
copy of the egg (frame_part 140) beside the intact one (frame_part 102), sharing the outline shell (the
damaged sprite has the same outline). Drawn through D87's damage tint it read as a mottled whole egg
(E3 QA round 3); now the shell is broken away where the damaged sprite is black (lower left, a crack
down from the top, small holes), a thin lip kept only along the girth, so the top view keeps the egg's
outline, the shell has a thickness and the hollow inside is the sprite's black (pal_1). The broken
stone is dull, pal_67 (the damaged sprite's median): it draws no glint.

Run: blender --background --python assets/blender/enemies/newsh8-102.py
     [-- --preview out.png [--preview-damaged out140.png]] [--top dir]   (--top: top-view masks per frame)
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
INTACT, DAMAGED = 102, 140  # the egg and its damaged frame (dgr), both drawn by this model (D17)
# The cracked egg (frame 140): faces of the crown whose top-view centre samples the crack field above
# "cut" are broken away, except a "lip" (px) of shell above the girth; islands of shell left alone in
# the break fall to "shard_z" px, flattened to "shard_flat" of their height (smaller than "shard_min"
# faces are dropped); the cut mesh is decimated to "keep" of its faces, then given a shell "thick" px
# thick. "shell" is the damaged sprite's median index inside its ink (67: the damaged stone is darker
# and has no glint), "inside" its black.
CRACK = {"subdiv": 5, "cut": 0.4, "lip": 0.15, "shard_z": 1.3, "shard_flat": 0.35, "shard_min": 6,
         "thick": 0.5, "shell": 67, "inside": 1, "rough": 0.55, "keep": 0.3}
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


def egg_bmesh(g, subdiv):
    """The egg's surface (no material, no UVs): an icosphere warped onto the girth, crown and belly.
    Returns the bmesh; each vertex's height above the ground in sprite px is in its z / PX."""
    egg = SPEC["egg"]
    cu, cv = egg["cu"], egg["cv"]
    radii = [egg_radius(2 * math.pi * i / 360, egg) for i in range(360)]
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
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
    return bm


def body(sprite, coll):
    g = R.Grid(sprite, NAME)
    bm = egg_bmesh(g, SPEC["subdiv"])
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
    common.frame_part(obj, [INTACT])
    return obj


# ----------------------------------------------------------------------------------------------
# The cracked egg (frame 140, the egg's damaged frame: TYRIAN's dgr). D87 drew it as this intact
# egg tinted by the pixel difference, a mottled whole egg (E3 QA round 3, L). It gets its own part
# here, shown on frame 140 only (D17), so the frame is drawn by this model and not by D87's damage.
# ----------------------------------------------------------------------------------------------

def damaged_pixels(index):
    """newsh8.shp sprite `index` as 14 rows of 12 palette indices (-1 transparent), decoded from the
    game data as src/data/sprites.ts decodeSprite2 does (a local copy: the catalogue lists only the
    intact frame for this model)."""
    sheet = (ROOT / "data" / "newsh8.shp").read_bytes()
    op = (index - 1) * 2
    p = sheet[op] | (sheet[op + 1] << 8)
    rows, row, x = [], [-1] * 12, 0
    while p < len(sheet) and sheet[p] != 0x0F:
        x += sheet[p] & 0x0F
        count = sheet[p] >> 4
        if count == 0:
            rows.append(row)
            row, x = [-1] * 12, 0
            p += 1
            continue
        for _ in range(count):
            p += 1
            if x < 12:
                row[x] = sheet[p]
            x += 1
        p += 1
    if any(v >= 0 for v in row):
        rows.append(row)
    rows += [[-1] * 12 for _ in range(14 - len(rows))]
    return rows


def crack_field(sprite):
    """Where the shell is broken, per sprite pixel (1 broken): the pixels black (palette 1) on the
    damaged frame that are not black on the intact one, and the ink ring's black pixels beside them
    (the break runs out through the rim there); the rest of the ink ring stays shell."""
    dmg = damaged_pixels(DAMAGED)
    ok = sprite["frames"][0]["pixels"]
    new = [[dmg[r][c] == 1 and ok[r][c] != 1 for c in range(12)] for r in range(14)]

    def near(r, c):
        return any(0 <= r + dr < 14 and 0 <= c + dc < 12 and new[r + dr][c + dc]
                   for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))
    return [[1.0 if new[r][c] or (dmg[r][c] == 1 and near(r, c)) else 0.0 for c in range(12)] for r in range(14)]


def sample(field, u, v):
    """Bilinear sample of a per-pixel field at sprite coordinates (u, v), pixel centres at +0.5."""
    h, w = len(field), len(field[0])
    x, y = u - 0.5, v - 0.5
    c0, r0 = math.floor(x), math.floor(y)
    fx, fy = x - c0, y - r0

    def at(c, r):
        return field[min(max(r, 0), h - 1)][min(max(c, 0), w - 1)]
    return ((at(c0, r0) * (1 - fx) + at(c0 + 1, r0) * fx) * (1 - fy)
            + (at(c0, r0 + 1) * (1 - fx) + at(c0 + 1, r0 + 1) * fx) * fy)


def cracked(sprite, coll):
    """The same egg, its shell broken open where the damaged sprite is black: the crown gone over
    the lower left (a low lip of shell kept along the girth, so the top-view outline is the egg's),
    a crack down from the top, loose shell pieces lying in the hollow. The shell has a thickness;
    its inside and the hollow are black (pal_1, the sprite's own black). The stone is dull here: the
    damaged sprite draws no glint, so no polish maps, one darker palette index (its median, 67)."""
    g = R.Grid(sprite, NAME)
    C = CRACK
    field = crack_field(sprite)
    bm = egg_bmesh(g, C["subdiv"])
    bm.faces.ensure_lookup_table()
    gone = []
    for f in bm.faces:
        if min(v.co.z for v in f.verts) / PX < SPEC["girth"] + C["lip"]:
            continue
        c = f.calc_center_median()
        u, v = g.uv(c.x, c.y)
        if sample(field, u, v) > C["cut"]:
            gone.append(f)
    bmesh.ops.delete(bm, geom=gone, context="FACES_ONLY")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    # Islands of shell left standing alone inside the break fall into the hollow as shards.
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            cur = stack.pop()
            isl.append(cur)
            for e in cur.edges:
                for n in e.link_faces:
                    if n.index not in seen:
                        seen.add(n.index)
                        stack.append(n)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    shards = 0
    for isl in islands[1:]:
        verts = {v for f in isl for v in f.verts}
        if len(isl) < C["shard_min"]:
            bmesh.ops.delete(bm, geom=list(isl), context="FACES_ONLY")
            continue
        zmin = min(v.co.z for v in verts)
        for v in verts:
            v.co.z = C["shard_z"] * PX + (v.co.z - zmin) * C["shard_flat"]
        shards += 1
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    me = bpy.data.meshes.new(f"{NAME}_cracked")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(common.palette_material(sprite, C["shell"], f"{NAME}_cracked", metallic=0.0, roughness=C["rough"]))
    me.materials.append(common.palette_material(sprite, C["inside"], f"{NAME}_inside", metallic=0.0, roughness=0.9))
    obj = bpy.data.objects.new(f"{NAME}_cracked", me)
    coll.objects.link(obj)
    obj.data.shade_smooth()
    # The fine mesh only serves to cut the breaks; collapse it back toward the intact egg's count.
    dec = obj.modifiers.new("lighter", "DECIMATE")
    dec.ratio = C["keep"]
    dec.use_collapse_triangulate = True
    sol = obj.modifiers.new("shell", "SOLIDIFY")
    sol.thickness = C["thick"] * PX
    sol.offset = -1.0
    sol.use_rim = True
    sol.material_offset = 1      # the inside faces: black
    sol.material_offset_rim = 0  # the broken edges: the shell's stone
    sol.use_even_offset = True
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bpy.ops.object.modifier_apply(modifier=sol.name)
    common.frame_part(obj, [DAMAGED])
    print(f"cracked: {len(gone)} faces broken away, {shards} shards, {len(obj.data.polygons)} faces")
    return obj


def shell(obj, coll):
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    s = common.outline_shell(closed, coll, **SHELL)
    s.name = s.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    return s


def top_masks(objects_by_frame, out_dir, k=8):
    """Top-view masks of each frame (white where the model is, k px per sprite px) by raycasting
    straight down, for tools/sprite_mask.py --measure."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dg = bpy.context.evaluated_depsgraph_get()
    for frame, objs in objects_by_frame.items():
        trees = [BVHTree.FromObject(o, dg) for o in objs]
        w, h = 12 * k, 14 * k
        img = np.zeros((h, w), np.float32)
        for r in range(h):
            for c in range(w):
                x, y = (c + 0.5) / k / 12 - 0.5, 7 / 12 - (r + 0.5) / k / 12
                if any(t.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)))[0] is not None for t in trees):
                    img[r, c] = 1.0
        im = bpy.data.images.new(f"top{frame}", w, h, alpha=False)
        px = np.stack([img[::-1]] * 3 + [np.ones_like(img)], -1)
        im.pixels[:] = px.ravel()
        im.filepath_raw = str(out_dir / f"top_{frame}.png")
        im.file_format = "PNG"
        im.save()


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    b = body(sprite, coll)
    c = cracked(sprite, coll)
    s = shell(b, coll)
    sprites = [dict(sp, frames=[INTACT, DAMAGED]) for sp in sprite["sprites"]]
    common.export_sprite_model(ROOT, [b, c, s], MODEL, sprites)
    if "--top" in sys.argv:
        top_masks({INTACT: [b], DAMAGED: [c]}, sys.argv[sys.argv.index("--top") + 1])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([b], out, ref, size=sprite["frames"][0]["size"])
        if "--preview-damaged" in sys.argv:
            common.render_preview([c], sys.argv[sys.argv.index("--preview-damaged") + 1], None,
                                  size=sprite["frames"][0]["size"], frame=DAMAGED)


if __name__ == "__main__":
    main()
