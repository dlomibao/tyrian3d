"""Blue asteroid (newsh5.shp frame 89, a 24x28 cell, 23 px disc): design A.

What it is: a floating, tumbling ball of blue stone (SURFACE's sky-layer weavers, BRAINIAC's and
NOSE DRIP's drifters, LAVA EXIT). Airborne, so it is round and closed all over: a sphere of the
sprite's inner disc (21 px across inside its ink ring, D74), not a ground dome.

Reading the sprite (light from the upper left; rubric "Reading a sprite"): a round rock whose crust
is cracked into dark plates (indices 48-53) parted by a network of pale veins (56-61, two 63 glints).
The black ring is the ink, the brighter upper left and darker lower right are the art's light. So:
the crust is broken into flat plates, each sunk a little below the old rounded crust with a
chamfered wall; the narrow strips of crust left standing between them are the veins, raised seams
whose lit slopes catch the light (a highlight on rock is a lit face, art rule 2, not paint). The
plates sit where the sprite draws its dark patches (local minima of the sprite's shade field); the
sides and the underside carry the same plates on an even spiral, so the tumbling rock reads the same
from any angle (underside: no tuning).

Colour: the D175 facet ramp (lib_newshd_rock.facet_ramp): every facet one shade of the sprite's own
48-63 ramp, ranked by its light and by the sprite's brightness under it, matched to the sprite's
shade distribution. Matte stone (metallic 0, roughness 0.85). AO/roughness bake only (no concept
projection); D90 outline shell from a sealed copy kept out of the bake (D118).

    blender -b --factory-startup -P newsh5-89.py -- [--no-bake] [--out file.glb]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_newshd_rock as lib  # noqa: E402

NAME = "newsh5-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = 1 / 12  # one sprite px in Blender units

# The inner disc (inside the ink ring): columns 1-21, rows 3-23 (pixel edges 1..22, 3..24).
CU, CV, R = 11.5, 13.5, 10.5
JITTER = 0.0  # spiral plate jitter, share of the spacing
SPACING = 3.7  # plate spacing on the sides and underside, sprite px (the top's are the sprite's)
COVER = 0.75  # plate cut radius as a share of the distance to the nearest plate (> 0.5: cuts meet)
STEP = (0.0, 0.35)  # extra depth of each plate, px (random): plates step against each other
CLAMP = False
SHORT = 0.0  # seams shorter than this (px) collapse before the chamfer
SEAM = 0.7  # the seam chamfer each side, px (the vein ridges)
SEG, PROFILE = 3, 0.7  # the ridge's rounding: segments and profile (> 0.5 a fuller, rounder ridge)
#: the facet ramp (D175) twice over the sprite's shade distribution: the plates take its darker part,
#: the vein ridges its paler part, as the sprite draws dark plates parted by pale veins
SPLIT = False
CHIP = 2.0  # chip_planes size (px); 0: each plate stays one facet
VEIN_SHIFT, PLATE_SHIFT = 1, 0
RAMP_ONE = {"sprite": 0.9}
RAMP_PLATE = {"sprite": 0.8, "size": 4.0, "strength": 0.9, "bias": 0.1}
RAMP_VEIN = {"sprite": 0.9, "size": 1.5, "strength": 0.5, "bias": -0.35}
SEED = 2  # plate depth jitter; seeds 1 and 5 overlap two seam chamfers (non-manifold), 2 is clean
DEBUG = False
GROW = 0.25  # px the waist is grown past the inner mask (the plates near the limb cut it back)

SPEC = {
    "mid": 54, "metallic": 0.0, "roughness": 0.85,
    "ramp": {"sprite": 0.75},
    "h_top": R * U, "h_bot": R * U, "rise": 1.0, "fall": 1.0, "top_pow": 1.0, "bot_pow": 1.0,
    "summit": (CU, CV), "summit_gain": 0.0, "ridges": [], "tilt": 0.0,
    "lumps": 0.006, "waist": 0.0, "seed": 89, "smooth": 8, "steps": 96, "grow": GROW,
}


# --- the plates --------------------------------------------------------------------------------

def sprite_seeds(pix):
    """The dark plates the sprite draws: local minima of its shade field (indices blurred over
    about a pixel), at least 3.6 px apart, inside the disc."""
    H, W = len(pix), len(pix[0])

    def inside(c, r):
        return math.hypot(c + 0.5 - CU, r + 0.5 - CV) < R - 0.6

    f = {}
    for r in range(H):
        for c in range(W):
            if not inside(c, r):
                continue
            s = w = 0.0
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and pix[rr][cc] >= 0 and inside(cc, rr):
                        g = math.exp(-(dr * dr + dc * dc) / 2)
                        s += g * pix[rr][cc]
                        w += g
            f[(c, r)] = s / w
    seeds = []
    for k in sorted(f, key=lambda k: f[k]):
        if all(math.hypot(k[0] - a, k[1] - b) >= 3.6 for a, b in seeds):
            seeds.append(k)
    dirs = []
    for c, r in seeds:
        x, y = c + 0.5 - CU, CV - (r + 0.5)
        z = math.sqrt(max(R * R - x * x - y * y, 0.0))
        dirs.append(Vector((x, y, z)).normalized())
    return dirs


def spiral_seeds(have):
    """Plates on the sides and underside: an even (Fibonacci) spiral, skipping points near a plate
    the sprite already places."""
    n = int(4 * math.pi * R * R / (SPACING * SPACING * 0.87))
    rnd = __import__("random").Random(SEED + 100)
    out = []
    for k in range(n):
        z = 1 - 2 * (k + 0.5) / n
        rho = math.sqrt(1 - z * z)
        a = k * math.pi * (3 - math.sqrt(5)) + 0.7
        d = Vector((rho * math.cos(a), rho * math.sin(a), z))
        # a little irregular, so the sides never read as a honeycomb
        d = (d + Vector([rnd.uniform(-1, 1) for _ in range(3)]) * JITTER * SPACING / R).normalized()
        if all(math.acos(max(-1, min(1, d.dot(e)))) * R > 0.8 * SPACING for e in have + out):
            out.append(d)
    return out


def plates(bm, centre, dirs):
    """Break the crust into flat plates: one planar cut per plate, deep enough that neighbouring cuts
    meet (each plate fills its Voronoi cell round its seed, so the ball is all plates), each at a
    slightly different depth so the plates step a little against each other. Then chamfer the seams
    between plates into narrow worn ridges (the sprite's pale veins: lit slopes, not paint)."""
    body = BVHTree.FromBMesh(bm)
    rnd = __import__("random").Random(SEED)
    planes = []
    for i, n in enumerate(dirs):
        nn = min(math.acos(max(-1, min(1, n.dot(e)))) for j, e in enumerate(dirs) if j != i) * R
        a = COVER * nn
        h = R - math.sqrt(max(R * R - a * a, 0.0)) + rnd.uniform(*STEP)
        # the crust's own radius along n (the waist follows the traced outline, not a true circle)
        hit = body.ray_cast(centre, n)
        apex = hit[0] if hit[0] is not None else centre + n * (R * U)
        planes.append((apex - n * (h * U), n))
    for co, n in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=n, clear_outer=True)
        cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(bm, edges=cut, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # short seams (where three plates nearly meet at two corners) collapse to one corner, so the
    # seam chamfers never overlap
    short = [e for e in bm.edges if e.calc_length() < SHORT * U and all(len(f.verts) > 4 for f in e.link_faces)]
    if short and SHORT > 0:
        bmesh.ops.collapse(bm, edges=short, uvs=False)
    # the seams: edges between two plates (both faces planar cut n-gons, normals apart)
    plate = {f for f in bm.faces if len(f.verts) > 4}
    seams = [e for e in bm.edges if len(e.link_faces) == 2 and all(f in plate for f in e.link_faces)
             and e.link_faces[0].normal.dot(e.link_faces[1].normal) < math.cos(math.radians(4))]
    if DEBUG:
        print("plates", len(plate), "seams", len(seams))
    # tag the veins: the seam ridges and any crust left at the corners (everything but the plates)
    layer = bm.faces.layers.int.new("vein")
    for f in bm.faces:
        f[layer] = 0 if f in plate else 1
    res = bmesh.ops.bevel(bm, geom=seams, offset=SEAM * U, offset_type="OFFSET", segments=SEG, profile=PROFILE,
                    affect="EDGES", clamp_overlap=CLAMP)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:  # a plate face lies on one of the cut planes
        c = f.calc_center_median()
        f[layer] = 0 if any(f.normal.dot(n) > 0.99995 and abs((c - co).dot(n)) < 1e-4 for co, n in planes) else 1


def rock(sprite, coll):
    g = lib.Grid(sprite, NAME)
    bm, _ = lib.rock_body(g, SPEC, sectors=96, rings_top=24, rings_bot=24)
    pix = [[int(v) for v in r] for r in sprite["frames"][0]["pixels"]]
    top = sprite_seeds(pix)
    dirs = top + spiral_seeds(top)
    centre = Vector((g.x(CU), g.y(CV), 0.0))
    nm = lambda tag: DEBUG and print(tag, sum(1 for e in bm.edges if not e.is_manifold))
    plates(bm, centre, dirs)
    nm("plates")
    if CHIP:
        lib.chip_planes(bm, CHIP)
    nm("chips")
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    nm("clean")
    bmesh.ops.triangulate(bm, faces=bm.faces[:], ngon_method="EAR_CLIP")
    nm("tri")
    if DEBUG:
        for e in bm.edges:
            if not e.is_manifold:
                print("bad", len(e.link_faces), [round(x / U, 2) for x in e.verts[0].co], round(e.calc_length() / U, 4))
    mat = common.palette_material(sprite, SPEC["mid"], NAME, metallic=SPEC["metallic"], roughness=SPEC["roughness"])
    obj = common.mesh_object(NAME, bm, [mat], coll, smooth=True)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(14))
    print(f"plates: {len(top)} from the sprite, {len(dirs) - len(top)} on the spiral")
    return obj, g


