"""USP Talon, the starting ship: a 3D version of its sprite (ship sprite 233 in tyrian.shp).

The hull's outline follows the sprite row by row (tools/extract-sprites.mjs renders it); colours are
sampled from the sprite. Materials named pal_<index> take that palette colour in game. Exports
public/models/usp_talon.glb and src/render/spriteModels/usp_talon.json.

Blender axes: forward is +Y, up is +Z, 1 unit = 12 Tyrian pixels. Sprite row r maps to
y = (14 - r) / 12, so the 24x28 sprite is centred on the origin.
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "usp_talon"
SPRITE = "ship-usp-talon-top.png"

HULL, POD, CANOPY, GLOW, KEEL, CHANNEL = range(6)

# The ship sprite and its banking frames (233 + bank * 2, bank -2..2) that the model replaces.
SPRITES = [{"sheet": "tyrian.shp#8", "size": 2, "frames": [233], "bank": {"step": 2, "max": 2}}]

PX = 1 / 12  # one sprite pixel in Blender units
HULL_PAL, POD_PAL = 24, 25  # mid-tones: the sprite hull averages index 24, its pods 25

# Palette colours of the indices used (tyrian.shp#8 ramp 16-31, sampled from the sprite).
PAL = {16: (16, 8, 0), 17: (28, 16, 0), 18: (44, 24, 4), 19: (56, 36, 8), 20: (73, 44, 16),
       21: (85, 60, 24), 22: (101, 73, 32), 23: (113, 85, 44), 24: (125, 101, 56), 25: (142, 113, 69),
       26: (154, 130, 85), 27: (170, 146, 101), 28: (182, 162, 121), 29: (207, 195, 158), 30: (231, 223, 199)}


def row(r):
    """Sprite row edge to Blender Y (row r's pixels span row(r)..row(r + 1))."""
    return (14 - r) / 12


def lerp_table(table, r):
    """Linear interpolation in a table of (row, a, b, ...) tuples sorted by row."""
    if r <= table[0][0]:
        return table[0][1:]
    for t0, t1 in zip(table, table[1:]):
        if t0[0] <= r <= t1[0]:
            f = (r - t0[0]) / (t1[0] - t0[0])
            return tuple(a + (b - a) * f for a, b in zip(t0[1:], t1[1:]))
    return table[-1][1:]


# Fuselage: (row at pixel centre, half width px, top z px, bottom z px). The nose follows the
# sprite's stepped outline (2, 4, 6, 8 px wide) and its height grows with its width; behind the
# shoulder (row 12) it is a round body about 10-11 px wide and 7 px tall, the pods fill out the rest.
FUSELAGE = [
    (2.5, 1.0, 1.5, -0.3), (3.5, 1.9, 2.1, -0.9), (4.5, 2.0, 2.3, -1.1), (5.5, 2.9, 2.8, -1.5),
    (7.5, 3.0, 3.1, -1.8), (8.5, 3.9, 3.5, -2.2), (11.5, 4.0, 3.9, -2.6), (12.5, 4.9, 4.2, -2.9),
    (13.5, 5.4, 4.3, -3.0), (17.0, 5.5, 4.4, -3.0), (21.5, 5.5, 4.2, -3.0), (23.5, 5.6, 3.8, -2.8),
    (24.5, 5.6, 3.4, -2.6), (25.5, 4.9, 2.8, -2.2), (26.5, 2.9, 1.9, -1.5), (27.0, 1.9, 1.3, -1.1),
    (27.3, 1.1, 0.9, -0.7),
]

# Pods: (row, axis x px, half width px), round in section. Their axis leans in toward the front
# and back so they merge into the fuselage there, and their outer edge follows the sprite's outline.
POD_Z = 0.9
POD_SHAPE = [
    (12.6, 3.9, 0.0), (13.4, 4.2, 1.6), (15.5, 4.6, 2.3), (17.5, 5.0, 2.9), (19.0, 5.4, 3.4),
    (20.5, 5.5, 3.5), (21.8, 5.5, 3.3), (22.6, 5.4, 2.6), (23.5, 5.0, 2.1), (24.3, 4.6, 1.6),
    (25.0, 4.2, 1.0), (25.6, 3.8, 0.0),
]

# Grooves: the two straight dark lines either side of the keel (sprite columns 9 and 14, rows 14-23),
# cut 1 px wide and GROOVE_DEPTH px deep into the fuselage.
GROOVE_X, GROOVE_ROWS, GROOVE_DEPTH = 2.5, (13.8, 25.3), 0.8

# Colours: each part takes its mid-tone and the game's lights shade it. The sprite's drawn light
# (lit pod crowns, white keel line, dark flanks and black outline) is not painted on: the game lights
# the model and draws its own outline. Only real markings are coloured: the dark grooves and canopy.
MODEL = "ship-usp-talon-light-fighter"


def resample(table, step=1.0):
    """The table's rows plus extra rows every `step` between them (linear, so the shape is the same),
    so the faces are about a sprite pixel long."""
    out = []
    for t0, t1 in zip(table, table[1:]):
        out.append(t0)
        n = int((t1[0] - t0[0]) / step)
        for i in range(1, n + 1):
            r = t0[0] + (t1[0] - t0[0]) * i / (n + 1)
            out.append((r,) + lerp_table(table, r))
    out.append(table[-1])
    return out


def fuselage_top(r, x=0.0):
    """Height in px of the fuselage's top surface at sprite row r, x px off the centreline."""
    w, top, bot = lerp_table(FUSELAGE, r)
    zc, h = (top + bot) / 2, (top - bot) / 2
    return zc + h * max(0.0, 1 - (x / w) ** 2) ** 0.5 if abs(x) < w else bot


def loft_px(bm, sections, sides, mat_index, cap_start=True, cap_end=True):
    """common.loft with sections (row, x, half width, half height, z centre) all in sprite px;
    each ring is moved to its own x."""
    start = len(bm.verts)
    common.loft(bm, [(row(r), w * PX, h * PX, z * PX) for r, _, w, h, z in sections], sides=sides,
                mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    bm.verts.ensure_lookup_table()
    i = start
    for _, x, w, h, _ in sections:
        n = 1 if w == 0 and h == 0 else sides
        for v in bm.verts[i:i + n]:
            v.co.x += x * PX
        i += n


def build(root):
    coll = common.reset_collection(NAME)
    mats = [
        # Painted metal hull and polished metal pods: the sprite's bright pod and keel spots are
        # sheen, which these make from the game's lights, not paint or geometry.
        common.material(f"pal_{HULL_PAL}_talon_hull", common.srgb(*PAL[HULL_PAL]), metallic=0.45, roughness=0.4),
        common.material(f"pal_{POD_PAL}_talon_pod", common.srgb(*PAL[POD_PAL]), metallic=0.75, roughness=0.3),
        common.material("pal_16_talon_canopy", common.srgb(*PAL[16]), metallic=0.0, roughness=0.08),
        common.material("engine_glow", (1.0, 0.45, 0.1), emission=(1.0, 0.5, 0.12), emission_strength=6.0),
        common.material("pal_28_talon_keel", common.srgb(*PAL[28]), metallic=0.4, roughness=0.3),
        common.material("pal_20_talon_channel", common.srgb(*PAL[20]), metallic=0.0, roughness=0.85),
    ]

    # Fuselage: a round body, pointed nose to rounded tail, with the two grooves cut into its back.
    fbm = bmesh.new()
    sections = [(2.0, 0.0, 0.0, 0.0, 0.6)]
    for r, w, top, bot in resample(FUSELAGE):
        sections.append((r, 0.0, w, (top - bot) / 2, (top + bot) / 2))
    sections.append((27.45, 0.0, 0.0, 0.0, 0.1))
    loft_px(fbm, list(reversed(sections)), sides=20, mat_index=HULL)
    body = common.mesh_object(NAME + "-body", fbm, mats, coll)
    cbm = bmesh.new()
    k = 2 ** 0.5  # a 4-sided loft ring is a box whose half extents are (w, h) / sqrt(2)
    for side in (-1, 1):
        rows = [GROOVE_ROWS[0] + (GROOVE_ROWS[1] - GROOVE_ROWS[0]) * i / 16 for i in range(17)]
        box = []
        for r in rows:
            bottom = fuselage_top(r, GROOVE_X) - GROOVE_DEPTH
            top = bottom + 4.0
            box.append((r, side * GROOVE_X, 0.5 * k, (top - bottom) / 2 * k, (top + bottom) / 2))
        loft_px(cbm, list(reversed(box)), sides=4, mat_index=CHANNEL)
    cutter = common.mesh_object(NAME + "-cutter", cbm, mats, coll)
    mod = body.modifiers.new("grooves", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    mesh = body.data
    bpy.data.objects.remove(body)
    bpy.data.meshes.remove(mesh)
    # Crisp groove walls: the channel's faces share no normals with the hull or each other.
    bmesh.ops.split_edges(bm, edges=[e for e in bm.edges if any(f.material_index == CHANNEL for f in e.link_faces)])

    # Engine pods (the highlighted lumps at rows 15-23, cols 4-8 and 15-19): round, as tall as wide.
    for side in (-1, 1):
        loft_px(bm, list(reversed([(r, side * x, w, w * 0.95, POD_Z) for r, x, w in resample(POD_SHAPE, 1.0)])),
                sides=16, mat_index=POD)

    # Keel: the bright 3 px ridge down the back from the canopy to the tail (rows 12-25).
    # (row, half width, height above the fuselage top): round in section, easing down at both ends.
    # Round in section (a circle as wide as the keel, its top `up` px above the fuselage, its centre
    # sunk below it so the ridge stands about 1.5 px proud of the hull at its edges).
    keel = [(12.0, 0.0, 0.0), (12.5, 1.2, 0.8), (13.5, 1.5, 1.1), (16, 1.5, 1.2), (20, 1.5, 1.2),
            (22.5, 1.5, 1.1), (24.2, 1.3, 0.9), (25.3, 1.0, 0.6), (25.8, 0.6, 0.35), (26.0, 0.0, 0.0)]
    keel = [(r, 0.0, w, w, fuselage_top(r) + (up - w if w else 0.0)) for r, w, up in keel]
    loft_px(bm, list(reversed(keel)), sides=12, mat_index=KEEL)
    # The sprite's white line down its crest (column 12) is the polished keel's sheen.

    # Nose ridge: the bright column down the nose (rows 3-9), lower and narrower.
    nose = [(2.8, 0.0, 0.0, 0.0, fuselage_top(2.8))]
    for r in (3.5, 5.0, 6.5, 8.0, 9.2):
        nose.append((r, 0.0, 0.8, 0.9, fuselage_top(r) + 0.05))
    nose.append((9.8, 0.0, 0.0, 0.0, fuselage_top(9.8)))
    loft_px(bm, list(reversed(nose)), sides=8, mat_index=KEEL)

    # Canopy (the dark spot at rows 10-11, cols 11-12): a small glazed dome, an ellipsoid sunk to
    # its equator so only its upper half shows, about 1 px proud of the hull.
    dome = []
    rc, half_len = 10.95, 1.1
    for i in range(7):
        t = -1 + 2 * i / 6
        k = max(0.0, 1 - t * t) ** 0.5
        dome.append((rc + t * half_len, 0.0, 1.1 * k, 1.45 * k, fuselage_top(rc) - 0.45))
    loft_px(bm, list(reversed(dome)), sides=12, mat_index=CANOPY)

    # Exhausts inside the back of the pods: hidden from the top view, there for later effects.
    for side in (-1, 1):
        x = side * 5.0
        loft_px(bm, [(23.8, x, 0.0, 0.0, POD_Z), (23.5, x, 0.8, 0.8, POD_Z)], sides=10, mat_index=GLOW,
                cap_start=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return obj


def main():
    root = common.repo_root(__file__)
    common.reference_image(f"{NAME}_sprite", root / "reference" / "sprites" / SPRITE, 24 / 12, 28 / 12)
    obj = build(root)
    common.export_sprite_model(root, [obj], NAME, SPRITES)
    if "--preview" in sys.argv:
        ref = root / "reference" / "models" / "ship-usp-talon-light-fighter" / "frame-tyrian8-233.png"
        common.render_preview([obj], sys.argv[sys.argv.index("--preview") + 1], ref, size=2)


if __name__ == "__main__":
    main()
