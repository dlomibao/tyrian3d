"""ASTEROID?'s cross pad (map 1-3 rows 233-237, shapesz 5x5 pattern, layer 0), hard-surface rebuild.

A mound of rock (the rim tiles 360-382 all round, and the inner corners 363 / 364 / 373 / 374) with
a raised gunmetal cross on it carrying three red light capsules per arm in silver bezels and a hot
core in a framed square at the centre. Everything is read off the tile art (pattern px, origin
top-left, y down):

- the mound (D148): the ASTEROID? station kit's (lib_l1kit) rubble bed over the whole painted
  footprint and its faceted stones over all of it but a strip round the cross (rock_field), so the
  rock is the same as the base complex's and every kit platform's. D141 left the mound to the HD
  ground's painting of these tiles and built an octagon of invented machinery quadrants over most
  of it: a lighter, painted stone round a polygon platform, beside polygon rocks a few rows below;
- the strip round the arms: the kit's mortar deck, the art's comb of kerb posts along its edge
  facing the rock, and the basket weave where it is wide enough;
- the cross: one chamfered slab (exactly the five enemy cells, top 0.30), the capsules (red blobs
  of the art, bezel = their 1-2 px silver ring, index 8; lens 113 glowing) and the core (113).

Geometry only from the tiles; no concept is projected (art rule 4). The only texture is the
model's AO/roughness bake (Building.bake_model, ground=0: the HD ground under it, the kit's worn
finish lib_l1kit.GRIT). No D51 outline shell: tile models draw no ink outline (structureInstances.ts
turns it off, tiles join edge to edge, D8), so a shell would only add an instanced draw and a
shadow caster (D141).

    Blender --background --factory-startup --python assets/blender/tiles/l1bld_cross_pad.py -- [--no-bake] [--preview x.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_tiles as lt  # noqa: E402


# --- Layout (pattern px) --------------------------------------------------------------------------
V_ARM = (48, 28, 72, 112)  # cells (1,2), (2,2), (3,2)
H_ARM = (24, 56, 96, 84)  # cells (2,1), (2,2), (2,3)
# Red lights (bbox of the art's red pixels, px): vertical arm (lying across x), horizontal (standing)
CAPS_V = [(50, 30, 68, 37), (50, 39, 68, 46), (50, 48, 68, 55), (50, 86, 68, 93), (50, 95, 68, 102), (50, 104, 68, 111)]
CAPS_H = [(25, 61, 31, 79), (33, 61, 39, 79), (41, 61, 47, 79), (73, 61, 79, 79), (81, 61, 87, 79), (89, 61, 95, 79)]
CORE = (52, 60, 67, 80)

# --- Heights --------------------------------------------------------------------------------------
BODY_Z = 0.20  # the cross slab's foot (0.03 under this, inside the kit's bed and deck)
STRIP = 6  # px: the kit's deck round the arms (the art's comb and weave there)
ARM_Z = 0.30  # the cross's top (enemy cells: 0.30..0.38)
BEZEL_Z = 0.342
LENS_Z = 0.362
CORE_Z = 0.370

# --- Palette indices (the art's own, per region: medians without the darkest / brightest) -------
I_ARM, I_ARM_EDGE = 6, 7
I_BEZEL = 8
I_LENS, I_CORE = 113, 113
I_LENS_HOT, I_CORE_HOT = 115, 116  # the art's brightest streaks: the glow's crest


def stadium(x0, y0, x1, y1, grow=0.0, segs=4):
    """A capsule's outline round a box (px): round ends on the short sides."""
    x0, y0, x1, y1 = x0 - grow, y0 - grow, x1 + grow, y1 + grow
    r = min(x1 - x0, y1 - y0) / 2
    return lb.Building.rounded_box(None, x0, y0, x1, y1, corner_px=r * 0.999, segments=segs)


def loft_cap(s, polys, mat, smooth=True, top_mat=None):
    """A closed, lofted solid through rings `polys` [(poly px, z), ...] (same vertex count), bottom
    and top capped: lens domes and the like."""
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(x), s.y(y), z)) for x, y in poly] for poly, z in polys]
    n = len(rings[0])
    top_mat = mat if top_mat is None else top_mat
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bm.faces.new(rings[-1]).material_index = top_mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=smooth)