def contrast(sprite, obj, vein):
    """Part the plates from the veins as the sprite does: after the ramp (which lays its shades out
    by the sprite's brightness and the light), each vein facet one shade paler and each plate facet
    one darker (VEIN_SHIFT, PLATE_SHIFT), kept in the rock's 48-61 ramp (63 stays a glint)."""
    import re
    me = obj.data
    idx_of = [int(re.match(r"pal_(\d+)_", m.name).group(1)) for m in me.materials]
    slot = {i: k for k, i in enumerate(idx_of)}
    for p, v in zip(me.polygons, vein):
        i = idx_of[p.material_index]
        if i == 63:
            continue
        j = max(48, min(61, i + (VEIN_SHIFT if v else PLATE_SHIFT)))
        if j not in slot:
            slot[j] = len(me.materials)
            me.materials.append(common.palette_material(sprite, j, f"{obj.name}-r{j}", metallic=SPEC["metallic"],
                                                        roughness=SPEC["roughness"]))
        p.material_index = slot[j]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, g = rock(sprite, coll)
    vein = [d.value for d in obj.data.attributes["vein"].data]
    flat = {}
    passes = ((0, RAMP_PLATE), (1, RAMP_VEIN)) if SPLIT else ((None, RAMP_ONE),)
    for tag, ramp in passes:
        faces = [k for k, v in enumerate(vein) if tag is None or v == tag]
        lib.facet_ramp(sprite, g, obj, dict(SPEC, ramp=ramp), faces=faces, flat=flat)
    lib.set_facet_normals(obj, flat)
    contrast(sprite, obj, vein)
    for m in obj.data.materials:  # matte stone: the light reads by the facets' angles, no glint
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.2
                break
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    print(f"{NAME} {len(obj.data.polygons)} triangles, non-manifold edges {open_edges}")
    closed = obj.copy()
    closed.data = obj.data.copy()
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(obj.data.materials)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=512, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **lib.D90_SHELL)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    if out:  # review builds only (flag)
        common.export_glb([obj, shell], out, image_format=fmt)
        print("exported", out)
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
