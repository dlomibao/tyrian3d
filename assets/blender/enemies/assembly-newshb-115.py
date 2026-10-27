"""Blue-pipe machine (newshb.shp, assembly of 15 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.10). Fifteen 2x2 ground enemies side by side make one 120x84 px
structure (sprite.json `assemblyLayout`): two big dark-blue pipes run down the screen, each with
a grey grille clamp, a ribbed grey canister and a glowing blue lamp on its outer side, and bend
into a heart-shaped loop of pipe at the bottom. The loop sits on a round grey platform with
lavender side panels and a ribbed collar; inside it is a dark pool with a stepped grey block.
Two gun ports flank the loop (in newshb-117 and newshb-121), and lattice towers stand at both
sides, leaning back (they are drawn tall in the sprite).

The structure is built once in assembly coordinates (left half mirrored about the pipes' axis,
assembly pixel column 59.5), then cut into its fifteen pieces with common.split_assembly.

newshb-117's port has a sliding hatch: closed (frame 117), a quarter open (195), half open
(233), and open with a muzzle flash (197, 235, 271, 273, which only vary the flash), so it gets
four models: newshb-117, -f2, -f3 and -f4. newshb-121's port is always open and only flashes, so
one model covers its five frames. The flashes animate (common.frame_part, one per frame): in -f4
a small dim flash (197), a big one (235), a dying ember with the hatch's edge sliding back in
(271) and the biggest (273); in newshb-121 none (121), a dim spark (199), the biggest (201), a
medium red one (237) and a bright one (275).

Run: blender --background --python assets/blender/enemies/assembly-newshb-115.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b121 as L  # noqa: E402

NAME = "assembly-newshb-115"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-39", "newshb-41", "newshb-43", "newshb-45", "newshb-47",
          "newshb-77", "newshb-79", "newshb-81", "newshb-83", "newshb-85",
          "newshb-115", "newshb-117", "newshb-119", "newshb-121", "newshb-123"]
# Assembly pixel (0, 0) is the top-left corner of newshb-39 (screen 163, -31); the assembly is
# 120 x 84 px and its centre (screen 223, 11) is the Blender origin.
CX0, CY0 = 223, 11
F = L.Frame(60, 42)
AXIS = 59.5  # pixel edge between the two pipes' mirror images
AX = F.x(AXIS)
TOWER_AXIS = 58.5  # the towers mirror about pixel column 58 (edge 58.5 + 0.5)


def mirror_col(e):
    return 2 * AXIS - e


# Hatch states of newshb-117's port: (model suffix, frames, hatch's left edge or None if open).
HATCH = [("", [117], 25.0), ("-f2", [195], 27.0), ("-f3", [233], 29.0), ("-f4", [197, 235, 271, 273], None)]
PORT_L = (25.0, 59.0, 33.0, 68.0)  # left port opening (pixel edges c0, r0, c1, r1)
HATCH_271 = 31.0  # on frame 271 the hatch's edge shows at the port's right side
BASE_TOP = 0.10
COLLAR_TOP = 0.18


def materials(sprite):
    tag = "nshb115"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(8, metallic=0.5, roughness=0.5),  # 0 base floor grey
        pal(10, metallic=0.5, roughness=0.45),  # 1 light grey collar
        pal(12, metallic=0.5, roughness=0.4),  # 2 bright ribs, caps, hatch
        pal(90, metallic=0.3, roughness=0.5),  # 3 lavender side panels
        pal(86, metallic=0.3, roughness=0.55),  # 4 dark purple top plates
        pal(54, metallic=0.6, roughness=0.25),  # 5 blue pipes
        pal(57, metallic=0.6, roughness=0.2),  # 6 blue loop
        pal(50, metallic=0.3, roughness=0.4),  # 7 dark pool inside the loop
        pal(4, metallic=0.5, roughness=0.6),  # 8 dark grey clamp body, recesses
        pal(7, metallic=0.5, roughness=0.45),  # 9 mid grey tiles, block
        pal(6, metallic=0.5, roughness=0.5),  # 10 tower shafts
        pal(154, emission_strength=4.0),  # 11 blue lamps
        pal(141, emission_strength=5.0),  # 12 lamp hot spot
        pal(2, metallic=0.2, roughness=0.8),  # 13 port interior
        pal(116, emission_strength=2.0),  # 14 ember in the right port
        pal(120, emission_strength=3.5),  # 15 muzzle flash
        pal(126, emission_strength=5.0),  # 16 flash core
        pal(9, metallic=0.5, roughness=0.45),  # 17 tower bodies
    ]


(BASE, COLLAR, RIB, LAV, PURP, PIPE, LOOP, POOL, CLAMP, TILE, SHAFT, LAMP, HOT, PORT, EMBER, FLASH,
 CORE, TOWER) = range(18)

# Muzzle flashes: (centre column, centre row (pixel edges, as in the sprites), {frame: blobs from the
# outside in, as (material, radius px)}). DIM is the dark red flash_materials() adds.
DIM = 18
FLASH_117 = (28.6, 64.3, {197: [(EMBER, 1.8)], 235: [(FLASH, 3.2), (CORE, 1.6)], 271: [(DIM, 1.2)],
                          273: [(FLASH, 3.6), (CORE, 2.6)]})
FLASH_121 = (91.4, 63.4, {199: [(DIM, 1.6)], 201: [(FLASH, 3.8), (CORE, 2.4)], 237: [(EMBER, 2.4), (FLASH, 1.2)],
                          275: [(FLASH, 3.0), (CORE, 1.6)]})


def flash_materials(sprite, mats):
    """materials() plus the dark red of the faintest flashes (DIM)."""
    return mats + [common.palette_material(sprite, 113, "nshb115", emission_strength=1.5)]


def tower(bm, col, rows, z_of, stub=None):
    """A leaning lattice tower along the sprite at edge column `col`: rows is a list of (row,
    half_width_px) from its tip down to its foot; z_of(row) is the height of its axis there."""
    secs = [(r, w, w * L.PX * 0.9 if w else 0.0, z_of(r)) for r, w in rows]
    L.loft_y(bm, F, col, secs, sides=8, mat=TOWER)
    if stub:  # a side stub sticking out of a drum: (col0, col1, row, half_height_px)
        c0, c1, r, h = stub
        L.sweep(bm, F, [(c0, r, z_of(r), 0.0, 0.0), (c0 + 0.3, r, z_of(r), h, h * L.PX * 0.9),
                        (c1, r, z_of(r), h, h * L.PX * 0.9)], sides=6, mat=TILE)


def build_left_half(bm):
    # Round platform: the bottom of a disc, its upper edge rising diagonally to the pipes.
    outline = [(AXIS, 45.0), (53.0, 44.0), (33.0, 38.5), (17.5, 45.5), (4.8, 52.2), (4.5, 58.0),
               (5.5, 64.0), (7.5, 70.0), (10.5, 76.0), (14.0, 81.0), (16.5, 85.0), (AXIS, 85.0)]
    L.prism(bm, F, outline, 0.0, BASE_TOP, mat=BASE)
    # Lavender rim panel on its outer edge, sloping up inward, with a bright inner lip.
    rim = [(17.5, 45.5), (4.8, 52.2), (4.5, 58.0), (5.5, 64.0), (7.5, 70.0), (10.5, 76.0), (14.0, 81.0),
           (16.5, 85.0), (17.0, 85.0), (17.0, 46.0)]
    tops = [0.2, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.2, 0.2]
    L.prism(bm, F, rim, 0.0, tops, mat=LAV)
    L.prism(bm, F, [(17.0, 45.8), (18.2, 45.2), (18.2, 85.0), (17.0, 85.0)], 0.0, 0.22, mat=RIB)
    # Ribbed collar between the rim and the loop.
    L.prism(bm, F, [(18.2, 45.2), (33.0, 38.5), (34.5, 40.0), (34.5, 62.0), (36.0, 70.0), (40.0, 76.0),
                    (45.0, 81.0), (48.5, 85.0), (18.2, 85.0)], 0.0, COLLAR_TOP, mat=COLLAR)
    for c0, c1 in ((19.0, 20.0), (21.0, 22.0)):
        L.prism(bm, F, [(c0, 44.8), (c1, 44.2), (c1, 85.0), (c0, 85.0)], 0.1, COLLAR_TOP + 0.03, mat=RIB)
    # Curved steps on the collar, round the loop (the diagonal bands at the bottom left).
    for radius, a0, a1 in ((34.0, 205, 237), (39.0, 200, 227)):
        pts = []
        for k in range(8):
            a = math.radians(a0 + (a1 - a0) * k / 7)
            pts.append((AXIS + radius * math.cos(a), 55.0 - radius * math.sin(a), COLLAR_TOP, 0.8, 0.025))
        L.sweep(bm, F, pts, sides=4, mat=SHAFT, smooth=False)
    # Lavender post beside the loop (columns 28-31, rows 40-58).
    L.box(bm, F, 28.0, 39.5, 32.0, 58.0, 0.1, 0.27, mat=LAV)
    # Gun port housing (columns 24-33, rows 58-68); the hatch and flash are added per model.
    c0, r0, c1, r1 = PORT_L
    L.box(bm, F, c0 - 1, r0 - 1.5, c1 + 1, r0, 0.1, 0.28, mat=COLLAR)
    L.box(bm, F, c0 - 1, r1, c1 + 1, r1 + 1.2, 0.1, 0.28, mat=COLLAR)
    L.box(bm, F, c0 - 1, r0, c0, r1, 0.1, 0.28, mat=COLLAR)
    L.box(bm, F, c1, r0, c1 + 1, r1, 0.1, 0.28, mat=COLLAR)
    L.box(bm, F, c0, r0, c1, r1, 0.1, 0.19, mat=PORT)

    # Big pipe down the screen (columns 33-52), into the top of the loop.
    L.loft_y(bm, F, 43.0, [(-1.0, 10.0, 0.27, 0.34), (41.0, 10.0, 0.27, 0.34), (44.5, 8.5, 0.23, 0.32),
                           (47.5, 5.0, 0.17, 0.3)], sides=16, mat=PIPE)
    # Grey grille clamp over its top (columns 35-47, rows 0-16).
    L.box(bm, F, 35.0, -1.0, 48.0, 17.0, 0.2, 0.635, mat=CLAMP)
    for r0, r1 in ((-1.0, 3.0), (4.0, 8.0), (10.0, 16.0)):
        for cc0, cc1 in ((35.0, 40.0), (41.0, 43.0), (44.0, 48.0)):
            L.box(bm, F, cc0 + 0.15, r0 + 0.15, cc1 - 0.15, r1 - 0.15, 0.6, 0.665, mat=TILE)
    # Ribbed grey canister lying on the pipe's outer side (columns 36-40, rows 29-41).
    secs = [(28.6, 0.0, 0.0, 0.6)]
    for k in range(14):
        r = 29.0 + k
        secs.append((r, 2.0, 0.07, 0.6))
        secs.append((r + 0.5, 2.6, 0.095, 0.6))
    secs.append((43.0, 2.0, 0.07, 0.6))
    secs.append((43.3, 0.0, 0.0, 0.6))
    L.loft_y(bm, F, 38.5, secs, sides=8, mat=TILE)
    # Glowing blue lamp on the pipe's outer side (columns 24-31, rows 19-41).
    L.ellipsoid(bm, F, 28.4, 30.5, 0.3, 4.2, 11.5, 0.2, mat=LAMP, segments=14, rings=8)
    L.ellipsoid(bm, F, 28.6, 26.5, 0.37, 2.2, 3.8, 0.13, mat=HOT, segments=10, rings=6)
    # Thin rod between the pipes (column 54, rows 15-31).
    L.loft_y(bm, F, 54.5, [(14.8, 0.0, 0.0, 0.12), (15.3, 0.75, 0.06, 0.12), (31.5, 0.75, 0.06, 0.12),
                           (32.0, 0.0, 0.0, 0.12)], sides=6, mat=TILE)
    # Purple plate reaching in from above (columns 23-31, rows 0-6).
    L.prism(bm, F, [(22.5, -1.0), (32.0, -1.0), (32.0, 3.5), (30.5, 6.2), (27.0, 6.2), (24.0, 3.0), (22.5, 1.0)],
            0.0, 0.3, mat=PURP)


def build_towers(bm):
    # Tall tower (column 15, rows 1-46): mast with two nodes, a drum, a shaft and a wide drum.
    za = lambda r: 0.14 + (46.0 - r) * 0.0085  # noqa: E731
    tower(bm, 15.5, [(0.8, 0.0), (1.2, 1.2), (3.8, 1.2), (4.2, 0.6), (8.0, 0.6), (8.3, 2.3), (10.7, 2.3),
                     (11.0, 0.6), (14.0, 0.6), (14.3, 3.0), (23.5, 3.0), (26.0, 2.3), (27.0, 1.6), (36.0, 1.6),
                     (36.6, 4.0), (45.0, 4.0), (47.0, 3.0), (48.0, 0.0)], za, stub=(10.0, 13.0, 20.0, 2.2))
    # Short tower (column 6, rows 17-50): mast with two nodes, a drum and a foot.
    zb = lambda r: 0.13 + (50.0 - r) * 0.0085  # noqa: E731
    tower(bm, 6.5, [(16.8, 0.0), (17.2, 1.2), (19.8, 1.2), (20.2, 0.6), (24.0, 0.6), (24.3, 2.3), (26.7, 2.3),
                    (27.0, 0.6), (29.8, 0.6), (30.2, 3.0), (39.0, 3.0), (42.5, 2.4), (43.2, 2.0), (46.0, 2.0),
                    (46.3, 2.5), (48.5, 2.5), (51.5, 2.0), (52.5, 0.0)], zb, stub=(1.0, 4.0, 35.5, 2.6))


def build_centre(bm):
    # The loop of pipe: heart-shaped, two lobes meeting in a dip at the top.
    left = [(59.5, 50.6), (55.0, 48.7), (49.0, 47.6), (43.5, 48.2), (39.5, 51.0), (37.6, 56.0), (38.3, 62.0),
            (41.3, 67.6), (46.5, 71.2), (53.0, 72.8), (59.5, 73.3)]
    loop = left + [(mirror_col(c), r) for c, r in reversed(left[1:-1])]
    L.sweep(bm, F, [(c, r, 0.3, 5.0, 0.18) for c, r in loop], sides=10, mat=LOOP, closed=True)
    # Dark pool inside it.
    L.prism(bm, F, loop, 0.0, BASE_TOP + 0.03, mat=POOL)
    # Stepped grey block in the middle (columns 51-66, rows 53-83).
    L.box(bm, F, 55.5, 53.0, 63.5, 58.0, 0.1, 0.22, mat=TILE)
    L.box(bm, F, 56.5, 54.0, 62.5, 57.0, 0.22, 0.24, mat=RIB)
    L.box(bm, F, 53.0, 57.5, 66.0, 63.0, 0.1, 0.27, mat=TILE)
    L.box(bm, F, 54.0, 58.5, 65.0, 61.8, 0.27, 0.29, mat=COLLAR)
    L.box(bm, F, 51.0, 62.5, 68.0, 85.0, 0.1, 0.31, mat=SHAFT)
    for r in (63.5, 67.5, 71.5, 75.5, 79.5):
        L.box(bm, F, 51.6, r, 67.4, r + 1.2, 0.31, 0.33, mat=COLLAR)
    L.box(bm, F, 58.8, 62.5, 60.2, 85.0, 0.31, 0.34, mat=CLAMP)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = bmesh.new()
    n = len(bm.verts)
    build_left_half(bm)
    L.mirror_since(bm, n, AX)
    n = len(bm.verts)
    build_towers(bm)
    L.mirror_since(bm, n, F.x(TOWER_AXIS + 0.5))
    build_centre(bm)
    # The right port is always open; its flashes (newshb-121) are separate frame parts.
    return L.to_object(NAME, bm, mats, coll), mats


def flash_objects(mats, flash, piece_offset, name, coll):
    """One object per frame of `flash` (FLASH_117 or FLASH_121): its glowing blobs at the port, in
    the piece's coordinates, shown only on that frame. Frame 271 also gets the hatch's edge."""
    col, row, frames = flash
    x0, y0 = piece_offset
    parts = []
    for frame, blobs in frames.items():
        bm = bmesh.new()
        for k, (mat, r) in enumerate(blobs):
            L.ellipsoid(bm, F, col, row, 0.21 + 0.04 * k, r, r, 0.06 - 0.01 * k, mat=mat, segments=12, rings=6)
        if frame == 271:
            c0, r0, c1, r1 = PORT_L
            L.box(bm, F, HATCH_271, r0, c1, r1, 0.19, 0.265, mat=RIB)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        parts.append(common.frame_part(L.to_object(f"{name}-{frame}", bm, mats, coll), [frame]))
    return parts


def hatch_object(mats, hatch_left, piece_offset, name, coll):
    """newshb-117's sliding hatch (or the muzzle flash when it's open), in the piece's coordinates."""
    c0, r0, c1, r1 = PORT_L
    bm = bmesh.new()
    if hatch_left is not None:
        L.box(bm, F, hatch_left, r0, c1, r1, 0.19, 0.265, mat=RIB)
        L.box(bm, F, hatch_left + 0.2, r0 + 0.8, hatch_left + 1.0, r1 - 0.8, 0.265, 0.28, mat=COLLAR)
    else:
        L.ellipsoid(bm, F, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.21, 3.4, 3.4, 0.07, mat=FLASH, segments=12, rings=6)
        L.ellipsoid(bm, F, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.24, 1.8, 1.8, 0.06, mat=CORE, segments=10, rings=5)
    x0, y0 = piece_offset
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    return L.to_object(name, bm, mats, coll)


