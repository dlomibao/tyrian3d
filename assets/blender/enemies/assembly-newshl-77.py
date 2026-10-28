"""Grey thruster tower (newshl.shp 77 and 79, side by side): a 3D version of its sprites.

Seen in episode 4, level 40. Two 2x2 sprites make one symmetric object 25 px wide (centred on the
seam's right-hand column): the lower end of a grey machine. Down the screen it has a narrow neck
with red lights (rows 0-6), a wide rounded tier with a dark slot across it (rows 7-11), a groove,
a narrower band, another groove, a second wide tier with a bright upper rim (rows 16-19) and a
glowing red exhaust bar at the bottom (rows 21-22). It is lofted down the screen as stacked lens
discs about 9 px thick with pointed side tips (domed along the screen too, their tops painted with the
sprite's own greys), the collar between them about 3 px lower, a broad flat-topped
wedge down the neck, the slot and the collar's intake cut in (boolean), then cut into the two pieces
(newshl-77 left, newshl-79 right).

Run: blender --background --python assets/blender/enemies/assembly-newshl-77.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "assembly-newshl-77"
PIECES = ["newshl-77", "newshl-79"]
ROOT = common.repo_root(__file__)
LOWEST = 5

# Rings are lofted down the screen at sprite rows (pixel-row centres, fractional rows allowed), each
# (row, half width left px, half width right px, half height px). The outline follows the sprite's
# own per-row extent (it is not quite symmetric: the right side carries shadow pixels). A ring's
# shape exponent K gives its section: 1 = ellipse, > 1 = a lens thinning to pointed side tips,
# < 1 = a boxy slab.
NECK = [(-0.5, 11.5, 11.5, 1.8), (0.0, 11.5, 11.4, 2.0), (0.5, 10.5, 9.8, 2.2), (1.0, 9.5, 8.5, 2.4),
        (2.0, 7.5, 7.5, 2.6), (3.0, 7.3, 7.5, 2.6), (4.0, 5.8, 8.3, 2.5), (5.0, 6.4, 6.6, 2.5),
        (6.0, 7.5, 8.4, 2.7), (6.7, 8.5, 9.0, 2.9)]
# The forward saucer is a low dome along the screen too: its crest (4.5 px) a little behind the
# middle, falling to a bevelled front edge and to about 3 px at the back above the collar.
SAUCER = [(6.55, 9.5, 9.5, 1.5), (7.0, 10.5, 10.5, 2.5), (7.6, 11.1, 11.1, 3.4), (8.3, 11.8, 11.8, 4.05),
          (9.2, 12.5, 12.5, 4.6), (10.2, 12.5, 12.5, 4.55), (11.0, 12.5, 12.5, 4.0), (11.55, 12.0, 12.0, 3.2)]
# The waist collar: one drum, its top about 1.45 px (3 px below the saucer crests), its front and
# back rows shadowed under the tiers above it.
COLLAR = [(11.4, 7.5, 10.4, 1.0), (12.0, 7.5, 10.4, 1.3), (12.5, 8.5, 10.4, 1.45), (13.0, 8.5, 10.4, 1.5),
          (14.0, 10.5, 10.4, 1.5), (14.6, 9.5, 10.4, 1.45), (15.0, 9.5, 10.4, 1.3), (15.6, 9.5, 10.4, 1.0)]
DISC = [(15.5, 10.0, 10.5, 2.2), (15.85, 12.2, 12.2, 3.3), (16.4, 12.6, 12.6, 4.1), (17.3, 12.6, 12.6, 4.4),
        (18.0, 11.6, 11.6, 4.1), (18.6, 10.6, 10.6, 3.7), (19.0, 9.5, 9.5, 3.2), (19.5, 8.0, 8.0, 2.3)]
TAIL_GROOVE = [(19.4, 6.5, 5.4, 1.6), (20.6, 6.5, 5.4, 1.3)]
ENGINE = [(20.5, 7.0, 7.0, 0.8), (20.8, 7.5, 7.5, 1.1), (22.2, 7.5, 7.5, 1.1), (22.5, 7.0, 7.0, 0.8)]
# The broad, low wedge down the neck's centre (the lighter V of rows 0-8: 2 px wide at the front,
# about 5 px at the back), flat-topped and about 1.3 px proud, running up over the saucer's front
# bevel and dying into its dome: (row, centre column, top half width, base half width, top px,
# base px).
RIDGE = [(-0.5, 23.5, 0.7, 1.5, 3.0, 1.2), (3.0, 23.6, 1.0, 2.1, 3.8, 1.6), (5.5, 23.9, 1.7, 3.0, 4.0, 1.6),
         (7.2, 24.0, 2.0, 3.3, 4.2, 2.0), (8.4, 24.0, 1.6, 3.0, 4.0, 2.4)]


def ring_loft(bm, grid, axis, sections, k, sides=24, mat_index=0):
    """Loft rings along the screen; returns the faces made. Sections as in the tables above."""
    rings = []
    for r, wl, wr, h in sections:
        y = grid.y(r)
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            c, s = math.cos(a), math.sin(a)
            w = wr if c > 0 else wl
            z = h * math.copysign(abs(s) ** k, s)
            ring.append(bm.verts.new((axis + w * c * lib.U, y, z * lib.U)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat_index
        f.normal_update()
    return faces


def ridge(bm, grid, sections, top_mat, side_mat):
    """A flat-topped wedge: a trapezoid section (lit flanks, flat top) closed by a keel buried in the
    neck. Sections as in RIDGE."""
    rings = []
    for r, c, tw, bw, top, base in sections:
        x, y = grid.x(c), grid.y(r)
        rings.append([bm.verts.new((x + dx * lib.U, y, z * lib.U))
                      for dx, z in ((bw, base), (tw, top), (-tw, top), (-bw, base), (0.0, 0.0))])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(5):
            j = (i + 1) % 5
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = top_mat if i == 1 else side_mat
    bm.faces.new(list(reversed(rings[0]))).material_index = side_mat
    bm.faces.new(rings[-1]).material_index = side_mat


def cut(obj, coll, mats, boxes):
    """Boolean-subtract axis-aligned boxes ((x0, y0, x1, y1, z0, z1, material slot)) from obj; the
    recess walls and floor take the box's material."""
    bm = bmesh.new()
    for x0, y0, x1, y1, z0, z1, m in boxes:
        lib.box(bm, x0, y0, x1, y1, z0, z1, mat_index=m)
    cutter = common.mesh_object(obj.name + "-cutter", bm, mats.list, coll)
    mod = obj.modifiers.new("recess", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)


