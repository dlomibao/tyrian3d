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

THE MODEL: a cut gem in a machined setting ring.
  table     flat, 3.75 px above the girdle, out to the sprite's dark diamond (fix round 1: the
            first build's 6.8 px dome hid the diamond's far half over its crest at the game camera)
  diamond   the table's edge: a modelled 1.3 px wide V panel line (0.22 px deep) along the
            sprite's dark diamond, in the diamond's own index (surface detail, not relief)
  crown     planar, flat-shaded facets from the table down to the girdle: per quadrant a kite off
            the diamond side folded along the diagonal (where the sprite's pale X glints are) and
            two facets each side of every corner (creases every 22.5 degrees). Lit from
            above they give the sprite's light centre and darker rim; the glints are sheen, not bumps
  girdle    a satin metal setting band at the silhouette, 1.4 px tall, a hair proud of the crown
            and pavilion with chamfered lips (the side/front/rear detail the camera sees)
  pavilion  a rounded cone below, 6 px deep, to a blunt culet: a plausible closed underside
One geometry for all three frames; every material steps 2 / 4 indices darker on the pulse frames.
Colours (trimmed medians of the sprite's regions, see region_colours): crown and pavilion 75 (build output),
diamond 72, girdle 73 (the sprite's pixels just inside the ink ring); blue 59 / 56 / 57.
No textures/<name>/ folder exists, so no AO/roughness bake (a smooth glossy gem gains nothing from
one); the outline shell (D51) is made from a sealed copy of the whole (closed) body.

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

R = 8.2               # silhouette (girdle) radius on the axes, px
SQ = 2.4              # ... and its superellipse exponent: the sprite's 224 px inner disc is a little
                      # fuller on the diagonals than a circle; n 2.4 / a 8.2 is the roundest fit with
                      # grid IoU 1.0 (a circle tops out at 0.964, n 2.8 fits best but reads squarish)
R_CROWN = 7.9         # where the crown meets the girdle's top lip, px (on the axes)
Z_GIRDLE_TOP = 0.55   # girdle top, px above the midplane
Z_GIRDLE_BOT = -0.85  # girdle bottom
H_TABLE = 4.3         # the flat table inside the diamond, px above the midplane (fix round 1: the old
                      # 6.8 px dome put the far half of the diamond over its crest at the game camera,
                      # so the diamond read as a chevron and the gem as a gumdrop)
D_PAV = 5.8           # culet below the midplane, px
GROOVE = (4.85, 5.35, 5.65, 6.15)   # diamond panel line, L1 radii in px: lip, floor, floor, lip
DEPTH = 0.22          # its depth, px
STAR_R = 6.3          # the kite's raised point on each diagonal, px from the centre (on the axes' scale)
STAR_Z = 2.9          # ... and its height: above the plane of the side and the girdle, so the kite folds
                      # along the diagonal (the sprite's pale X glints sit on that crease)

BODY, GROOVE_M, GIRDLE = 0, 1, 2


def sq(a):
    """The silhouette's radius at angle a relative to its radius on the axes (1 on the axes)."""
    c, s = abs(math.cos(a)), abs(math.sin(a))
    return 1.0 / (c ** SQ + s ** SQ) ** (1.0 / SQ)


def flat_ring(r, z):
    """A level ring of the silhouette's shape, r px on the axes."""
    out = []
    for i in range(N):
        a = 2 * math.pi * i / N
        out.append((r * sq(a) * math.cos(a), r * sq(a) * math.sin(a), z))
    return out


def diamond_ring(s, z):
    """The diamond's four corners (on the axes), L1 radius s px, level at z."""
    return [(s, 0.0, z), (0.0, s, z), (-s, 0.0, z), (0.0, -s, z)]


def build_bm():
    """The whole gem as one closed bmesh (px units, scaled to U later); faces carry material ids.

    Crown (fix round 1): a flat table out to the diamond, the diamond panel line cut into it, and
    planar flat-shaded facets from the table's four corners and four sides down to the girdle:
    per quadrant a kite off the diamond side (a shallow star facet to a raised point on the diagonal,
    folded down the diagonal to the girdle, where the sprite's pale X glints are) and two facets each
    side of every corner, split at 22.5 degrees. Low and hard-edged; no speckle bumps."""
    g0, g1, g2, g3 = GROOVE
    bm = bmesh.new()

    def face(vs, m, smooth):
        f = bm.faces.new(vs)
        f.material_index, f.smooth = m, smooth
        return f

    # table + diamond panel line (4-corner rings: straight-sided, flat shaded)
    centre = bm.verts.new((0.0, 0.0, H_TABLE))
    dr = [[bm.verts.new(p) for p in diamond_ring(s, H_TABLE - d)]
          for s, d in ((g0, 0.0), (g1, DEPTH), (g2, DEPTH), (g3, 0.0))]
    for i in range(4):
        face((centre, dr[0][i], dr[0][(i + 1) % 4]), BODY, False)
    for k in range(3):
        for i in range(4):
            j = (i + 1) % 4
            face((dr[k][i], dr[k + 1][i], dr[k + 1][j], dr[k][j]), GROOVE_M, False)
    corners = dr[3]

    # crown rim (level, the silhouette's shape) and the faceted crown down to it
    rim = [bm.verts.new(p) for p in flat_ring(R_CROWN, Z_GIRDLE_TOP)]
    q4 = N // 4
    for q in range(4):
        a, b = corners[q], corners[(q + 1) % 4]
        base = q * q4
        for k in range(q4):
            i, j = base + k, (base + k + 1) % N
            apex = a if k < q4 // 2 else b
            face((apex, rim[i], rim[j]), BODY, False)
        # the kite off the diamond side: a shallow star facet from the side to a raised point on the
        # diagonal, then two steeper facets meeting in a crease down the diagonal to the girdle
        ad = 2 * math.pi * (base + q4 // 2) / N
        rm = STAR_R * sq(ad)
        m = bm.verts.new((rm * math.cos(ad), rm * math.sin(ad), STAR_Z))
        g = rim[base + q4 // 2]
        face((a, m, b), BODY, False)
        face((a, g, m), BODY, False)
        face((m, g, b), BODY, False)

    # girdle: a step out to its chamfered top lip, the band, the chamfered bottom lip, a step in;
    # then the pavilion, a rounded cone to a blunt culet (smooth: a plausible closed underside)
    rings = [rim]
    spec = [(flat_ring(R - 0.15, Z_GIRDLE_TOP), GIRDLE), (flat_ring(R, Z_GIRDLE_TOP - 0.15), GIRDLE),
            (flat_ring(R, Z_GIRDLE_BOT + 0.15), GIRDLE), (flat_ring(R - 0.15, Z_GIRDLE_BOT), GIRDLE),
            (flat_ring(R - 0.35, Z_GIRDLE_BOT), GIRDLE)]
    for k in range(1, 9):
        phi = math.radians(10 * k)
        spec.append((flat_ring((R - 0.35) * math.cos(phi), Z_GIRDLE_BOT - (D_PAV + Z_GIRDLE_BOT) * math.sin(phi)), BODY))
    smooth_m = {BODY: True, GIRDLE: False}
    for ring, m in spec:
        vs = [bm.verts.new(p) for p in ring]
        prev = rings[-1]
        for i in range(N):
            j = (i + 1) % N
            face((prev[i], vs[i], vs[j], prev[j]), m, smooth_m[m])
        rings.append(vs)
    culet = bm.verts.new((0.0, 0.0, -D_PAV))
    for i in range(N):
        face((rings[-1][i], culet, rings[-1][(i + 1) % N]), BODY, True)
    bmesh.ops.scale(bm, vec=(U, U, U), verts=bm.verts)
    return bm


def load_sprite(name):
    return common.load_sprite(WT, name)


def trimmed_median(vals, colors):
    """Median palette index of a region, without its darkest and brightest 15% (lighting)."""
    luma = lambda i: sum(w * c for w, c in zip((0.299, 0.587, 0.114), colors[str(i)]))
    s = sorted(vals, key=luma)
    k = int(len(s) * 0.15)
    s = s[k:len(s) - k] if len(s) > 6 else s
    return s[len(s) // 2]


def region_colours(sprite):
    """The sprite's own index per region, on frame 0 (centre at pixel corner 12, 14)."""
    px = sprite["frames"][0]["pixels"]
    ink = min(int(k) for k in sprite["colors"])
    body, groove, rim = [], [], []
    for y, row in enumerate(px):
        for x, v in enumerate(row):
            if v < 0 or v == ink:
                continue
            dx, dy = x + 0.5 - 12, y + 0.5 - 14
            l1, r = abs(dx) + abs(dy), math.hypot(dx, dy)
            near_ink = any(0 <= y + b < len(px) and 0 <= x + a < len(row) and px[y + b][x + a] == ink
                           for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near_ink:
                rim.append(v)
            elif GROOVE[0] - 0.3 <= l1 <= GROOVE[3] + 0.3:
                groove.append(v)
            else:
                body.append(v)
    c = sprite["colors"]
    # the crown covers the rim pixels too from above (the girdle is ~0.3 px of the top view), so they
    # count toward its colour; the girdle's own side is unseen in the sprite and takes the rim's index
    b = trimmed_median(body + rim, c)
    # the line is the band's dark pixels (the band also crosses the pale diagonal speckles: sheen)
    line = [v for v in groove if v < b - 1]
    print("groove band", sorted(groove), "line", sorted(line))
    return b, sorted(line)[len(line) // 2], trimmed_median(rim, c)


def build(sprite, name):
    coll = common.reset_collection(name)
    frames = [f["index"] for f in sprite["frames"]]
    body_i, groove_i, rim_i = region_colours(sprite)
    print(name, "region indices body/groove/rim", body_i, groove_i, rim_i)

    def pal(i, part, **kw):
        return common.palette_material(sprite, i, f"{name}-{part}", frames={frames[1]: i - 2, frames[2]: i - 4}, **kw)

    mats = [
        pal(body_i, "gem", metallic=0.05, roughness=0.2),      # glossy gem: the lights make its sheen
        pal(groove_i, "line", metallic=0.05, roughness=0.35),  # the diamond panel line
        pal(rim_i, "girdle", metallic=0.6, roughness=0.38),    # satin metal setting band
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
