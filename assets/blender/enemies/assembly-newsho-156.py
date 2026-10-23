"""Grey walker base (newsho.shp, 7 pieces of assembly-newsho-156): a 3D version of its sprites.

Seen in episode 3 (level 3.12). Seven 2x2 ground enemies make the lower half of a big machine
whose top half (newshk-51/53/55, not in this batch) is on fire: a grey deck with a dark slatted
panel inside a rounded blue hull, three grey feet under its front edge (newsho-120, 122, 124),
and on each side a grey arm (newsho-118 + 156 on the left, 126 + 164 on the right): a bracket
at the top, a post down to two shiny pistons that join into one ram, ending in a round drum
with a hub. The right arm is the left one mirrored (about screen pixel column 115).

The whole thing is built once in screen pixel coordinates (sprite.json `assemblyLayout`), with
screen pixel edge (116, 93) as the origin, then cut into the pieces with common.split_assembly.
All pieces are single frames.

Run: blender --background --python assets/blender/enemies/assembly-newsho-156.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b092 as lib  # noqa: E402

NAME = "assembly-newsho-156"
ROOT = common.repo_root(__file__)
PIECES = ["newsho-156", "newsho-164", "newsho-118", "newsho-120", "newsho-122", "newsho-124", "newsho-126"]
CX0, CY0 = 116, 93
S = lib.Space(CX0, CY0)
PX = lib.PX
ARM_AXIS = S(115.5, 0)[0]  # screen pixel x maps to 230 - x between the arms


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsho156"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.3, roughness=0.6),  # 0 near-black panel and recesses
        pal(3, metallic=0.4, roughness=0.5),  # 1 dark grey
        pal(4, metallic=0.5, roughness=0.45),  # 2 grey plating
        pal(5, metallic=0.5, roughness=0.4),  # 3 mid grey
        pal(6, metallic=0.55, roughness=0.4),  # 4 light grey edges
        pal(7, metallic=0.6, roughness=0.35),  # 5 bright grey
        pal(9, metallic=0.75, roughness=0.25),  # 6 shiny piston
        pal(54, metallic=0.35, roughness=0.45),  # 7 dark blue
        pal(56, metallic=0.35, roughness=0.4),  # 8 blue hull
        pal(57, metallic=0.35, roughness=0.35),  # 9 light blue
        pal(8, metallic=0.75, roughness=0.25),  # 10 piston
    ]
    PANEL, DARK, GREY, MID, LIGHT, BRIGHT, SHINY, BLUE_D, BLUE, BLUE_L, PISTON = range(11)
    bm = bmesh.new()

    def rect(x0, y0, x1, y1):
        return [S(x0, y1), S(x1, y1), S(x1, y0), S(x0, y0)]

    def box(x0, y0, x1, y1, z0, z1, mat, top=None, r=0.0, steps=1):
        lib.rounded_prism(bm, rect(x0, y0, x1, y1), z0, z1, r=r, steps=steps, mat=mat, top_mat=top)

    def poly(points, z0, z1, mat, top=None, r=0.0, steps=2):
        lib.rounded_prism(bm, [S(x, y) for x, y in points], z0, z1, r=r, steps=steps, mat=mat, top_mat=top)

    # ---- left arm (newsho-118 above, newsho-156 below), mirrored to the right afterwards ----
    arm_start = len(bm.verts)
    # Top bracket: a beam across (rows 69-73) with a short hook down at its inner end.
    box(60.5, 68.5, 77.0, 73.5, 0.0, 0.42, GREY, top=DARK, r=0.05)
    box(73.8, 72.0, 77.5, 75.5, 0.0, 0.40, LIGHT, top=GREY, r=0.04)
    # Outer post under the beam's outer end, chamfered on its inner top edge.
    box(60.5, 70.0, 65.5, 77.8, 0.0, 0.38, MID, top=PANEL, r=0.08, steps=2)
    # Shadowed gap under the beam and the second, lower beam (rows 75-79).
    box(65.0, 73.0, 74.0, 75.5, 0.0, 0.16, PANEL)
    box(65.5, 75.0, 74.2, 79.6, 0.0, 0.32, GREY, top=DARK, r=0.04)
    box(72.6, 77.6, 74.2, 79.6, 0.30, 0.33, BRIGHT)  # its lit corner
    # Dark recess beside the post (rows 79-82).
    box(69.0, 79.0, 74.5, 82.6, 0.0, 0.1, PANEL)
    # Post down to the pistons (columns 65-68, rows 79-86) with its lit right edge.
    box(64.6, 78.5, 69.6, 86.6, 0.0, 0.3, MID, top=DARK, r=0.04)
    box(67.8, 79.0, 69.4, 86.2, 0.29, 0.31, LIGHT)
    # Collar where the two pistons leave the post (row 86).
    box(65.4, 85.6, 72.0, 87.4, 0.0, 0.28, LIGHT, top=BRIGHT, r=0.04)
    # Two pistons side by side (rows 87-95): the left one thicker.
    xa, xb = S(67.6, 0)[0], S(71.1, 0)[0]
    ra, rb = 1.6 * PX, 1.15 * PX
    lib.tube(bm, [(xa, S(0, 87.0)[1], ra, ra), (xa, S(0, 95.0)[1], ra, ra)], sides=10, mat=SHINY)
    lib.tube(bm, [(xb, S(0, 87.0)[1], rb, rb), (xb, S(0, 96.0)[1], rb, rb)], sides=8, mat=PISTON)
    # Cross bar joining them to the side box (rows 94-95).
    box(62.6, 93.6, 72.6, 96.4, 0.0, 0.25, GREY, top=MID, r=0.04)
    # The ram they join into (columns 67-71, rows 96-105), with a groove at row 100.
    xr = S(69.9, 0)[0]
    rr = 2.5 * PX
    lib.tube(bm, [(xr, S(0, 95.5)[1], rr, rr * 0.9), (xr, S(0, 99.6)[1], rr, rr),
                  (xr, S(0, 99.8)[1], rr, rr * 0.82), (xr, S(0, 100.7)[1], rr, rr * 0.82),
                  (xr, S(0, 100.9)[1], rr, rr), (xr, S(0, 105.6)[1], rr, rr)], sides=12, mat=SHINY)
    # Side box left of the ram (columns 62-66, rows 96-104) and a small bracket right of it.
    box(61.8, 96.0, 67.2, 105.2, 0.0, 0.3, MID, top=GREY, r=0.05)
    box(72.4, 98.6, 76.4, 104.6, 0.0, 0.22, LIGHT, top=GREY, r=0.04)
    # Drum at the end (columns 66-74, rows 106-115): a grey ring round a dark recess, with a hub.
    cx, cy = S(70.5, 111.0)
    lib.rounded_prism(bm, lib.circle(cx, cy, 4.8 * PX, n=20), 0.0, 0.28, r=0.06, steps=2, mat=LIGHT, top_mat=MID)
    lib.rounded_prism(bm, lib.circle(cx, cy, 3.2 * PX, n=16), 0.27, 0.285, mat=PANEL)
    hx, hy = S(70.5, 112.4)
    lib.rounded_prism(bm, lib.circle(hx, hy, 1.7 * PX, n=12), 0.2, 0.34, r=0.03, steps=1, mat=MID, top_mat=GREY)
    lib.rounded_prism(bm, lib.circle(hx, hy, 0.6 * PX, n=8), 0.3, 0.345, mat=PANEL)
    # Dark side plate left of the drum.
    box(63.0, 105.5, 66.5, 114.5, 0.0, 0.18, DARK, r=0.03)

    lib.mirror_from(bm, arm_start, ARM_AXIS)

    # ---- body (newsho-120, 122, 124) ----
    # Blue hull with a rounded rim, running up past the pieces' top edge (the burning half).
    hull = [(90, 66), (90, 73), (88, 74), (88, 81.5), (89, 83), (91, 84.3), (93, 85.3), (95, 86),
            (137, 86), (139, 85.2), (141, 84.3), (142.4, 83), (143, 81.5), (143, 74), (141.4, 73),
            (141.4, 66)]
    poly(hull, 0.0, 0.2, BLUE, top=BLUE_D, r=0.09, steps=3)
    # Grey deck inside it (columns 92-136), dark on top.
    box(92.0, 66.0, 137.4, 77.6, 0.0, 0.3, DARK, top=PANEL, r=0.03)
    # Side rails of the deck, the left one lit along its outer edge.
    box(92.0, 66.0, 95.6, 77.4, 0.28, 0.35, LIGHT, top=GREY, r=0.03)
    box(134.6, 66.0, 137.4, 77.4, 0.28, 0.35, GREY, top=GREY, r=0.03)
    # Slatted vents at both ends of the panel: a post and three slats each.
    for x0, x1, post in ((96.0, 104.0, 96.0), (128.0, 134.4, 130.0)):
        box(post, 66.0, post + 1.0, 76.0, 0.29, 0.33, MID)
        for y in (69.0, 71.9, 73.9):
            box(x0, y, x1, y + 1.0, 0.29, 0.32, DARK)
    # Ledge along the front of the panel (row 76) with two bolts.
    box(95.6, 75.9, 134.6, 77.1, 0.29, 0.33, DARK)
    for x in (112.0, 120.0):
        box(x, 75.9, x + 1.0, 77.1, 0.3, 0.36, BRIGHT)
    # Front lip (rows 78-79).
    box(92.0, 77.4, 137.4, 80.4, 0.0, 0.26, GREY, top=GREY, r=0.05, steps=2)
    # Three grey feet under the front edge (rows 81-86); the middle one has a round lit nose.
    box(101.8, 80.0, 106.8, 86.3, 0.0, 0.24, MID, top=GREY, r=0.05, steps=2)
    box(123.8, 80.0, 127.2, 86.3, 0.0, 0.24, MID, top=GREY, r=0.05, steps=2)
    box(111.6, 80.0, 119.2, 85.0, 0.0, 0.24, DARK, top=GREY, r=0.04)
    yn = S(0, 84.8)[1]
    lib.tube(bm, [(S(111.6, 0)[0], yn, 0.14, 1.7 * PX), (S(119.2, 0)[0], yn, 0.14, 1.7 * PX)], sides=10, mat=BRIGHT)
    box(112.0, 85.5, 119.0, 87.4, 0.0, 0.1, GREY)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        # 120 x 140 sprite px centred on the origin covers all seven pieces (size 10 tiles).
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 120, 140)
        common.render_preview([obj], str(out), str(ref), size=10, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
