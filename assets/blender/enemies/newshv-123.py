"""newshv-123 (red gem pod) and newshv-153 (its blue twin), (D50-D53, D65, D120, D122). Builds both gems: this script also writes newshv-153.

WHAT IT IS: a launched gem pod. newshv-123 is type 799, mv(0,1) with xAccel 92 (it drifts), launched
by 797 (the GEM WAR gunship's centre with the red gem) every 110 ticks; newshv-153 is type 802,
acc(94,94) cAccel(2,2) (it wanders and homes, and fires), launched by 807 (the centre with the blue
gem) every 30 ticks. Neither has a level spawn event (2.6/2.7). So it flies free: a round, closed
gem, never on the ground (the old docstrings' "meets the ground" is wrong).

THE SPRITE (24x28, newshv.shp size 2; 153 is the same drawing 16 indices lower, 64-79 -> 48-63):
a round disc 18 px across with a 1 px ink ring (64 / 48); inside it a 16 px circle (224 px) lit
bright in the middle (79) and darker toward the rim (69-72). A thin dark diamond (69-72; corners
on the axes, L1 radius ~5 px from the centre) and pale diagonal speckles (77-78). Frames 125/127
(155/157) are the same pixels 2 and 4 indices darker (a pulse); the ink ring stays.

THE MODEL (QA H4 rebuild): a domed, faceted cut gem, a brilliant seen from above. The sprite's
concentric diamonds are its facet rings, each a ring of flat, flat-shaded facets with crisp edges,
stepping down from a bright table to the round girdle (L1 radii in px from the centre, heights in px
above the midplane):
  table     flat diamond, L1 <= 2.3, z 4.75: the bright centre (78), a mild glow (D126 strength
            0.35) on a metallic, rough face (D173)
  star      L1 2.3 -> 4.7, about 25-28 degrees so the south facets glint under the game's sun and
            camera: a kite and two triangles per table edge, alternate facets 76 / 74 (ring 75)
  bezel     L1 4.7 -> 6.3 at the corners (deep, steep), only to L1 5.7 and about 12 degrees at the
            side mids: the sprite's dark diamond is this facet ring, not an engraved line, and like
            the sprite it is dark points, not an even frame: N 69, S 70, E/W 72, the diagonal
            sides 73 (the north two 74, which the game's sun leaves in shade)
  upper     the dark diamond's outer edge out to a 16-point ring halfway to the girdle; zig-zag
            facets alternating 77 / 75 (ring 76): the sprite's checker of pale speckles
  lower     from that ring down to the round girdle, facets alternating 74 / 72: the shaded rim (73)
  girdle    a thin polished band (72) at the silhouette
  pavilion  16 flat facets down to a culet: a plausible closed underside
The sprite's lit centre and darker rim come from the dome's lighting plus each ring's palette index;
its glints are sheen, not bumps. The girdle is a circle (R 8.38 px): the sprite's flat-sided mask is
a rasterised pixel circle, not a cushion cut. Glassy: dielectric, roughness 0.14, F0 about 0.08 through Specular
IOR Level 1.0 (D176; exported as KHR_materials_specular). One geometry for all three frames; every
material steps 2 / 4 indices darker on the pulse frames. Blue twin: the same indices 16 lower.
No AO/roughness bake (a polished gem gains nothing from one); the outline shell (D51, D90/D118) is
made from a sealed copy of the whole (closed) body.

Exports public/models/enemies/newshv-123.glb and newshv-153.glb and their spriteModels entries.

Run: blender --background --python assets/blender/enemies/newshv-123.py [-- --renders <dir>]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402

WT = common.repo_root(__file__)

U = 1 / 12            # one sprite px in model units
N = 64                # points per ring; a multiple of 4 so the diamond's corners sit on the axes

R = 8.38              # silhouette (girdle) radius, px
SQ = 2.0              # ... and its superellipse exponent: 2 is a true circle. The 18 px sprite mask's
                      # flat sides are how a pixel circle rasterises, not square corners (a 2.4
                      # superellipse read as a cushion cut in game). A circle of radius 8.3-8.45
                      # scores grid IoU 0.964 / 0.969 / 0.977 on the three frames; 8.38 sits mid-band
R_CROWN = 8.13        # where the crown meets the girdle, px
Z_GIRDLE_TOP = 0.6    # girdle top, px above the midplane
Z_GIRDLE_BOT = -0.7   # girdle bottom
D_PAV = 5.6           # culet below the midplane, px
# facet rings on the sprite's concentric diamonds: (L1 radius px, z at the corners, z at the side mids)
TABLE = (2.3, 4.75, 4.75)
STAR = (4.7, 3.55, 3.9)   # star facets about 25-28 deg: the south ones face the half-vector of the
                          # game's sun and camera (sun.ts / view.ts), so they glint
BEZEL = (6.3, 2.55, 3.75) # deep, steep and dark at the diamond's corners; shallow (~12 deg) at its sides,
BEZEL_SIDE_L1 = 5.7       # ... and narrower there (its side points at L1 5.7): the sprite's dark
                          # diamond is dark blobs at N/S (69-70), lighter at E/W (71-72) and mid-tone
                          # along the diagonals (72-74), not an even drawn frame
UPPER_T = 0.5         # the upper/lower facet ring sits this far from the bezel to the girdle ...
UPPER_SAG = 0.36      # ... and drops this share of the height between them (a convex dome: < 0.5)
UPPER_ZIG = 0.22      # odd points of that ring this much higher, even ones lower: kite facets

(TABLE_M, STAR_A, STAR_B, BEZEL_M, UPPER_A, UPPER_B, LOWER_A, LOWER_B, GIRDLE_M, PAV_M, BEZEL_SIDE, BEZEL_EW,
 BEZEL_SIDE_N, BEZEL_S) = range(14)
STAR_M, UPPER_M, LOWER_M = (STAR_A, STAR_B), (UPPER_A, UPPER_B), (LOWER_A, LOWER_B)
FACET_STEP = 1         # alternate facets of a ring one index above / below the ring's own index: the
                       # sprite's checker of pale speckles (77-78) among 74-75 is per-facet sparkle


def sq(a):
    """The silhouette's radius at angle a relative to its radius on the axes (1 on the axes)."""
    c, s = abs(math.cos(a)), abs(math.sin(a))
    return 1.0 / (c ** SQ + s ** SQ) ** (1.0 / SQ)


