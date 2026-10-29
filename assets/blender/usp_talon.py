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

HULL, POD, CANOPY, GLOW, KEEL, RIB = range(6)

# The ship sprite and its banking frames (233 + bank * 2, bank -2..2) that the model replaces.
SPRITES = [{"sheet": "tyrian.shp#8", "size": 2, "frames": [233], "bank": {"step": 2, "max": 2}}]

PX = 1 / 12  # one sprite pixel in Blender units
HULL_PAL, POD_PAL, RIB_PAL = 24, 25, 25  # mid-tones: the sprite hull averages index 24, its pods and ribs 25

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

# Colours: each part takes its mid-tone and the game's lights shade it. The sprite's drawn light
# (lit pod crowns, white spine line, dark flanks and black outline) is not painted on: the game lights
# the model and draws its own outline. Only real parts are coloured: the canopy glass and the spine.
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


def fuselage_top(r):
    """Height in px of the fuselage's flat top deck at sprite row r."""
    return lerp_table(FUSELAGE, r)[1]


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


def hull_profile(w, top, bot):
    """Right half of the fuselage's faceted section, top centre to bottom centre, as (x, z) px:
    a flat top deck, a chamfered shoulder, the side and a chamfered belly (angular hard surface)."""
    h = top - bot
    return [(0.0, top), (0.42 * w, top), (0.76 * w, top - 0.24 * h), (w, top - 0.55 * h),
            (0.74 * w, bot + 0.12 * h), (0.34 * w, bot), (0.0, bot)]


def section_loft(bm, sections, mat_index, creases=(), cap=True):
    """Loft closed rings along the sprite's rows. Each section is (row, x offset px, right-half profile
    [(x, z) px] from top centre to bottom centre); the left half mirrors it. The profile corners in
    `creases` become hard edges (split), so a smooth-shaded panel stays flat and its edges crisp."""
    rings = []
    n = None
    for r, x0, prof in sections:
        pts = list(prof) + [(-x, z) for x, z in reversed(prof[1:-1])]
        n = len(pts)
        rings.append([bm.verts.new(((x0 + x) * PX, row(r), z * PX)) for x, z in pts])
    m = len(prof)
    crease_idx = set()
    for i in creases:
        crease_idx.add(i)
        crease_idx.add((2 * m - 2 - i) % n)
    split = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat_index
        for i in crease_idx:
            split.append((r0[i], r1[i]))
    if cap:
        f0 = bm.faces.new(list(reversed(rings[0])))
        f1 = bm.faces.new(rings[-1])
        f0.material_index = f1.material_index = mat_index
    bm.edges.ensure_lookup_table()
    edges = [bm.edges.get(pair) for pair in split]
    if cap:
        edges += list(f0.edges) + list(f1.edges)
    bmesh.ops.split_edges(bm, edges=[e for e in edges if e is not None])


