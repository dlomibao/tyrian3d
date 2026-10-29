"""USP Talon, the starting ship: a 3D version of its sprite (ship sprite 233 in tyrian.shp).

Its parts are laid out from the concept (assets/blender/features/concepts/), registered onto the
sprite: ogive nose, framed oval canopy, two-part round engine pods with outboard caps, cross bands,
vents, tail plate and exhaust housings, each where the concept draws it, inside the sprite's outline.
Colours are palette indices closest to the concept's mid-tones. Materials named pal_<index> take that palette colour in game. Exports
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

HULL, POD, CANOPY, GLOW, KEEL, RIB, VENT, FRAME, CAP = range(9)

# The ship sprite and its banking frames (233 + bank * 2, bank -2..2) that the model replaces.
SPRITES = [{"sheet": "tyrian.shp#8", "size": 2, "frames": [233], "bank": {"step": 2, "max": 2}}]

PX = 1 / 12  # one sprite pixel in Blender units

# Palette colours of the indices used (tyrian.shp#8 ramp 16-31, from reference/models/.../sprite.json).
PAL = {16: (16, 8, 0), 17: (28, 16, 0), 18: (44, 24, 4), 19: (56, 36, 8), 20: (73, 44, 16),
       21: (85, 60, 24), 22: (101, 73, 32), 23: (113, 85, 44), 24: (125, 101, 56), 25: (142, 113, 69),
       26: (154, 130, 85), 27: (170, 146, 101), 28: (182, 162, 121), 29: (207, 195, 158), 30: (231, 223, 199)}

MODEL = "ship-usp-talon-light-fighter"

# The layout follows the concept (assets/blender/features/concepts/<MODEL>.jpg) registered onto the
# sprite (assets/blender/textures/<MODEL>/concept.png, 16 texels per sprite px): every part sits
# where the concept draws it, inside the sprite's outline. Positions below are in sprite px
# (column c, row r: c = 12 is the centre line), heights z in px above the model's origin.


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


def resample(table, step=1.0):
    """The table's rows plus extra rows every `step` between them (linear, so the shape is the same)."""
    out = []
    for t0, t1 in zip(table, table[1:]):
        out.append(t0)
        n = int((t1[0] - t0[0]) / step)
        for i in range(1, n + 1):
            r = t0[0] + (t1[0] - t0[0]) * i / (n + 1)
            out.append((r,) + lerp_table(table, r))
    out.append(table[-1])
    return out


# Fuselage, from the concept: (row, half width px, deck z px, belly z px). An ogive nose from the tip
# at row 2 widening to 8 px across the cockpit (rows 10-14), then, between the engine pods, the narrower
# rear body (columns 9.2-14.8) down to the tail plate's blunt end at row 26.8.
FUSELAGE = [
    (2.0, 0.15, 0.6, 0.1), (2.6, 0.75, 1.0, -0.2), (3.5, 1.4, 1.5, -0.6), (5.0, 2.2, 2.1, -1.1),
    (6.5, 2.8, 2.6, -1.5), (8.0, 3.4, 3.0, -1.9), (9.5, 3.8, 3.3, -2.2), (11.0, 4.0, 3.5, -2.5),
    (14.0, 4.0, 3.6, -2.7), (16.0, 3.7, 3.6, -2.7), (17.5, 3.0, 3.5, -2.6), (19.0, 2.8, 3.4, -2.5),
    (23.0, 2.8, 3.1, -2.3), (25.5, 2.8, 2.8, -2.0), (26.4, 2.6, 2.4, -1.6), (26.8, 2.1, 1.9, -1.2),
]


def fuselage_top(r):
    return lerp_table(FUSELAGE, r)[1]


def hull_profile(w, top, bot, deck=0.45, ch=0.22):
    """Right half of a faceted hard-surface section, top centre to bottom centre, as (x, z) px:
    a flat deck, a chamfered shoulder, the side and a chamfered belly."""
    h = top - bot
    return [(0.0, top), (deck * w, top), (0.8 * w, top - ch * h), (w, top - 0.55 * h),
            (0.74 * w, bot + 0.12 * h), (0.34 * w, bot), (0.0, bot)]


def plate_profile(w, top, bot, ch):
    """A raised plate's half section: flat top, a 45-degree chamfer, straight side."""
    ch = min(ch, 0.45 * w, 0.8 * (top - bot))
    return [(0.0, top), (w - ch, top), (w, top - ch), (w, bot), (0.0, bot)]


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


def plate(bm, rows, mat_index, ch=0.3):
    """A raised chamfered plate lofted along rows: rows are (row, centre column, half width, top z,
    bottom z)."""
    section_loft(bm, [(r, c - 12, plate_profile(w, t, b, ch)) for r, c, w, t, b in rows], mat_index,
                 creases=(1, 2, 3))