def flat_ring(r, z, n=N):
    """A level ring of the silhouette's shape, r px on the axes."""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        out.append((r * sq(a) * math.cos(a), r * sq(a) * math.sin(a), z))
    return out


def diamond_r(s, a):
    """Radius of the diamond |x| + |y| = s at angle a."""
    return s / (abs(math.cos(a)) + abs(math.sin(a)))


def diamond_ring(spec, n=8):
    """n points on a diamond facet ring (corners on the axes), corners at z_c, side mids at z_m."""
    s, zc, zm = spec
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        # height: corners zc, side mids zm, linear along the side in between
        t = abs(((a / (math.pi / 2)) % 1.0) - 0.5) * 2   # 1 at a corner, 0 mid-side
        r = diamond_r(s, a)
        out.append((r * math.cos(a), r * math.sin(a), zm + (zc - zm) * t))
    return out


def build_bm():
    """The whole gem as one closed bmesh (px units, scaled to U later); faces carry material ids."""
    bm = bmesh.new()

    count = [0]

    def face(vs, m, smooth=False):
        if isinstance(m, tuple):          # a ring with alternating facets
            m = m[count[0] % 2]
            count[0] += 1
        f = bm.faces.new(vs)
        f.material_index, f.smooth = m, smooth
        return f

    def verts(pts):
        return [bm.verts.new(p) for p in pts]

    def bridge(a, b, m):
        """Facets between ring a (n points) and ring b (k*n points, same start angle), outward."""
        n, k = len(a), len(b) // len(a)
        for i in range(n):
            j = (i + 1) % n
            if k == 1:
                # a quad folded into two flat triangles; the fold alternates (a star pattern)
                if i % 2 == 0:
                    face((a[i], b[i], b[j]), m)
                    face((a[i], b[j], a[j]), m)
                else:
                    face((a[i], b[i], a[j]), m)
                    face((a[j], b[i], b[j]), m)
                continue
            base = i * k
            for q in range(k):
                bi, bj = b[(base + q) % len(b)], b[(base + q + 1) % len(b)]
                face((a[i] if q < k // 2 else a[j], bi, bj), m)
            face((a[i], b[(base + k // 2) % len(b)], a[j]), m)

    table = verts(diamond_ring(TABLE))
    face(table, TABLE_M)                      # one flat polished table
    star = verts(diamond_ring(STAR, 16))     # corners, quarter points and side mids
    bridge(table, star, STAR_M)              # star facets: a kite and two triangles per table edge
    b16 = diamond_ring(BEZEL, 16)
    for i in range(16):                      # pull the side and quarter points in: a narrower band there
        if i % 4:
            x, y, z = b16[i]
            f = BEZEL_SIDE_L1 / BEZEL[0] if i % 4 == 2 else (1 + BEZEL_SIDE_L1 / BEZEL[0]) / 2
            b16[i] = (x * f, y * f, z)
    ring16 = verts(b16)
    # the bezel: one quad per quarter side, symmetric about each corner. Point 0 is E, 4 N, 8 W, 12 S.
    # The sprite's dark diamond is darkest at N/S (69-70), 71-72 at E/W, mid-tone (72-74) on the sides
    for i in range(16):
        j = (i + 1) % 16
        # N corner darkest (69); S corner 70; E/W 72; the diagonal sides 73, the two north ones 74 as
        # they face away from the game's sun and its lighting darkens them
        m = BEZEL_SIDE_N if i in (1, 2, 5, 6) else BEZEL_SIDE
        if i in (3, 4):
            m = BEZEL_M
        elif i in (11, 12):
            m = BEZEL_S
        elif i in (15, 0, 7, 8):
            m = BEZEL_EW
        for tri in ((star[i], ring16[i], ring16[j]), (star[i], ring16[j], star[j])):
            face(tri, m)
    # the upper facet ring: halfway from the bezel to the girdle; its points alternately higher and
    # lower (UPPER_ZIG), so the facets fold into kites
    up = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        p = ring16[i].co
        rb = math.hypot(p.x, p.y)
        rr = R_CROWN * sq(a)
        r = rb + (rr - rb) * UPPER_T
        z = p.z - (p.z - Z_GIRDLE_TOP) * UPPER_SAG + (UPPER_ZIG if i % 2 else -UPPER_ZIG)
        up.append((r * math.cos(a), r * math.sin(a), z))
    upper = verts(up)
    # bezel (16, collinear on the diamond's sides) -> upper (16): folded quads
    for i in range(16):
        j = (i + 1) % 16
        if i % 2 == 0:
            face((ring16[i], upper[i], upper[j]), UPPER_M)
            face((ring16[i], upper[j], ring16[j]), UPPER_M)
        else:
            face((ring16[i], upper[i], ring16[j]), UPPER_M)
            face((ring16[j], upper[i], upper[j]), UPPER_M)
    rim = verts(flat_ring(R_CROWN, Z_GIRDLE_TOP))
    bridge(upper, rim, LOWER_M)

    # girdle: chamfered lips and a thin band; then a faceted pavilion to the culet
    rings = [rim]
    spec = [(flat_ring(R, Z_GIRDLE_TOP - 0.15), GIRDLE_M), (flat_ring(R, Z_GIRDLE_BOT + 0.15), GIRDLE_M),
            (flat_ring(R_CROWN, Z_GIRDLE_BOT), GIRDLE_M)]
    for ring, m in spec:
        vs = verts(ring)
        prev = rings[-1]
        for i in range(N):
            j = (i + 1) % N
            face((prev[i], vs[i], vs[j], prev[j]), m)
        rings.append(vs)
    # pavilion: 16 main facets to a 16-point ring 55% of the way, then 16 facets to the culet
    pav = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        r = R_CROWN * sq(a) * 0.5
        pav.append((r * math.cos(a), r * math.sin(a), Z_GIRDLE_BOT - (D_PAV + Z_GIRDLE_BOT) * 0.62))
    pav = verts(pav)
    k = N // 16
    for i in range(16):
        j = (i + 1) % 16
        for q in range(k):
            bi, bj = rings[-1][(i * k + q) % N], rings[-1][(i * k + q + 1) % N]
            face((pav[i] if q < k // 2 else pav[j], bj, bi), PAV_M)
        face((pav[i], pav[j], rings[-1][(i * k + k // 2) % N]), PAV_M)
    culet = bm.verts.new((0.0, 0.0, -D_PAV))
    for i in range(16):
        face((pav[(i + 1) % 16], pav[i], culet), PAV_M)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(U, U, U), verts=bm.verts)
    return bm


def load_sprite(name):
    return common.load_sprite(WT, name)


def zone(x, y):
    """The sprite region of pixel (x, y) (centre at pixel corner 12, 14): the facet ring above it."""
    dx, dy = x + 0.5 - 12, y + 0.5 - 14
    l1, r = abs(dx) + abs(dy), math.hypot(dx, dy)
    if r > 7.0:
        return "rim"
    if l1 < TABLE[0]:
        return "table"
    if l1 < STAR[0] - 0.1:
        return "star"
    if l1 < BEZEL[0]:
        return "bezel"
    return "upper"


def region_colours(sprite):
    """The sprite's own index per facet ring, on frame 0: the median of its pixels (ink left out).
    The bezel is the sprite's dark diamond line: the median of that band's darker half."""
    px = [[int(v) for v in row.split()] if isinstance(row, str) else row for row in sprite["frames"][0]["pixels"]]
    ink = min(int(k) for k in sprite["colors"])
    zones = {}
    for y, row in enumerate(px):
        for x, v in enumerate(row):
            if v >= 0 and v != ink:
                zones.setdefault(zone(x, y), []).append(v)
    med = {k: sorted(v)[len(v) // 2] for k, v in zones.items()}
    dark = sorted(zones["bezel"])[: len(zones["bezel"]) // 2]
    med["bezel"] = dark[len(dark) // 2]
    print("region medians", med)
    return med


def build(sprite, name):
    coll = common.reset_collection(name)
    frames = [f["index"] for f in sprite["frames"]]
    c = region_colours(sprite)
    print(name, "region indices", c)

    def pal(i, part, roughness=0.14, spec=1.0, metallic=0.0, glow=0.0):
        m = common.palette_material(sprite, i, f"{name}-{part}", metallic=metallic, roughness=roughness,
                                    emission_strength=glow, frames={frames[1]: i - 2, frames[2]: i - 4})
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:   # D176: a polished gem's F0 (~0.08, IOR ~1.76)
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    k = FACET_STEP
    mats = [
        # the bright core: a mild glow (D126: 35% glow, 65% lit) on a metallic, rough face (D173: a
        # glow on a glossy dielectric shows only its reflection)
        pal(c["table"], "table", 0.6, 0.5, 1.0, 0.35),
        pal(c["star"] + k, "star_a"), pal(c["star"] - k, "star_b"),
        pal(c["bezel"] - 2, "bezel"),
        pal(c["upper"] + k, "upper_a"), pal(c["upper"] - k, "upper_b"),
        pal(c["rim"] + k, "lower_a"), pal(c["rim"] - k, "lower_b"),
        pal(c["rim"] - 1, "girdle", 0.25, 0.8),
        pal(c["rim"] - 1, "pavilion", 0.2, 0.8),
        pal(c["bezel"] + 2, "bezel_side"),
        pal(c["bezel"] + 1, "bezel_ew"),
        pal(c["bezel"] + 3, "bezel_side_n"),
        pal(c["bezel"] - 1, "bezel_s"),
    ]
    obj = common.mesh_object(name, build_bm(), mats, coll, smooth=None)
    shell = common.outline_shell(obj, coll, voxel=0.008, faces=1600, smooth=4, inside=0.006)
    return [obj, shell]


# --- review renders ------------------------------------------------------------------------------
def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def set_frame_colours(objs, frame):
    for o in objs:
        for m in o.data.materials:
            if m is None:
                continue
            if "base_rgb" not in m:
                m["base_rgb"] = list(m.diffuse_color[:3])
            rgb = m.get("tyrian_frame_rgb", {}).get(str(frame))
            m.diffuse_color = (*(rgb if rgb is not None else m["base_rgb"]), 1.0)


def renders(objs, sprite, out):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.color_type = "MATERIAL"
    scene.render.resolution_percentage = 100
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.05, 0.05, 0.06)
    shell = [o for o in objs if o.get("tyrian_outline")]
    out.mkdir(parents=True, exist_ok=True)
    frames = [f["index"] for f in sprite["frames"]]

    # top_flat: unlit palette colours on the sprite grid (12 image px per sprite px), no shell
    for o in shell:
        o.hide_render = True
    sh.light = "FLAT"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 24 * 12, 28 * 12
    top = camera(scene, "cam_top", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    for f in frames:
        set_frame_colours(objs, f)
        scene.render.filepath = str(out / f"top_flat_{f}.png")
        bpy.ops.render.render(write_still=True)

    sh.light = "STUDIO"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_specular_highlight = True
    scene.render.film_transparent = False
    scene.render.resolution_x = scene.render.resolution_y = 480
    d = 4.0
    o = 1.9
    views = {
        "top": camera(scene, "v_top", (0, 0, 10), (0, 0, 0), ortho=o),
        "game": camera(scene, "v_game", (0, -d * 0.55, d * 0.85), (0, 0, 0)),
        "q34": camera(scene, "v_q34", (d * 0.62, -d * 0.55, d * 0.55), (0, 0, 0)),
        "q34r": camera(scene, "v_q34r", (-d * 0.62, d * 0.6, d * 0.5), (0, 0, 0)),
        "side": camera(scene, "v_side", (d, 0, 0), (0, 0, 0), ortho=o),
        "front": camera(scene, "v_front", (0, -d, 0), (0, 0, 0), ortho=o),
        "rear": camera(scene, "v_rear", (0, d, 0), (0, 0, 0), ortho=o),
        "under": camera(scene, "v_under", (0.3, -d * 0.4, -d * 0.85), (0, 0, 0)),
    }
    views["top"].rotation_euler = (0, 0, 0)
    for f in (frames[0], frames[2]):
        set_frame_colours(objs, f)
        for k, cam in views.items():
            if f != frames[0] and k not in ("game", "q34"):
                continue
            scene.camera = cam
            scene.render.filepath = str(out / f"{k}_{f}.png")
            bpy.ops.render.render(write_still=True)
    set_frame_colours(objs, frames[0])
    for o in shell:
        o.hide_render = False


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    for name in ("newshv-123", "newshv-153"):
        sprite = load_sprite(name)
        objs = build(sprite, name)
        print(f"{name}: body {tris(objs[0])} tris, shell {tris(objs[1])} tris")
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprite["sprites"])
        if "--renders" in argv:
            renders(objs, sprite, Path(argv[argv.index("--renders") + 1]) / name)
        for o in objs:
            o.hide_render = True
            o.hide_set(True)


if __name__ == "__main__":
    main()