def shrink(poly, cx, cy, k):
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


def cross(s):
    arm = s.m(I_ARM, metallic=0.5, roughness=0.45)
    edge = s.m(I_ARM_EDGE, metallic=0.5, roughness=0.4)
    side = s.m(3, metallic=0.4, roughness=0.55)
    vx0, vy0, vx1, vy1 = V_ARM
    hx0, hy0, hx1, hy1 = H_ARM
    c = 1.5  # outer corners cut
    poly = [(vx0 + c, vy0), (vx1 - c, vy0), (vx1, vy0 + c), (vx1, hy0), (hx1 - c, hy0), (hx1, hy0 + c), (hx1, hy1 - c),
            (hx1 - c, hy1), (vx1, hy1), (vx1, vy1 - c), (vx1 - c, vy1), (vx0 + c, vy1), (vx0, vy1 - c), (vx0, hy1),
            (hx0 + c, hy1), (hx0, hy1 - c), (hx0, hy0 + c), (hx0 + c, hy0), (vx0, hy0), (vx0, vy0 + c)]
    s.slab(poly, BODY_Z - 0.03, ARM_Z, arm, chamfer_px=1.0, drop=0.02, side_mat=side, bevel_mat=edge)
    # a raised rail (step) round the arm's edges: the art's light line framing the capsules
    bezel = s.m(I_BEZEL, metallic=0.65, roughness=0.32)
    lens = s.m(I_LENS, emission_strength=1.2, roughness=0.18, metallic=0.0)
    lens_hot = s.m(I_LENS_HOT, emission_strength=1.6, roughness=0.15, metallic=0.0)
    lens_rim = s.m(112, metallic=0.2, roughness=0.3)
    clamp = s.m(I_ARM_EDGE, metallic=0.55, roughness=0.38)
    for (x0, y0, x1, y1) in CAPS_V + CAPS_H:
        out = stadium(x0, y0, x1, y1, grow=1.3)
        s.rim(out, 1.5, ARM_Z - 0.01, BEZEL_Z, bezel, chamfer_px=0.5, drop=0.008)
        # dark well floor and the lens dome
        s.slab(stadium(x0, y0, x1, y1, grow=0.0), ARM_Z - 0.01, ARM_Z + 0.012, lens_rim, chamfer_px=0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        base = stadium(x0, y0, x1, y1, grow=-0.1, segs=6)
        rings = [(base, ARM_Z + 0.008)]
        for sc, z in ((0.97, LENS_Z - 0.022), (0.86, LENS_Z - 0.008), (0.62, LENS_Z)):
            # shrink the short side more than the long one: a pill-shaped glass top
            w, h = x1 - x0, y1 - y0
            kx = 1 - (1 - sc) * (min(w, h) / w) * 1.2
            ky = 1 - (1 - sc) * (min(w, h) / h) * 1.2
            rings.append(([(cx + (x - cx) * kx, cy + (y - cy) * ky) for x, y in base], z))
        loft_cap(s, rings, lens, top_mat=lens_hot)
    # clamps between neighbouring capsules (bridges on the bezels, as in the concept)
    for (a, b) in zip(CAPS_V, CAPS_V[1:]):
        if b[1] - a[3] < 6:
            ym = (a[3] + b[1]) / 2
            s.slab(s.rounded_box(56.5, ym - 1.0, 61.5, ym + 1.0, 0.4, 1), ARM_Z, BEZEL_Z + 0.006, clamp, chamfer_px=0.4, drop=0.006)
    for (a, b) in zip(CAPS_H, CAPS_H[1:]):
        if b[0] - a[2] < 6:
            xm = (a[2] + b[0]) / 2
            s.slab(s.rounded_box(xm - 1.0, 67.5, xm + 1.0, 72.5, 0.4, 1), ARM_Z, BEZEL_Z + 0.006, clamp, chamfer_px=0.4, drop=0.006)
    # bolts on the arm's tips
    flange = s.m(I_BEZEL, metallic=0.6, roughness=0.35)
    s.bolts([(50.5, 57.5), (69.5, 57.5), (50.5, 82.5), (69.5, 82.5)], ARM_Z, r_px=0.6, height=0.012, mat=flange)
    # The core: a chamfered square frame (rim), clamp plates on its sides, a dark well, the glowing lens
    x0, y0, x1, y1 = CORE
    frame = s.rounded_box(x0 - 2.2, y0 - 2.2, x1 + 2.2, y1 + 2.2, 2.6, 1)
    s.rim(frame, 2.4, ARM_Z - 0.01, CORE_Z - 0.006, bezel, chamfer_px=0.7, drop=0.01)
    s.slab(s.rounded_box(x0, y0, x1, y1, 1.6, 1), ARM_Z - 0.01, ARM_Z + 0.012, lens_rim, chamfer_px=0)
    core = s.m(I_CORE, emission_strength=1.6, roughness=0.15)
    base = s.rounded_box(x0 + 0.1, y0 + 0.1, x1 - 0.1, y1 - 0.1, 1.6, 2)
    ccx, ccy = (x0 + x1) / 2, (y0 + y1) / 2
    loft_cap(s, [(base, ARM_Z + 0.008), (shrink(base, ccx, ccy, 0.95), CORE_Z - 0.012), (shrink(base, ccx, ccy, 0.82), CORE_Z)], core,
             top_mat=s.m(I_CORE_HOT, emission_strength=1.8, roughness=0.12))
    for bx in ((ccx - 3, y0 - 3.2, ccx + 3, y0 - 0.8), (ccx - 3, y1 + 0.8, ccx + 3, y1 + 3.2),
               (x0 - 3.2, ccy - 3, x0 - 0.8, ccy + 3), (x1 + 0.8, ccy - 3, x1 + 3.2, ccy + 3)):
        s.slab(s.rounded_box(*bx, 0.5, 1), ARM_Z, CORE_Z + 0.002, clamp, chamfer_px=0.5, drop=0.008)


def mound(s, k):
    """The kit's rock mound and the deck strip round the cross (D148). Returns the footprint."""
    fp = s.footprint
    arms = s.box_mask(*V_ARM) | s.box_mask(*H_ARM)
    deck = kit.dil_disk(arms, STRIP) & fp
    k.bed(fp)
    k.deck(deck & ~arms)
    k.rock_field(fp & ~kit.dil4(deck, 1), fp, deck)
    k.kerb(deck, no_post=kit.dil4(arms, 1))
    n = k.paving(kit.ero_disk(deck, kit.KERB_W) & ~kit.dil4(arms, 1))
    k.rocks()
    k.no_needles()
    print(f"mound: {len(k.stones)} stones, {n} bricks")
    return fp


def objects_of(s, k):
    """The cross (s.parts, normals recalculated) and the kit's mound (oriented as built) as one
    object, without a terraced deck (as lib_tyrbld.Structure.objects does)."""
    coll = common.reset_collection(f"{lb.SHAPES}-{s.prefix}-{s.name}")
    bmesh.ops.recalc_face_normals(s.parts, faces=s.parts.faces)
    s._merge(k.g.bm)
    k.g.bm = bmesh.new()
    return [lb.mesh_object(f"{lb.SHAPES}-{s.prefix}-{s.name}-parts", s.parts, s.pal.materials, coll)]


def build(bake=True):
    lb.clear_scene()
    s = lb.Building("cross-pad")
    k = kit.Kit(s)
    fp = mound(s, k)
    cross(s)
    objects = objects_of(s, k)
    s.check(objects)
    iou = s.top_iou(objects, fp)
    tris = sum(len(p.vertices) - 2 for o in objects for p in o.data.polygons)
    print(f"RESULT iou={iou:.4f} tris={tris}")
    if bake:
        objects = s.bake_model(objects, ground=0.0, grit=kit.GRIT)
    if lt.preview_arg():
        lt.preview(s.ts, objects, s.pattern, Path(lt.preview_arg()) if str(lt.preview_arg()).endswith(".png") else Path(lt.preview_arg()) / "shapesz-l1bld-cross-pad.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv)