def rounded_ends(r0, r1, c, w, top, bot, ease=0.4, n=4, min_w=0.45):
    """Rows for a plate whose ends round off in the top view over `ease` px."""
    out = []
    for i in range(n + 1):
        t = i / n
        r = r0 + ease * t
        out.append((r, c, max(min_w, w * (0.55 + 0.45 * t ** 0.5)), top, bot))
    out.append((r1 - ease, c, w, top, bot))
    for i in range(n, -1, -1):
        t = i / n
        out.append((r1 - ease * t, c, max(min_w, w * (0.55 + 0.45 * t ** 0.5)), top, bot))
    # Drop repeated rows.
    clean = [out[0]]
    for o in out[1:]:
        if o[0] > clean[-1][0] + 1e-4:
            clean.append(o)
    return clean


def build(root):
    coll = common.reset_collection(NAME)
    mats = [
        common.material("pal_24_talon_hull", common.srgb(*PAL[24]), metallic=0.5, roughness=0.4),
        # The engine pods are polished metal: the concept's bright domes are sheen from the lights.
        common.material("pal_25_talon_pod", common.srgb(*PAL[25]), metallic=0.8, roughness=0.3),
        common.material("pal_16_talon_canopy", common.srgb(*PAL[16]), metallic=0.0, roughness=0.05),
        common.material("engine_glow", (1.0, 0.45, 0.1), emission=(1.0, 0.5, 0.12), emission_strength=6.0),
        common.material("pal_26_talon_spine", common.srgb(*PAL[26]), metallic=0.8, roughness=0.3),
        common.material("pal_24_talon_band", common.srgb(*PAL[24]), metallic=0.55, roughness=0.4),
        common.material("pal_18_talon_vent", common.srgb(*PAL[18]), metallic=0.3, roughness=0.7),
        common.material("pal_21_talon_frame", common.srgb(*PAL[21]), metallic=0.6, roughness=0.35),
        common.material("pal_22_talon_cap", common.srgb(*PAL[22]), metallic=0.6, roughness=0.38),
    ]
    bm = bmesh.new()

    # Fuselage: the concept's ogive nose and narrower rear body in one faceted hull (flat deck,
    # chamfered shoulders and belly), crisp along its length.
    secs = [(r, 0.0, hull_profile(w, t, b)) for r, w, t, b in resample(FUSELAGE, 0.8)]
    section_loft(bm, secs, HULL, creases=(1, 2, 3, 4, 5))

    # Nose spine: the concept's narrow raised centre panel from row 4 back to the canopy (row 9.4).
    nose = []
    for i in range(9):
        r = 4.0 + (9.6 - 4.0) * i / 8
        w = 0.55 + 0.45 * min(1.0, (r - 4.0) / 2.0)
        t = fuselage_top(r)
        nose.append((r, 12.0, w, t + 0.4, t - 1.0))
    plate(bm, nose, KEEL, ch=0.25)

    # Cockpit: the concept's long oval canopy, columns 10-14, rows 9.6-16.3, in a darker raised
    # coaming (columns 9.6-14.4, rows 9.2-16.7); the glass is a dark, glossy bubble.
    def oval(r, r0, r1, mid, front=0.35, back=0.25):
        t = (r - r0) / (r1 - r0)
        f = min(1.0, t / front) if t < front else (min(1.0, (1 - t) / back) if t > 1 - back else 1.0)
        return max(0.3, mid * f ** 0.5)
    frame = []
    for i in range(15):
        r = 9.2 + (16.7 - 9.2) * i / 14
        hw = oval(r, 9.2, 16.7, 2.45)
        t = fuselage_top(r)
        frame.append((r, 0.0, [(0.0, t + 0.45), (hw - 0.3, t + 0.45), (hw, t + 0.15), (hw, t - 1.2), (0.0, t - 1.2)]))
    section_loft(bm, frame, FRAME, creases=(1, 2, 3))
    glass = []
    for i in range(15):
        r = 9.6 + (16.3 - 9.6) * i / 14
        hw = oval(r, 9.6, 16.3, 1.95)
        t = fuselage_top(r) + 0.4
        rise = 1.5 * (hw / 1.95) ** 0.7
        glass.append((r, 0.0, [(0.0, t + rise), (0.45 * hw, t + 0.92 * rise), (0.8 * hw, t + 0.6 * rise),
                               (hw, t + 0.05), (0.0, t)]))
    section_loft(bm, glass, CANOPY, creases=(3,))
    # The canopy's cross frame (row 12.4), where the front pane meets the rear one.
    bar = []
    for r in (12.25, 12.6):
        hw = oval(r, 9.6, 16.3, 1.95) + 0.1
        t = fuselage_top(r) + 0.4
        rise = 1.5 * (hw / 1.95) ** 0.7 + 0.12
        bar.append((r, 0.0, [(0.0, t + rise), (0.45 * hw, t + 0.92 * rise), (0.8 * hw, t + 0.6 * rise),
                             (hw, t + 0.05), (0.0, t)]))
    section_loft(bm, bar, FRAME, creases=(3,))

    # Rear spine behind the canopy (rows 16.6-19, columns 11-13): a raised polished strip.
    plate(bm, [(r, 12.0, 1.0, fuselage_top(r) + 0.45, fuselage_top(r) - 1.0) for r in (16.5, 17.7, 19.0)], KEEL, ch=0.25)

    # Cross bands between the pods (concept rows 19-22): two raised straps, a recessed dark grille
    # between them with three slats, then a lower band.
    for r0, r1 in ((19.0, 19.95), (21.0, 21.9)):
        plate(bm, [(r, 12.0, 2.15, fuselage_top(r) + 0.55, fuselage_top(r) - 1.2) for r in (r0, r1)], RIB, ch=0.3)
    plate(bm, [(r, 12.0, 1.9, fuselage_top(r) + 0.05, fuselage_top(r) - 1.0) for r in (19.9, 21.05)], VENT, ch=0.1)
    for rc in (20.2, 20.5, 20.8):
        plate(bm, [(r, 12.0, 1.8, fuselage_top(r) + 0.3, fuselage_top(r) - 0.2) for r in (rc - 0.07, rc + 0.07)], RIB, ch=0.05)

    # Vents (rows 22.6-23.5): two dark ports either side of the centre line, set in a raised frame.
    plate(bm, [(r, 12.0, 2.0, fuselage_top(r) + 0.3, fuselage_top(r) - 1.0) for r in (22.2, 23.7)], HULL, ch=0.2)
    for c in (11.1, 12.9):
        plate(bm, [(r, c, 0.55, fuselage_top(r) + 0.36, fuselage_top(r)) for r in (22.6, 23.4)], VENT, ch=0.05)

    # Tail plate (rows 23.8-26.6): the concept's chevron-marked plate, narrowing to the tail.
    plate(bm, [(23.8, 12.0, 1.7, fuselage_top(23.8) + 0.4, fuselage_top(23.8) - 1.0),
               (25.6, 12.0, 1.4, fuselage_top(25.6) + 0.4, fuselage_top(25.6) - 1.0),
               (26.6, 12.0, 0.9, fuselage_top(26.6) + 0.3, fuselage_top(26.6) - 0.8)], RIB, ch=0.3)

    for side in (-1, 1):
        def col(c):
            return 12 + side * (12 - c)

        # Engine pod, front cowling (rows 12.4-18.2): a polished shell from the nose's flank out to the
        # pod's full width; its rear rim is the seam the concept draws at row 18.
        cowl = [(12.4, 9.2, 0.9, 1.6), (13.4, 8.7, 1.4, 2.0), (14.4, 8.1, 1.8, 2.3), (15.4, 7.7, 2.2, 2.55),
                (16.3, 7.4, 2.45, 2.7), (17.2, 7.3, 2.6, 2.75), (18.2, 7.25, 2.6, 2.75)]
        loft_px(bm, [(r, col(c) - 12, w, h, 0.9) for r, c, w, h in cowl], sides=16, mat_index=POD)
        # Engine pod, rear dome (rows 18.1-23.8): round, about as tall as it is wide.
        dome = [(18.1, 7.25, 2.45, 2.6), (19.5, 7.2, 2.5, 2.65), (21.0, 7.2, 2.45, 2.6), (22.2, 7.25, 2.25, 2.4),
                (23.0, 7.35, 1.8, 2.0), (23.5, 7.5, 1.1, 1.3), (23.8, 7.6, 0.0, 0.0)]
        loft_px(bm, [(r, col(c) - 12, w, h, 0.9) for r, c, w, h in dome], sides=16, mat_index=POD)

        # Outboard armour caps (columns 3-5, rows 18.8-23): chamfered plates hugging the pods' sides.
        cap = rounded_ends(18.8, 22.9, 4.25, 1.15, 2.3, -1.2, ease=0.6)
        plate(bm, [(r, col(4.25 + 1.15 - w), w, t, b) for r, _, w, t, b in cap], CAP, ch=0.45)

        # Engine housing under the back of the pod (rows 23-25, columns 6-10) with its intake grille
        # (columns 8.6-9.8) and an exhaust nozzle (columns 7-8.6) sticking out behind (to row 25.9), its
        # glow set deep inside: the concept draws the nozzles dark.
        plate(bm, [(r, col(7.9), 1.9, 1.0, -1.4) for r in (22.9, 24.9)], CAP, ch=0.35)
        plate(bm, [(r, col(9.2), 0.6, 1.15, 0.6) for r in (23.2, 24.6)], VENT, ch=0.05)
        loft_px(bm, [(24.6, col(7.8) - 12, 0.75, 0.75, 0.0), (25.9, col(7.8) - 12, 0.72, 0.72, 0.0)],
                sides=10, mat_index=VENT, cap_end=False)
        loft_px(bm, [(24.9, col(7.8) - 12, 0.5, 0.5, 0.0), (25.3, col(7.8) - 12, 0.5, 0.5, 0.0)],
                sides=10, mat_index=GLOW, cap_start=False)

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
