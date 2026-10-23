"""Ground hatch (newsho.shp, assembly of 2 pieces): a 3D version of its sprites.

Seen in level 3.12. Two 2x2 ground enemies side by side (sprite.json `assemblyLayout`, newsho-191
on the left, newsho-193 on the right) make one 48x22 px bunker: a grey concrete frame with a light
bevel on its top and left edges round a dark pit, closed by one big armoured lid. The lid carries
a raised stepped hump (a narrow block on top of a wider one, lit on its top and left edges, set in
a dark groove), slatted vents on both sides with small studs, a lit lip along its front edge and
two latches hanging over it, and three hinge blocks along its back edge.

The five frames of each piece are the lid swinging open on its back hinge (front edge rising
towards the camera, its top face and lit lip foreshortening up the screen until the lid stands
almost on end over the empty pit), so each frame is its own shape: newsho-191 (closed),
newsho-191-f2 ... -f5 and the same for newsho-193. The whole bunker is built once per frame in
assembly coordinates and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsho-191.py [-- --preview out.png]
(the preview is the whole closed bunker; each frame of the whole bunker also gets
<name>-f<k>.png and each exported piece <model>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsho-191"
ROOT = common.repo_root(__file__)
PIECES = ["newsho-191", "newsho-193"]
# Assembly pixel (0, 0) is the top-left corner of newsho-191 (screen cx 129 - 12, cy 39 - 14);
# the assembly is 48 x 28 px and its centre (screen 141, 39) is the Blender origin.
CX0, CY0 = 141, 39
PX = 1 / 12

# Lid angle (degrees, front edge up) for each frame: fitted so the lit lip lands on sprite rows
# 19 (closed), 14, 12, 9 and 7: the lip starts 13 px in front of the hinge (row edge 6), so
# cos(angle) ~ (lip row - 6) / 13.
ANGLES = [0.0, 52.0, 62.0, 77.0, 86.0]

RIM_TOP = 0.30  # top of the concrete frame
CHAMFER_LOW = 0.20  # outer edge of the lit bevel on the frame's top and left sides
FLOOR = 0.03  # pit floor
LID_TOP = 0.26  # lid's top face when closed (also the hinge height)
LID_T = 2.5 * PX  # lid thickness


def X(c):
    """Assembly pixel-edge column (fractions allowed) to Blender X."""
    return (c - 24) / 12


def Y(r):
    """Assembly pixel-edge row to Blender Y: sprite up is +Y."""
    return (14 - r) / 12


# --- geometry helpers --------------------------------------------------------------------------

def box(bm, c0, r0, c1, r1, z0, z1, mat):
    """An axis-aligned block over pixel edges c0..c1, r0..r1, from z0 to z1."""
    pts = [(X(c0), Y(r1)), (X(c1), Y(r1)), (X(c1), Y(r0)), (X(c0), Y(r0))]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)


def plate(bm, outline, z0, z1, mat):
    """A block with an outline of (col, row) pixel edges."""
    pts = [(X(c), Y(r)) for c, r in outline]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)


def prism_x(bm, profile, c0, c1, mats, cap):
    """A profile of (row edge, z) points swept along X from column edge c0 to c1. mats[i] is the
    material of the side between profile points i and i + 1; the two end caps get `cap`."""
    a = [bm.verts.new((X(c0), Y(r), z)) for r, z in profile]
    b = [bm.verts.new((X(c1), Y(r), z)) for r, z in profile]
    bm.faces.new(a).material_index = cap
    bm.faces.new(list(reversed(b))).material_index = cap
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[i]


def prism_y(bm, profile, r0, r1, mats, cap):
    """A profile of (column edge, z) points swept along Y from row edge r0 to r1."""
    a = [bm.verts.new((X(c), Y(r0), z)) for c, z in profile]
    b = [bm.verts.new((X(c), Y(r1), z)) for c, z in profile]
    bm.faces.new(a).material_index = cap
    bm.faces.new(list(reversed(b))).material_index = cap
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[i]


# --- the bunker --------------------------------------------------------------------------------

def materials(sprite, frame):
    tag = "nsho191"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    closed = frame == 0
    lip = [3, 4, 5, 5, 6][frame]  # the lip brightens as it tilts towards the light
    return [
        pal(4, metallic=0.2, roughness=0.7),  # 0 concrete frame
        pal(7, metallic=0.2, roughness=0.6),  # 1 lit bevel, top edge
        pal(6, metallic=0.2, roughness=0.65),  # 2 lit bevel, left edge
        pal(1, metallic=0.0, roughness=0.9),  # 3 dark pit, grooves
        pal(2 if closed else 3, metallic=0.45, roughness=0.45),  # 4 lid top
        pal(2, metallic=0.45, roughness=0.5),  # 5 lid sides, underside, front
        pal(3, metallic=0.5, roughness=0.4),  # 6 highlights on the lid
        pal(lip, metallic=0.6, roughness=0.35),  # 7 lit lip
        pal(5, metallic=0.7, roughness=0.3),  # 8 studs and latches
    ]


FRAME, BEVEL_T, BEVEL_L, PIT, TOP, SIDE, HL, LIP, STUD = range(9)


def build(sprite, frame, coll):
    bm = bmesh.new()
    mats = materials(sprite, frame)

    # Concrete frame round the pit (cols 1-45, rows 2-22; the pit is cols 4-43, rows 4-20). Its
    # top and left outer edges are bevelled (the light rows/columns of the sprite); faces that
    # look into the pit are dark.
    z0, zt, zl = 0.0, RIM_TOP, CHAMFER_LOW
    prism_x(bm, [(2, z0), (2, zl), (3, zt), (4, zt), (4, z0)], 1, 46,
            [FRAME, BEVEL_T, FRAME, PIT, FRAME], FRAME)
    prism_x(bm, [(21, z0), (21, zt), (23, zt), (23, z0)], 4, 46, [PIT, FRAME, FRAME, FRAME], FRAME)
    prism_y(bm, [(1, z0), (1, zl), (2, zt), (4, zt), (4, z0)], 4, 23,
            [FRAME, BEVEL_L, FRAME, PIT, FRAME], FRAME)
    prism_y(bm, [(44, z0), (44, zt), (46, zt), (46, z0)], 4, 21, [PIT, FRAME, FRAME, FRAME], FRAME)
    box(bm, 4, 4, 44, 21, 0.0, FLOOR, PIT)  # pit floor

    # ---- the lid, built closed and then swung open on its back hinge ----
    start = len(bm.verts)
    t = LID_TOP
    b = LID_TOP - LID_T
    # Main plate (rows 8-19) with the lit lip as a bevel on its front top edge (row 19).
    prism_x(bm, [(8, b), (8, t), (19, t), (20, t - 0.07), (20, b)], 5, 43,
            [SIDE, TOP, LIP, SIDE, SIDE], SIDE)
    # Three hinge blocks along the back edge (rows 6-7), split by the gaps at cols 19-20, 28-29.
    for c0, c1 in ((5, 19), (21, 28), (30, 43)):
        box(bm, c0, 6, c1, 8, b, t, TOP)
    box(bm, 5, 8, 6, 19, t, t + 0.008, HL)  # lit left edge (col 5)
    box(bm, 6, 18, 43, 19, t, t + 0.008, PIT)  # groove in front of the lip (row 18)
    # Stepped hump: a wide block (cols 11-37, rows 12-17) under a narrow one (cols 16-32, rows
    # 9-11), in a dark groove, lit on its top and left edges.
    hump = [(11, 12), (16, 12), (16, 9), (33, 9), (33, 12), (38, 12), (38, 18), (11, 18)]
    ring = [(10, 11), (15, 11), (15, 8), (34, 8), (34, 11), (39, 11), (39, 18), (10, 18)]
    inset = [(12, 13), (17, 13), (17, 10), (33, 10), (33, 13), (38, 13), (38, 18), (12, 18)]
    plate(bm, ring, t, t + 0.012, PIT)
    plate(bm, hump, t, t + 0.06, HL)
    plate(bm, inset, t + 0.03, t + 0.075, TOP)
    # Slatted vents on both sides (slats on rows 11-13, 15 and 17 over dark grooves) with studs.
    for c0, c1 in ((6, 10), (39, 43)):
        box(bm, c0, 14, c1, 18, t, t + 0.01, PIT)
        for r0, r1 in ((11, 14), (15, 16), (17, 18)):
            box(bm, c0, r0, c1, r1, t, t + 0.035, TOP)
    for c in (5, 39):
        for r in (15, 17):
            box(bm, c + 0.15, r + 0.15, c + 0.85, r + 0.85, t, t + 0.05, STUD)
    # Two latches hanging over the front edge (cols 21 and 29).
    for c in (21, 29):
        box(bm, c, 19, c + 1, 21, t - 0.13, t + 0.02, STUD)

    a = math.radians(ANGLES[frame])
    ca, sa = math.cos(a), math.sin(a)
    yh, zh = Y(6), LID_TOP
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        dy, dz = v.co.y - yh, v.co.z - zh
        v.co.y = yh + dy * ca + dz * sa
        v.co.z = zh - dy * sa + dz * ca

    return common.mesh_object(f"{NAME}-f{frame + 1}", bm, mats, coll)


def merged_sprite():
    """newsho-191's sprite.json with the colours of both pieces, so any piece's index is valid."""
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, frame, out):
    """The whole bunker's sprite (given frame) as one image, padded to the 24:28 shape that
    render_preview expects for size 4 (48 x 56 px, the bunker in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        fr = data["frames"][frame]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(fr["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new(f"assembly_sprite_{frame}", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def model_name(piece, frame):
    return piece if frame == 0 else f"{piece}-f{frame + 1}"


def main():
    sprite = merged_sprite()
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    datas = {name: common.load_sprite(ROOT, name) for name in PIECES}
    nframes = len(datas[PIECES[0]]["frames"])
    assert nframes == len(ANGLES)
    for frame in range(nframes):
        coll = common.reset_collection(f"{NAME}-f{frame + 1}")
        obj = build(sprite, frame, coll)
        pieces = common.split_assembly(obj, layout)
        for name in PIECES:
            spr = datas[name]["sprites"][0]
            sub = [{**spr, "frames": [spr["frames"][frame]]}]
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{model_name(name, frame)}", sub)
        if preview:
            import tempfile
            ref = composite_png(layout, frame, Path(tempfile.mkdtemp()) / "assembly.png")
            out = preview if frame == 0 else preview.parent / f"{NAME}-f{frame + 1}.png"
            common.render_preview([obj], str(out), ref, size=4, view_px=480)
            for name in PIECES:
                img = ROOT / "reference" / "models" / name / datas[name]["frames"][frame]["image"]
                common.render_preview([pieces[name]], str(preview.parent / f"{model_name(name, frame)}.png"),
                                      img, size=2)
        for o in list(coll.objects):
            o.hide_render = True


if __name__ == "__main__":
    main()