def build(root):
    coll = common.reset_collection(NAME)
    mats = [
        # Painted metal hull and polished metal pods: the sprite's bright pod and spine spots are
        # sheen, which these make from the game's lights, not paint or geometry.
        common.material(f"pal_{HULL_PAL}_talon_hull", common.srgb(*PAL[HULL_PAL]), metallic=0.5, roughness=0.38),
        common.material(f"pal_{POD_PAL}_talon_pod", common.srgb(*PAL[POD_PAL]), metallic=0.75, roughness=0.3),
        common.material("pal_16_talon_canopy", common.srgb(*PAL[16]), metallic=0.0, roughness=0.06),
        common.material("engine_glow", (1.0, 0.45, 0.1), emission=(1.0, 0.5, 0.12), emission_strength=6.0),
        common.material("pal_27_talon_spine", common.srgb(*PAL[27]), metallic=0.6, roughness=0.32),
        common.material(f"pal_{RIB_PAL}_talon_rib", common.srgb(*PAL[RIB_PAL]), metallic=0.5, roughness=0.45),
    ]
    bm = bmesh.new()

    # Fuselage: an angular hull, pointed nose to blunt tail. Its section is faceted (flat deck,
    # chamfered shoulders and belly); the facets stay crisp and run smooth along the length.
    secs = [(2.05, 0.0, hull_profile(0.15, 0.9, 0.3))]
    for r, w, top, bot in resample(FUSELAGE):
        secs.append((r, 0.0, hull_profile(w, top, bot)))
    secs.append((27.45, 0.0, hull_profile(0.5, 0.5, -0.3)))
    section_loft(bm, secs, HULL, creases=(1, 2, 3, 4, 5))

    # Engine pods (the highlighted bulges at rows 15-23, cols 4-8 and 15-19): round, as tall as wide,
    # set into the hull's flanks so a dark valley (sprite columns 9 and 14) parts them from the deck.
    for side in (-1, 1):
        loft_px(bm, list(reversed([(r, side * x, w, w * 0.95, POD_Z) for r, x, w in resample(POD_SHAPE, 1.0)])),
                sides=16, mat_index=POD)

    # Spine: the thin bright crease down the centre of the back (sprite column 12, rows 13-25), a
    # narrow ridge with a sharp, slim crest; its white pixels are the polished crest's sheen.
    def spine(r0, r1, up, half, lift_ends=0.15):
        rows = [r0 + (r1 - r0) * i / 10 for i in range(11)]
        out = []
        for i, r in enumerate(rows):
            e = min(i, 10 - i) / 2.0
            k = min(1.0, e) if e > 0 else 0.0
            t = fuselage_top(r)
            u = lift_ends + (up - lift_ends) * k
            hw = max(0.25, half * (0.5 + 0.5 * k))
            out.append((r, 0.0, [(0.0, t + u), (0.22, t + u), (hw, t - 0.05), (hw * 0.8, t - 1.0), (0.0, t - 1.0)]))
        section_loft(bm, out, KEEL, creases=(1, 2, 3))
    spine(12.6, 25.7, 0.95, 1.05)
    # The nose ridge ahead of the cockpit (rows 3-8): the same crease, lower.
    spine(3.0, 8.4, 0.6, 0.85)

    # Tail ribs (rows 19-25): raised crisp straps across the back between the pods, alternating
    # with the dark gaps between them (rows 20, 22 and 24).
    for rc, half_len, grow in ((19.5, 0.42, 0.45), (21.5, 0.42, 0.45), (23.5, 0.42, 0.4), (25.1, 0.32, 0.0)):
        rib = []
        for r in (rc - half_len, rc + half_len):
            w, top, bot = lerp_table(FUSELAGE, rc)
            rib.append((r, 0.0, hull_profile(w + grow, top + 0.5, bot - 0.2)))
        section_loft(bm, rib, RIB, creases=(1, 2, 3, 4, 5))

    # Cockpit: the dark slit at rows 9-11, cols 10-13. A raised frame (a hull-coloured coaming with a
    # chamfered rim) holds a long, low glass canopy, pointed at both ends, its base edge crisp.
    def outline(r, ends, mid):
        """Half width of a long, blunt-ended outline between rows ends[0] and ends[1]: straight sides
        that close in over the last quarter at each end."""
        t = (r - ends[0]) / (ends[1] - ends[0])
        return max(0.35, mid * min(1.0, 4.0 * min(t, 1 - t)) ** 0.55)
    frame = []
    for i in range(13):
        r = 8.1 + (12.75 - 8.1) * i / 12
        hw = outline(r, (8.1, 12.75), 2.3)
        t = fuselage_top(r)
        frame.append((r, 0.0, [(0.0, t + 0.35), (hw - 0.35, t + 0.35), (hw, t), (hw, t - 1.2), (0.0, t - 1.2)]))
    section_loft(bm, frame, HULL, creases=(1, 2, 3))
    glass = []
    for i in range(13):
        r = 8.5 + (12.35 - 8.5) * i / 12
        hw = outline(r, (8.5, 12.35), 1.85)
        t = fuselage_top(r) + 0.3
        rise = 1.0 * (hw / 1.85) ** 0.7
        glass.append((r, 0.0, [(0.0, t + rise), (0.5 * hw, t + 0.9 * rise), (0.85 * hw, t + 0.5 * rise),
                               (hw, t), (0.0, t)]))
    section_loft(bm, glass, CANOPY, creases=(3,))

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