def merged_sprite():
    data = common.load_sprite(ROOT, "newshb-115")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole machine's sprite (layout frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 10 (120 x 140 px, the machine in the middle)."""
    rows = [[(0.0, 0.0, 0.0, 0.0)] * 120 for _ in range(140)]
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        want = next(e["frame"] for e in data["assemblyLayout"] if e["model"] == name)
        frame = next((f for f in data["frames"] if want.endswith(f"|{f['index']}")), data["frames"][0])
        x0, y0 = cx + 60 - 12, cy + 70 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    rows[y0 + r][x0 + c] = (*(ch / 255 for ch in data["colors"][str(v)]), 1.0)
    return L.write_png(out, 120, 140, rows)


def main():
    sprite = merged_sprite()
    obj, mats = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    offsets = {name: (cx / 12, -cy / 12) for name, cx, cy in layout}
    pieces = common.split_assembly(obj, layout)
    coll = obj.users_collection[0]
    fmats = flash_materials(sprite, mats)
    exported = {}  # model name -> (objects, sprite image)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        if name == "newshb-121":
            objs = [pieces[name]] + flash_objects(fmats, FLASH_121, offsets[name], f"{name}-flash", coll)
            common.export_sprite_model(ROOT, objs, f"enemies/{name}", data["sprites"])
            exported[name] = (objs, data["frames"][0]["image"], name)
            continue
        if name != "newshb-117":
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
            exported[name] = ([pieces[name]], data["frames"][0]["image"], name)
            continue
        for suffix, frames, hatch_left in HATCH:
            model = name + suffix
            if hatch_left is None:
                extra = flash_objects(fmats, FLASH_117, offsets[name], f"{model}-flash", coll)
            else:
                extra = [hatch_object(mats, hatch_left, offsets[name], f"{model}-hatch", coll)]
            sprites = [dict(s, frames=[f for f in s["frames"] if f in frames]) for s in data["sprites"]]
            sprites = [s for s in sprites if s["frames"]]
            common.export_sprite_model(ROOT, [pieces[name]] + extra, f"enemies/{model}", sprites)
            exported[model] = ([pieces[name]] + extra, f"frame-newshb-{frames[0]}.png", name)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        # Whole machine with newshb-117's hatch a quarter open (the layout frame, 195).
        whole_hatch = hatch_object(mats, HATCH[1][2], (0.0, 0.0), "whole-hatch", coll)
        common.render_preview([obj, whole_hatch], str(out), ref, size=10, view_px=640)
        for model, (objs, image, piece) in exported.items():
            img = ROOT / "reference" / "models" / piece / image
            common.render_preview(objs, str(out.parent / f"{model}.png"), img, size=2)
    if "--frames" in sys.argv:  # every frame of the animated models, one row each
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for model, piece in (("newshb-117-f4", "newshb-117"), ("newshb-121", "newshb-121")):
            data = common.load_sprite(ROOT, piece)
            frames = {f for s in json.loads((ROOT / "src/render/spriteModels" / f"{model}.json").read_text())["sprites"]
                      for f in s["frames"]}
            data["frames"] = [f for f in data["frames"] if f["index"] in frames]
            common.render_frame_previews(exported[model][0], str(out.parent / f"{model}.png"), data, ROOT)


if __name__ == "__main__":
    main()
