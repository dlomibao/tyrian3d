"""Stepped pyramid (newsh3.shp frames 153, 155, 191, 193, a 2x2 assembly): a 3D version of its sprites.

Seen in episode 4 (level 4.2), standing in the desert in rows. Four 2x2 ground enemies make one
48x56 px tile (sprite.json `assemblyLayout`; 153 top left, 155 top right, 191 bottom left, 193
bottom right): a sandstone ziggurat of four tiers with a pointed cap, drawn in the game's oblique
view, so each higher tier sits further up the screen, its lit west edge, shaded east edge and dark
south face showing as stripes. The sand around it, with the pyramid's shadow to the right and
below, is part of the sprites, so the model stands on a thin plate of sand.

Each tier is a block whose sloped sides cover the sprite's riser stripes (one pixel on the west,
north and east, the tall dark south face below), with a bright lip and a flat step inside it; the
next tier stands on that step. The whole tile is built once in assembly coordinates and cut into
the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-191.py [-- --preview out.png]
(the preview is the whole pyramid; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b076 as lib  # noqa: E402

NAME = "assembly-newsh3-191"
ROOT = common.repo_root(__file__)
PIECES = ["newsh3-153", "newsh3-155", "newsh3-191", "newsh3-193"]
# One pyramid of the layout: 153 at screen (80, 11), 155 (104, 11), 191 (80, 39), 193 (104, 39).
# Its 48x56 px tile's top-left pixel is screen (68, -3); its centre (92, 25) is the Blender origin.
CX0, CY0 = 92, 25
F = lib.Frame(48, 56)

# Tiers, bottom up: outer footprint (pixel edges c0, c1, r0, r1), riser widths (west, north, east,
# south) in px, and the height of the step on top.
TIERS = [
    ((2, 41, 11, 43), (1, 1, 1, 6), 0.24),
    ((5, 38, 9, 33), (1, 1, 1, 2), 0.34),
    ((8, 35, 7, 27), (1, 1, 1, 2), 0.44),
    ((12, 32, 5, 22), (1, 1, 1, 3), 0.56),
]
CAP = (16, 28, 4, 16)  # the pointed cap's base (edges); its tip is at column edge 22, row 3
CAP_TOP = 0.92


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "n3a191"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, metallic=0.0, **kw)  # noqa: E731
    mats = [
        pal(20, roughness=0.85),  # 0 south steps (in shade)
        pal(21, roughness=0.85),  # 1 north risers, south lips
        pal(18, roughness=0.9),  # 2 south and east faces in deep shade
        pal(24, roughness=0.8),  # 3 west steps
        pal(22, roughness=0.85),  # 4 east steps
        pal(27, roughness=0.7),  # 5 lit west lips
        pal(25, roughness=0.75),  # 6 north lips, the cap's lit west face
        pal(23, roughness=0.8),  # 7 east lips
        pal(17, roughness=0.95),  # 8 doorway and vents
        pal(168, roughness=0.95),  # 9 sand
        pal(165, roughness=0.95),  # 10 shadow on the sand
        pal(163, roughness=0.95),  # 11 deep shadow under the south face
        pal(19, roughness=0.9),  # 12 west risers, the cap's south foot
    ]
    S_STEP, N_RISE, SHADE, W_STEP, E_STEP, W_LIP, N_LIP, E_LIP, DOOR, SAND, SHADOW, DEEP, W_RISE = range(13)
    bm = bmesh.new()

    # Sand plate over the whole tile, with the pyramid's shadow to its right and below it.
    lib.box(bm, F, 0, 48, 0, 56, 0.0, 0.01, SAND)
    for c0, c1, r0, r1, m in ((41, 43.5, 15, 43, SHADOW), (43.5, 45, 17, 45, SAND),
                              (3, 43.5, 43, 46, DEEP), (4, 44, 46, 48.5, SHADOW)):
        lib.quad(bm, [F.p(c0, r1, 0.012), F.p(c1, r1, 0.012), F.p(c1, r0, 0.012), F.p(c0, r0, 0.012)], m)

    z_low = 0.0
    for i, ((c0, c1, r0, r1), (w, n, e, s), z) in enumerate(TIERS):
        if z_low > 0:  # a skirt down to the sand where the tier reaches past the one below
            lib.box(bm, F, c0, c1, r0, r1, 0.0, z_low, N_RISE)
        outer = lib.rect(F, c0, c1, r0, r1, z_low)
        top = (c0 + w, c1 - e, r0 + n, r1 - s)
        lib.ring_faces(bm, outer, lib.rect(F, *top, z), (N_RISE, SHADE, SHADE, W_RISE))
        lip = (top[0] + 1, top[1] - 1, top[2] + 1, top[3] - 1)
        lib.ring_faces(bm, lib.rect(F, *top, z), lib.rect(F, *lip, z), (N_LIP, E_LIP, N_RISE, W_LIP))
        nxt = TIERS[i + 1][0] if i + 1 < len(TIERS) else CAP
        inner = (max(lip[0], nxt[0]), min(lip[1], nxt[1]), max(lip[2], nxt[2]), min(lip[3], nxt[3]))
        lib.ring_faces(bm, lib.rect(F, *lip, z), lib.rect(F, *inner, z), (W_STEP, E_STEP, S_STEP, W_STEP))
        z_low = z

    # The pointed cap: its tip leans to the north (as drawn), its north foot reaches the sand.
    tip = F.p(22, 3, CAP_TOP)
    c0, c1, r0, r1 = CAP
    sw, se = F.p(c0, r1, z_low), F.p(c1, r1, z_low)
    nw, ne = F.p(c0, r0, 0.0), F.p(c1, r0, 0.0)
    lib.quad(bm, [tip, nw, sw], W_LIP)
    lib.quad(bm, [tip, se, ne], E_STEP)
    lib.quad(bm, [tip, sw, se], S_STEP)
    lib.quad(bm, [tip, ne, nw], N_RISE)
    lib.quad(bm, [nw, ne, se, sw], N_RISE)
    # A darker band at the foot of its south face (row 15).
    zf = z_low + (CAP_TOP - z_low) * (1 / 13) + 0.004
    lib.quad(bm, [F.p(c0 + 0.5, r1 - 0.05, z_low + 0.004), F.p(c1 - 0.5, r1 - 0.05, z_low + 0.004),
                  F.p(c1 - 1.3, r1 - 1, zf), F.p(c0 + 1.3, r1 - 1, zf)], W_RISE)

    # Doorway, vents and slots on the south faces.
    def on_south(tier, cols, rows, mat):
        (tc0, tc1, tr0, tr1), (_, _, _, s), z = TIERS[tier]
        zl = TIERS[tier - 1][2] if tier else 0.0
        def zz(r):
            return z - (r - (tr1 - s)) / s * (z - zl) + 0.006
        (a, b), (p, q) = cols, rows
        lib.quad(bm, [F.p(a, q, zz(q)), F.p(b, q, zz(q)), F.p(b, p, zz(p)), F.p(a, p, zz(p))], mat)

    on_south(0, (24.6, 26.4), (38, 41.5), DOOR)
    on_south(0, (35, 39.5), (41, 42.8), DOOR)
    on_south(0, (35.8, 37.8), (37.1, 38), DOOR)
    on_south(1, (28, 30), (32, 32.9), DOOR)
    on_south(2, (16, 18), (26, 26.9), DOOR)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh3-191's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh3-191")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    seen, layout = set(), []
    for e in sprite["assemblyLayout"]:
        if e["model"] in PIECES and e["model"] not in seen and abs(e["cx"] - CX0) <= 12 and abs(e["cy"] - CY0) <= 14:
            seen.add(e["model"])
            layout.append((e["model"], e["cx"] - CX0, e["cy"] - CY0))
    assert len(layout) == 4, layout
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, 48, 56, 24, 28, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
