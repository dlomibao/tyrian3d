"""Rib-backed lava beast (newshe.shp, assembly of 8 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.8), lying on the ground. Eight 2x2 pieces side by side make one
96 x 56 px creature (sprite.json `assemblyLayout`, two rows of four): a long hunched body of
overlapping dark red shell segments, each with a glowing orange rib on its front edge, growing
taller towards the head; a row of pink bone knobs along its back; a pink hooked tail tip on the
left; a head on the right split into an upper part with two glowing yellow eyes and a lower
jaw, both rimmed with orange ridges; and a thin red limb that trails from the jaw along under
the body. None of the pieces is animated.

The whole creature is built once in assembly coordinates (lib_b130), then cut into the eight
pieces with common.split_assembly. Being a ground object, it sits on z = 0 and builds upward.

Run: blender --background --python assets/blender/enemies/assembly-newshe-123.py [-- --preview out.png]
(the preview is the whole creature; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b130 import dome_height, dome_loft, ellipsoid, sweep, to_object, composite_png  # noqa: E402

NAME = "assembly-newshe-123"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-85", "newshe-87", "newshe-89", "newshe-91",
          "newshe-123", "newshe-125", "newshe-127", "newshe-129"]
# Assembly pixel (0, 0) is screen (-20, -32) (newshe-85's top-left corner); the centre of the
# 96 x 56 px assembly, screen (28, -4), is the Blender origin.
CX0, CY0 = 28, -4
HS = 0.85  # overall height scale

# Shell segments, tail to neck: (rib width px, sections (col, top row, bottom row, height)).
SEGMENTS = [
    (0.0, [(2.6, 23.5, 26.5, 0.12), (4.0, 21.0, 29.0, 0.24), (6.0, 19.5, 31.0, 0.3),
           (8.0, 18.5, 32.0, 0.34), (10.4, 17.0, 33.5, 0.36)]),
    (3.0, [(10.6, 17.0, 35.5, 0.34), (11.5, 15.5, 37.0, 0.44), (14.0, 15.0, 37.0, 0.47),
           (17.4, 15.0, 37.5, 0.44)]),
    (2.4, [(17.6, 15.0, 38.0, 0.46), (18.5, 14.0, 40.0, 0.54), (21.0, 14.0, 42.5, 0.57),
           (23.4, 14.0, 44.0, 0.56)]),
    (2.4, [(23.6, 13.0, 43.5, 0.58), (24.5, 12.0, 45.0, 0.65), (28.0, 12.0, 46.0, 0.68),
           (31.4, 12.0, 46.0, 0.66)]),
    (2.8, [(31.6, 10.0, 45.5, 0.68), (32.5, 8.0, 46.0, 0.75), (36.0, 8.0, 46.5, 0.78),
           (38.0, 9.0, 42.0, 0.76), (40.4, 9.0, 39.5, 0.72)]),
    (2.8, [(40.6, 7.0, 41.0, 0.75), (41.5, 5.0, 42.5, 0.84), (45.0, 6.0, 41.5, 0.86),
           (48.0, 6.5, 43.0, 0.85), (49.4, 6.0, 44.0, 0.84)]),
    (3.0, [(49.6, 5.0, 44.5, 0.85), (50.5, 4.0, 45.5, 0.9), (53.0, 3.0, 47.5, 0.94),
           (56.0, 4.0, 49.0, 0.92), (58.5, 5.0, 50.0, 0.88), (60.4, 6.0, 50.0, 0.82)]),
    (0.0, [(60.6, 8.0, 50.0, 0.76), (62.5, 9.5, 49.0, 0.72), (65.0, 8.0, 45.0, 0.68),
           (68.4, 9.0, 42.0, 0.62)]),
]
# The head: upper part (eyes) and lower jaw, over a low dark core that shows in the gap.
HEAD = [(66.5, 9.5, 25.0, 0.56), (69.0, 10.0, 25.0, 0.62), (72.0, 10.0, 25.0, 0.64),
        (76.0, 10.5, 25.0, 0.6), (80.0, 11.0, 24.5, 0.52), (83.0, 13.0, 24.5, 0.44),
        (85.5, 15.5, 24.5, 0.34), (87.6, 18.0, 24.5, 0.2), (88.6, 19.5, 24.0, 0.08)]
JAW = [(66.5, 29.0, 41.0, 0.4), (70.0, 28.5, 39.5, 0.42), (74.0, 29.0, 37.5, 0.42),
       (79.0, 28.5, 37.5, 0.4), (83.0, 28.0, 37.5, 0.36), (86.0, 26.0, 36.5, 0.26),
       (87.6, 25.0, 33.5, 0.14)]
CORE = [(66.0, 12.0, 40.0, 0.3), (75.0, 12.0, 37.0, 0.3), (86.0, 17.0, 36.0, 0.2),
        (88.4, 20.0, 31.0, 0.06)]


def scaled(sections):
    return [(c, t, b, h * HS) for c, t, b, h in sections]


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshe123"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(118, metallic=0.2, roughness=0.5),  # 0 red shell
        pal(115, metallic=0.15, roughness=0.6),  # 1 dark red shell backs, head
        pal(112, metallic=0.1, roughness=0.8),  # 2 near-black core and gaps
        pal(121, metallic=0.2, roughness=0.4, emission_strength=0.8),  # 3 orange ribs and ridges
        pal(123, metallic=0.2, roughness=0.4, emission_strength=1.2),  # 4 yellow rib (tail end)
        pal(75, metallic=0.1, roughness=0.5),  # 5 pink bone knobs
        pal(69, metallic=0.1, roughness=0.6),  # 6 brown bone knobs underneath
        pal(125, emission_strength=4.0),  # 7 glowing yellow eyes
        pal(127, emission_strength=6.0),  # 8 white-hot eye cores
        pal(118, metallic=0.2, roughness=0.5),  # 9 red limb and head
        pal(73, metallic=0.1, roughness=0.5),  # 10 pink tail hook
    ]
    SHELL, BACK, CORE_M, RIB, YRIB, BONE, BONE_DK, EYE, HOT, LIMB, HOOK = range(11)
    bm = bmesh.new()
    surfaces = []

    # Shell segments: red at the front, darker towards the back, a glowing rib on the front edge.
    for k, (rib, secs) in enumerate(SEGMENTS):
        secs = scaled(secs)
        surfaces.append(secs)
        bands = [SHELL if i < len(secs) - 2 else BACK for i in range(len(secs) - 1)]
        if k in (0, len(SEGMENTS) - 1):
            bands = [BACK] * (len(secs) - 1)
        dome_loft(bm, secs, bands)
        if rib:
            c0, t0, b0, h0 = secs[1]
            c1 = c0 + rib
            dome_loft(bm, [(c0 - 0.6, t0 - 0.2, b0 + 0.2, h0 + 0.025), (c0 + 0.2, t0 - 0.4, b0 + 0.4, h0 + 0.045),
                           (c1 - 0.6, t0 - 0.4, b0 + 0.4, h0 + 0.045), (c1, t0 - 0.1, b0 + 0.1, h0 + 0.02)],
                      YRIB if k == 1 else RIB)
    # A second rib at the back of the tallest segment (column 59).
    c, t, b, h = scaled(SEGMENTS[6][1])[-2]
    dome_loft(bm, [(58.0, t, b - 1, h + 0.01), (58.6, t - 0.3, b - 0.7, h + 0.035), (59.6, t - 0.1, b - 1, h + 0.02)], RIB)

    # Head, jaw and the dark core between them.
    for secs, mat in ((CORE, CORE_M), (HEAD, BACK), (JAW, BACK)):
        secs = scaled(secs)
        surfaces.append(secs)
        dome_loft(bm, secs, mat)

    def z_at(c, r):
        return max(dome_height(s, c, r) for s in surfaces)

    # Orange ridges round the head and jaw, and the streak behind the lower eye.
    def ridge(points, w=1.0, hh=0.03, mat=RIB, lift=0.0):
        sweep(bm, [(c, r, z_at(c, r) + lift, w, hh) for c, r in points], sides=6, mat=mat)
    ridge([(76.5, 11.0), (80.0, 12.0), (83.0, 14.0), (85.2, 17.0), (86.4, 20.5), (86.8, 24.0)], w=1.1)
    ridge([(69.5, 29.6), (74.0, 30.6), (79.0, 31.2), (83.0, 30.8), (85.6, 29.0), (86.6, 26.5)], w=1.1)
    ridge([(72.0, 33.0), (75.0, 35.0), (79.0, 35.8), (84.0, 35.4)], w=0.9)
    ridge([(76.5, 21.0), (80.0, 21.6), (84.0, 22.0)], w=0.9)
    ridge([(76.0, 16.5), (80.0, 17.0), (82.5, 17.5)], w=0.7, mat=LIMB)

    # Two glowing eyes on the upper head (columns 70-77, rows 12-22) with white-hot cores.
    for c, r, rx, ry in ((73.5, 13.8, 3.6, 2.2), (73.8, 20.6, 4.0, 2.3)):
        z = z_at(c, r)
        ellipsoid(bm, c, r, z - 0.02, rx, ry, 0.09, mat=EYE)
        ellipsoid(bm, c - 0.6, r, z + 0.02, rx * 0.68, ry * 0.75, 0.08, mat=HOT)

    # Pink bone knobs along the back, and three down the neck.
    for c, r, rx, ry, rz in ((7.3, 21.5, 2.8, 2.9, 0.14), (20.0, 19.0, 2.2, 1.9, 0.1),
                             (26.0, 18.5, 2.4, 1.7, 0.1), (33.2, 16.0, 3.2, 1.8, 0.11),
                             (42.0, 14.0, 3.4, 1.8, 0.11), (51.8, 12.8, 3.5, 1.9, 0.12),
                             (63.5, 12.5, 2.8, 2.0, 0.12), (64.6, 18.0, 2.8, 1.9, 0.12),
                             (66.0, 23.8, 2.8, 1.7, 0.11), (67.5, 9.6, 2.2, 1.3, 0.08)):
        ellipsoid(bm, c, r, z_at(c, r) - rz * 0.3, rx, ry, rz, mat=BONE)

    # Pink hook curling under the tail tip (columns 4-15, rows 27-34).
    sweep(bm, [(4.6, 26.6, 0.08, 0.0, 0.0), (5.0, 27.5, 0.09, 0.9, 0.06), (6.2, 29.6, 0.1, 1.1, 0.07),
               (7.7, 31.2, 0.1, 1.1, 0.07), (9.4, 32.6, 0.1, 1.1, 0.07), (12.0, 33.4, 0.1, 1.0, 0.065),
               (15.0, 33.6, 0.1, 0.9, 0.06), (16.0, 33.6, 0.1, 0.0, 0.0)], sides=8, mat=HOOK)

    # The thin limb trailing from under the jaw along beneath the body (rows 38-50), with brown
    # knuckles and an orange stripe along its lower edge.
    limb = [(33.5, 43.0), (37.0, 45.8), (41.0, 47.4), (46.0, 47.9), (52.0, 48.2), (58.0, 48.8),
            (64.0, 49.2), (70.0, 49.0), (75.0, 48.2), (79.0, 46.6), (82.5, 44.4), (85.5, 41.6),
            (87.6, 39.6), (88.8, 38.4)]
    sweep(bm, [(c, r, 0.09, 1.6 if c < 80 else 1.2, 0.08) for c, r in limb], sides=8, mat=LIMB)
    sweep(bm, [(c, r + 0.9, 0.1, 0.6, 0.04) for c, r in limb[1:-1]], sides=6, mat=RIB)
    for c, r, rx, ry in ((36.0, 43.2, 2.8, 2.2), (57.5, 47.0, 2.0, 1.7), (69.5, 48.8, 2.4, 1.2)):
        ellipsoid(bm, c, r, 0.12, rx, ry, 0.1, mat=BONE_DK)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshe-123's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshe-123")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    print(f"whole creature: {len(obj.data.polygons)} faces")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(common, ROOT, layout, CX0, CY0, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