def build(sprites):
    coll = common.reset_collection(NAME)
    pixels = [list(a) + list(b) for a, b in zip(sprites[0]["frames"][0]["pixels"], sprites[1]["frames"][0]["pixels"])]
    grid = lib.Grid(48, 28, pixels)
    mats = lib.Mats(NAME, lib.merged_colors(sprites))
    neck = mats(6, metallic=0.35, roughness=0.45)
    wedge = mats(7, metallic=0.35, roughness=0.4)
    wedge_side = mats(10, metallic=0.35, roughness=0.4)
    saucer = mats(9, metallic=0.35, roughness=0.45)
    collar_back = mats(5, metallic=0.4, roughness=0.6)
    band = mats(6, metallic=0.35, roughness=0.45)
    disc = mats(7, metallic=0.35, roughness=0.45)
    shadow = mats(3, metallic=0.4, roughness=0.6)
    black = mats(2, metallic=0.3, roughness=0.7)
    floor = mats(4, metallic=0.4, roughness=0.6)
    rim_hi = mats(14, metallic=0.1, roughness=0.45)
    rim_mid = mats(12, metallic=0.1, roughness=0.45)
    glow = {i: mats(i, metallic=0.0, roughness=0.4, emission_strength=3.5) for i in (116, 118, 121)}
    light_a = mats(116, metallic=0.0, roughness=0.4, emission_strength=3.0)
    light_b = mats(118, metallic=0.0, roughness=0.4, emission_strength=3.0)
    axis = grid.x(24)

    greys = {saucer, disc}

    def shade(idx, default):
        """The sprite's own grey for an upward face (its lit spots and shaded edges), kept out of the
        darkest shades the lighting already gives and off the olive 8."""
        if idx is None or not 3 <= idx <= 15:
            return default
        idx = max(idx, LOWEST)
        slot = mats(7 if idx == 8 else idx, metallic=0.35, roughness=0.45)
        greys.add(slot)
        return slot

    def obj_of(bm, tag):
        return common.mesh_object(f"{NAME}-{tag}", bm, mats.list, coll)

    # The forward saucer: a domed lens 9 px thick with pointed side tips; the lit spot of row 11
    # (columns 16-18) painted on its upper face, and the dark slot of rows 10-11 (columns 20-28) cut
    # into its back edge, open toward the collar below it: a deeper shadowed front row (10) and a
    # shallower floor behind it (row 11).
    bm = bmesh.new()
    faces = ring_loft(bm, grid, axis, SAUCER, k=1.8, mat_index=saucer)
    for f in faces:
        c = f.calc_center_median()
        if c.z < 1.5 * lib.U or f.normal.z < 0.3:
            continue
        f.material_index = shade(grid.sample(c.x, c.y), saucer)
    saucer_obj = obj_of(bm, "saucer")
    cut(saucer_obj, coll, mats, [(grid.x(19.5), grid.y(9.5), grid.x(28.5), grid.y(10.5),
                                  2.6 * lib.U, 0.5, shadow)])
    cut(saucer_obj, coll, mats, [(grid.x(19.5), grid.y(10.45), grid.x(28.5), grid.y(12.5),
                                  2.9 * lib.U, 0.5, floor)])

    # The waist collar: one drum about 3 px below the saucer crests, shadowed in its front and back
    # rows (12 and 15), with the intake of rows 13-14 (columns 30-33) cut in.
    bm = bmesh.new()
    faces = ring_loft(bm, grid, axis, COLLAR, k=1.2, mat_index=band)
    for f in faces:
        c = f.calc_center_median()
        if c.y > grid.y(12.4):
            f.material_index = shadow
        elif c.y < grid.y(14.7):
            f.material_index = collar_back
    collar_obj = obj_of(bm, "collar")
    cut(collar_obj, coll, mats, [(grid.x(29.5), grid.y(12.6), grid.x(33.5), grid.y(14.5),
                                  0.2 * lib.U, 0.5, black)])

    bm = bmesh.new()
    ring_loft(bm, grid, axis, NECK, k=1.2, sides=20, mat_index=neck)
    ridge(bm, grid, RIDGE, wedge, wedge_side)
    # The rear disc: an 8.8 px lens whose narrow front bevel (row 16) carries the lit rim, the
    # sprite's own shades from near-white on the left fading to dark on the right; its back half
    # stays plain.
    faces = ring_loft(bm, grid, axis, DISC, k=1.8, mat_index=disc)
    for f in faces:
        c = f.calc_center_median()
        if grid.y(16.4) <= c.y <= grid.y(15.85) and c.z > 1.0 * lib.U:
            idx = grid.sample(c.x, grid.y(16))
            if idx is not None and idx >= 9:
                f.material_index = mats(idx, metallic=0.1, roughness=0.45)
        elif f.normal.z > 0.3:
            f.material_index = shade(grid.sample(c.x, c.y), disc)
    ring_loft(bm, grid, axis, TAIL_GROOVE, k=1.0, sides=16, mat_index=shadow)
    # The exhaust: a flat glowing bar 2 px thick, hottest where the sprite is (columns 20-21, 27-28).
    faces = ring_loft(bm, grid, axis, ENGINE, k=0.35, sides=28, mat_index=glow[118])
    for f in faces:
        c = f.calc_center_median()
        idx = grid.sample(c.x, min(max(c.y, grid.y(22)), grid.y(21)), skip=(-1,), reach=1)
        if idx is None or idx < 113:
            continue
        f.material_index = glow[121] if idx >= 120 else glow[118] if idx >= 117 else glow[116]
    # The dark exhaust nub under it (row 23, columns 23-24).
    lib.box(bm, grid.x(22.5), grid.y(22.4), grid.x(24.5), grid.y(23.5), -0.6 * lib.U, 0.6 * lib.U,
            mat_index=black)

    # Red lights: at the neck's flared front corners (rows 0-1, columns 16-17 and 31-32) and at its
    # pinch (row 5, columns 18-19 and 29-30), small studs standing on the surface.
    for c, r, z, m in ((16.5, 0.3, 1.5, light_a), (31.7, 0.4, 0.9, light_a),
                       (18.5, 5.0, 1.3, light_b), (29.5, 5.0, 1.3, light_b)):
        lib.blob(bm, (grid.x(c), grid.y(r), z * lib.U), (0.9 * lib.U, 0.9 * lib.U, 0.8 * lib.U),
                 segments=8, rings=5, mat_index=m)
    body_obj = obj_of(bm, "body")

    # One mesh; edges between different materials are split so recess walls, rims and grooves
    # stay crisp under smooth shading (but not between the hull's own painted greys).
    bm = bmesh.new()
    for o in (body_obj, saucer_obj, collar_obj):
        bm.from_mesh(o.data)
        bpy.data.objects.remove(o)
    crisp = [e for e in bm.edges if len(e.link_faces) == 2
             and e.link_faces[0].material_index != e.link_faces[1].material_index
             and not {e.link_faces[0].material_index, e.link_faces[1].material_index} <= greys]
    bmesh.ops.split_edges(bm, edges=crisp)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprites = [common.load_sprite(ROOT, n) for n in PIECES]
    obj = build(sprites)
    layout = [(p["model"], p["cx"] - 123, p["cy"] + 17) for p in sprites[0]["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for s in sprites:
        piece = pieces[s["name"]]
        for poly in piece.data.polygons:
            poly.use_smooth = True
        common.export_sprite_model(ROOT, [piece], f"enemies/{s['name']}", s["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        common.render_preview([obj], str(out), None, size=4)
        for s in sprites:
            f = s["frames"][0]
            common.render_preview([pieces[s["name"]]], str(out.with_name(f"{s['name']}.png")),
                                  ROOT / "reference" / "models" / s["name"] / f["image"], size=2)


if __name__ == "__main__":
    main()
