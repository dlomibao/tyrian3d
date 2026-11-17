"""Waterfall (newshh.shp, a 5 x 2 block of 24 x 28 pieces; TORM's is 4 x 2): scenery, not an object (D212).

WHAT IT IS: a river going over a jungle cliff into a plunge pool. The sprite is a full rectangle
painted to run on into the tiles round it: the cliff wall's shadowed flanks left and right (their
lobed caps and the lit rock are mostly in the TILES beside the sprite), the curtain of water (its
crest is in the river tiles ABOVE the sprite: the sprite's first row is already falling water),
the pool, the bushes on its banks. Fixed (enemies 739-744, mv 0, armor 0); only the water animates
(ani 12, four phases).

HOW. As the island rock round level 1's machines (D66, D84): a relief whose colour is palette data
in a texture made from the sprite's own pixels (lib_tiles.rock_material; the game's rockMaterial.ts
looks the colours up in the live palette), fading out at the rectangle's edge into the HD terrain,
with no ink outline and no cast shadow. lib_newshh_falls.py makes the fields; here they become, per
piece:

  <piece>-static     rock, bushes and the wet rock under the water: matte, one texture
  <piece>-water-<f>  falls, foam and pool for sprite frame f (tyrian_frames): smoother, so the sun's
                     sheen lies where the river rolls over; its own texture; clear between the
                     strands, where the wet rock of the static layer shows
  <piece>-under      the closed underside (back wall, sides, base), turned away from the art's view

The shape is the real standing cliff (about 30 px tall): each layer is a surface over the art's
oblique view, a point drawn at art row s with height h standing at plan row v = s + h, so with
`tyrian_oblique` 1 the game draws every point where the art has it (D82, D165), and
`tyrian_depth_band` keeps it under what the original draws over it. The water lies WATER_OVER px
above the static layer everywhere, and its node sits higher, so it is drawn after it (both blend).

Contract: public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json for the six
pieces, every frame, pivots at the pieces' box centres on the ground.

Run: blender --background --python assets/blender/enemies/assembly-newshh-129.py [-- --measure dir]
(--measure dir: also writes each phase's coverage in the art's view, for tools/sprite_mask.py --measure)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1]),
                str(Path(__file__).resolve().parents[1] / "tiles")]
import common  # noqa: E402
import lib_newshh_falls as F  # noqa: E402
import lib_tiles as lt  # noqa: E402

NAME = "assembly-newshh-129"
WT = common.repo_root(__file__)
PX = 1 / 12
BAND = [0.0, 0.4, 0.0, 3.5]   # tyrian_depth_band: under background 2 (D165), 3.5 units of cliff squeezed in
SEAM = 0.5        # px a piece's static layer reaches under its neighbours, against hairline gaps,
SEAM_DROP = 0.4   # and px lower there: a piece's own box always shows its own texture (a neighbour's copy of
                  # those pixels can differ: newshh-129's and -205's fields assume copies of themselves beside
                  # them). The water layer stops at its box: it is clear between the strands, so a strip of
                  # the neighbour's water (another phase's, between the rows) would show through.
EDGE = 1.5        # px a piece reaches past the assembly's rectangle, for the fade
TOP_EDGE = 3.6    # and past its top, where the strands' heads start in the river above
FINE_STEP, COARSE_STEP = 0.5, 1.0   # px between a layer's vertices: fine over rock and over the crest's roll
CREST_ROWS = 10   # the rows the water layer is fine over (both ways: the crest is scalloped)
WATER_NODE_UP = 0.5   # units the water nodes sit above the static one: three.js draws blended meshes far to near
                      # by their node's place, so the static layer (which writes depth) is drawn before its water
STATIC_FINISH = {"roughness": 0.9, "metallic": 0.0}
WATER_FINISH = {"roughness": 0.78, "metallic": 0.0}
UNDER_DROP = 0.5  # px under the surface the underside starts
STATIC_CREASE, WATER_CREASE = 45.0, 55.0   # degrees: sharper folds are hard edges (no smoothed normals across)


def load():
    frames, colors, data = {}, {}, {}
    for name in F.PIECES:
        d = common.load_sprite(WT, name)
        data[name] = d
        colors.update(d["colors"])
        frames[name] = {f["index"]: f["pixels"] for f in d["frames"]}
        assert sorted(frames[name]) == sorted(F.CYCLES[name]), name
    return frames, colors, data


def sample(a, u, s):
    """Bilinear sample of a padded-canvas field (F.HRES samples per px) at art point (u, s)."""
    x = (u + F.PAD) * F.HRES - 0.5
    y = (s + F.PAD) * F.HRES - 0.5
    x0 = int(min(max(np.floor(x), 0), a.shape[1] - 2))
    y0 = int(min(max(np.floor(y), 0), a.shape[0] - 2))
    fx, fy = min(max(x - x0, 0.0), 1.0), min(max(y - y0, 0.0), 1.0)
    return float((a[y0, x0] * (1 - fx) + a[y0, x0 + 1] * fx) * (1 - fy) + (a[y0 + 1, x0] * (1 - fx) + a[y0 + 1, x0 + 1] * fx) * fy)


def material(name, ch, ramps, finish):
    """lib_tiles' HD rock material for a layer's channels, with its own finish and no ink outline
    (the game's outline pass skips a material whose userData.outlineParameters.visible is false)."""
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = lt.rock_material(name, ch, ramps, alpha=ch["alpha"])
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = finish["roughness"]
    bsdf.inputs["Metallic"].default_value = finish["metallic"]
    mat["outlineParameters"] = {"visible": False}
    return mat


def axis(lo, hi, fine=None):
    """Grid lines from lo to hi (px): FINE_STEP apart through the whole-px cells `fine(cell)` picks,
    COARSE_STEP apart through the others (none given: all coarse)."""
    out, x = [lo], lo
    while x < hi - 1e-6:
        end = min(hi, math.floor(x + 1e-6) + 1.0)
        step = FINE_STEP if fine is not None and fine(math.floor(x + 1e-6)) else COARSE_STEP
        n = max(1, int(round((end - x) / step)))
        out += [x + (end - x) * i / n for i in range(1, n + 1)]
        x = end
    return out


def box(name, seam):
    """The art rectangle a layer of a piece covers: its own box, `seam` over its neighbours, EDGE past
    the assembly's edge."""
    c0, r0 = F.HOME[name]
    left = EDGE if c0 == 0 else seam
    right = EDGE if c0 + F.PW == F.W else seam
    top = TOP_EDGE if r0 == 0 else seam
    bottom = EDGE if r0 + F.PH == F.H else seam
    return c0, r0, c0 - left, c0 + F.PW + right, r0 - top, r0 + F.PH + bottom


def sheet(name, piece, heights, tex, fine, coll, mat, crease, seam=0.0, node_up=0.0, min_alpha=None):
    """One layer of a piece: a grid over its art rectangle, each vertex at its height on the art's ray
    (plan row = art row + height), UVs on the piece's texture. `fine`: (columns, rows) that get the
    fine grid (axis). `min_alpha`: leave out the quads the texture's coverage never reaches (the water
    layer over rock)."""
    c0, r0, u0, u1, s0, s1 = box(piece, seam)
    us, ss = axis(u0, u1, fine[0]), axis(s0, s1, fine[1])
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("rock")
    cx, cy = c0 + F.PW / 2, r0 + F.PH / 2
    tw, th = F.PW + 2 * F.PAD, F.PH + 2 * F.PAD
    verts, uvs, art = {}, {}, {}
    for j, s in enumerate(ss):
        for i, u in enumerate(us):
            h = sample(heights, u, s)
            over = max((c0 - u) * (c0 > 0), (u - c0 - F.PW) * (c0 + F.PW < F.W), (r0 - s) * (r0 > 0), (s - r0 - F.PH) * (r0 + F.PH < F.H))
            if over > 1e-6:
                h = max(h - SEAM_DROP * over / SEAM, 0.0)
            verts[(i, j)] = bm.verts.new(((u - cx) * PX, (cy - (s + h)) * PX, h * PX - node_up))
            art[verts[(i, j)]] = (u, s)
            uvs[(i, j)] = ((u - c0 + F.PAD) / tw, 1 - (s - r0 + F.PAD) / th)
    alpha = tex["alpha"]
    for j in range(len(ss) - 1):
        for i in range(len(us) - 1):
            if min_alpha is not None:
                x0, x1 = int((us[i] - c0 + F.PAD) * F.TEX), int(np.ceil((us[i + 1] - c0 + F.PAD) * F.TEX))
                y0, y1 = int((ss[j] - r0 + F.PAD) * F.TEX), int(np.ceil((ss[j + 1] - r0 + F.PAD) * F.TEX))
                if alpha[max(0, y0 - 1):y1 + 1, max(0, x0 - 1):x1 + 1].max() < min_alpha:
                    continue
            keys = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            f = bm.faces.new([verts[k] for k in keys])
            f.smooth = True
            for loop, k in zip(f.loops, keys):
                loop[uv].uv = uvs[k]
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()
    for e in bm.edges:
        (ua, sa), (ub, sb) = art[e.verts[0]], art[e.verts[1]]
        # hard: a sharp fold, and the box's own edge where a seam strip hangs from it (its slope is not the surface's)
        on_box = any(abs(a - k) < 1e-6 and abs(b - k) < 1e-6
                     for a, b, ks in ((ua, ub, (c0, c0 + F.PW)), (sa, sb, (r0, r0 + F.PH))) for k in ks)
        if len(e.link_faces) == 2 and (on_box or e.calc_face_angle(0.0) > math.radians(crease)):
            e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o.location = (0, 0, node_up)
    coll.objects.link(o)
    return o


def underside(name, piece, heights, coll, mat):
    """A piece's closed underside (art rule 3: closed and plausible, nothing more): a back wall under
    its top edge, a base on the ground, side walls, and a skirt under its bottom edge. Every face is
    turned away from the art's eye or lies along its rays (the sides are plumb planes of one column, the
    skirt runs down the ray of the piece's last row), and it starts UNDER_DROP px under the surface on
    the same rays, so the game never draws it; the viewer and Blender see a solid."""
    c0, r0 = F.HOME[piece]
    a0, a1, b0, b1 = c0, c0 + F.PW, r0, r0 + F.PH
    cx, cy = c0 + F.PW / 2, r0 + F.PH / 2
    bm = bmesh.new()

    def top(u, s):
        h = max(sample(heights, u, s) - UNDER_DROP, 0.05)
        return bm.verts.new(((u - cx) * PX, (cy - (s + h)) * PX, h * PX)), h

    def ground(u, v):
        return bm.verts.new(((u - cx) * PX, (cy - v) * PX, 0.0))

    def face(verts, want):
        f = bm.faces.new(verts)
        f.normal_update()
        if f.normal.dot(want) < 0:
            f.normal_flip()
        f.smooth = False

    us, ss = axis(a0, a1), axis(b0, b1)
    back = [top(u, b0) for u in us]
    back_g = [ground(u, b0 + h) for u, (_, h) in zip(us, back)]
    front = [top(u, b1) for u in us]
    front_g = [ground(u, b1) for u in us]
    for i in range(len(us) - 1):
        face([back[i][0], back[i + 1][0], back_g[i + 1], back_g[i]], (0, 1, 0))
        face([front[i][0], front[i + 1][0], front_g[i + 1], front_g[i]], (0, -1, -1))
    for k, u, want in ((0, a0, (-1, 0, 0)), (-1, a1, (1, 0, 0))):
        chain = [back[k][0]] + [top(u, s)[0] for s in ss[1:-1]] + [front[k][0]]
        face(chain + [front_g[k], back_g[k]], want)
    face(back_g + front_g[::-1], (0, 0, -1))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def tag(o):
    """The glTF extras: the art's view (obliqueView.ts, D165) and no cast shadow (modelPrep.ts, D66)."""
    o["tyrian_oblique"] = 1.0
    o["tyrian_depth_band"] = list(BAND)
    o["tyrian_ground"] = True
    return o


def build():
    frames, colors, data = load()
    fields = F.Fields(frames, colors)
    coll = common.reset_collection(NAME)
    under = common.palette_material({"name": NAME, "colors": colors}, 2, "nshh129under", metallic=0.0, roughness=0.95)
    under.use_backface_culling = True
    under["outlineParameters"] = {"visible": False}
    h_static, h_water = fields.heights()
    static = fields.static()
    waters = [fields.water_layer(k) for k in range(4)]
    parts = {}
    rock = ~fields.water   # (padded canvas) where the static layer is seen
    for name in F.PIECES:
        c0, r0 = F.HOME[name]
        mine = rock[:, max(0, c0 + F.PAD - 1):c0 + F.PAD + F.PW + 1][max(0, r0 + F.PAD - 1):r0 + F.PAD + F.PH + 1]
        cols = set(np.flatnonzero(mine.any(0)) + max(0, c0 + F.PAD - 1) - F.PAD)
        rows = set(np.flatnonzero(mine.any(1)) + max(0, r0 + F.PAD - 1) - F.PAD)
        static_fine = (lambda c, cols=cols: c in cols or c + 1 in cols or c - 1 in cols,
                       lambda r, rows=rows: r in rows or r + 1 in rows or r - 1 in rows)
        water_fine = (lambda c, top=r0 == 0: top, lambda r: r < CREST_ROWS)
        tex = F.piece_texture(static, name)
        group = [tag(sheet(f"{name}-static", name, h_static, tex, static_fine, coll,
                           material(f"rock_{name}_static", tex, F.STATIC_RAMPS, STATIC_FINISH), STATIC_CREASE, seam=SEAM))]
        for k, layer in enumerate(waters):
            frame = F.CYCLES[name][k]
            tex = F.piece_texture(layer, name)
            o = sheet(f"{name}-water-{frame}", name, h_water, tex, water_fine, coll,
                      material(f"rock_{name}_water_{frame}", tex, F.WATER_RAMPS, WATER_FINISH), WATER_CREASE,
                      node_up=WATER_NODE_UP, min_alpha=0.004)
            group.append(common.frame_part(tag(o), [frame]))
        group.append(tag(underside(f"{name}-under", name, h_static, coll, under)))
        parts[name] = group
    return fields, data, parts, (static, waters)


def write_measure(out, fields, layers):
    """Each phase's coverage in the art's view on the catalogue layout's grid, TEX px per sprite px:
    where a layer's texture is more than half opaque (the sheets cover every texel of their boxes)."""
    static, waters = layers
    out.mkdir(parents=True, exist_ok=True)
    p = F.PAD * F.TEX
    for k, layer in enumerate(waters):
        cover = np.maximum(static["alpha"], layer["alpha"])[p:-p, p:-p] > 0.5
        img = bpy.data.images.new(f"cover{k}", cover.shape[1], cover.shape[0], alpha=True)
        px = np.zeros(cover.shape + (4,), np.float32)
        px[..., :3] = 1.0
        px[..., 3] = cover
        img.pixels.foreach_set(px[::-1].ravel())
        img.filepath_raw = str(out / f"top_phase{k}.png")
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)


def main():
    fields, data, parts, layers = build()
    for name in F.PIECES:
        common.export_sprite_model(WT, parts[name], f"enemies/{name}", data[name]["sprites"])
        print(name, {o.name: len(o.data.polygons) for o in parts[name]})
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--measure" in args:
        write_measure(Path(args[args.index("--measure") + 1]), fields, layers)


if __name__ == "__main__":
    main()
