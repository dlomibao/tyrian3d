"""Red dome turret, damaged (newshs.shp frame 275): the approach C model of newshs-269's damaged frame.

Hit hard enough, the turret (newshs-269.py) shows frame 275 instead of 269: the same outline, but
the housing scorched black down its left side and round the lower right, the grey gun ball burnt
dark, and the red glass dome cracked, with dark streaks (112-113) and ember spots (118-121) where
it was plain glass, its hot spot shrunk to a point.

The intact build is imported (newshs-269.py's build, so geometry and outline are exactly the intact
model's); then the frame-275 pixels repaint it:

- The mesh is cut along every sprite pixel boundary (bisect, x and y), so each face lies in one
  pixel's column and row.
- Each face (not the underside) is repainted from its pixel, comparing frame 275 with frame 269:
  grey parts where 275 went to index 1-2 are scorch (pal_1, rough, not metallic); the gun ball's
  remaining faces go dull dark grey (pal_4); dome faces where 275 shows 112-113 over brighter glass
  are cracks (pal_112), and where 275 is brighter than 269 (>= 118) they are embers in the pixel's
  own index, emissive; the hot spot's faces that 275 no longer lights are plain glass (pal_116).
  The palette indices are the damaged frame's own (art rule 5): the live palette colours them.
- No new geometry: the sprite's damage is paint (burns, embers), and highlights are sheen. The
  grid cuts are dissolved again wherever both sides kept one material (flat runs).

Frame 275 is decoded from data/newshs.shp here (reference/models/ has only the normal frame).

blender -b --factory-startup --python assets/blender/enemies/newshs-269-damaged.py -- \
    [--no-export] [--preview out.png] [--iou]
"""

import importlib.util
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location("newshs_269", Path(__file__).with_name("newshs-269.py"))
I = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(I)

ROOT = I.ROOT
INTACT = I.NAME
NAME = "newshs-269-d"
MODEL = f"enemies/{NAME}"
FRAME, NORMAL = 275, 269
SPRITES = [{"sheet": "newshs.shp", "size": 2, "frames": [FRAME]}]
W, H = 24, 28
U = I.U
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

GREY = {2, 3, 5, 7, 10, 12}  # the intact model's housing, rim, hatch, slots, ball, shine
BALL = {7, 12}
GLASS = {116, 121}


def _decode(sheet, index):
    """data/sprites.ts decodeSprite2: a 12-wide Sprite2, rows of palette indices (-1 transparent)."""
    op = (index - 1) * 2
    p = sheet[op] | (sheet[op + 1] << 8)
    rows, row, x = [], [-1] * 12, 0
    while p < len(sheet) and sheet[p] != 0x0F:
        x += sheet[p] & 0x0F
        count = sheet[p] >> 4
        if count == 0:
            rows.append(row)
            row, x = [-1] * 12, 0
            p += 1
            continue
        for _ in range(count):
            p += 1
            if x < 12:
                row[x] = sheet[p]
            x += 1
        p += 1
    if any(v >= 0 for v in row):
        rows.append(row)
    return rows


def frame_pixels(index):
    """A size-2 frame (tiles index, +1, +19, +20, each 12 x 14) as a 28 x 24 array."""
    sheet = (ROOT / "data" / "newshs.shp").read_bytes()
    out = np.full((H, W), -1, np.int32)
    for off, ox, oy in ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)):
        s = _decode(sheet, index + off)
        for y in range(min(14, len(s))):
            out[oy + y, ox:ox + 12] = s[y]
    return out


def pal_index(mat):
    return int(mat.name.split("_")[1])


def repaint(obj, sprite, normal, damaged):
    """Cut obj along the pixel grid and repaint each face from its frame-275 pixel."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for c in range(1, W):
        x = (c - W / 2) * U
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    for r in range(1, H):
        y = (H / 2 - r) * U
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, y, 0), plane_no=(0, 1, 0))

    slots = {}

    def slot(index, metallic, roughness, emission=0.0):
        key = (index, metallic, roughness, emission)
        if key not in slots:
            mat = common.palette_material(sprite, index, f"{NAME}_{len(slots)}", metallic=metallic,
                                          roughness=roughness, emission_strength=emission)
            me.materials.append(mat)
            slots[key] = len(me.materials) - 1
        return slots[key]

    src = [pal_index(m) for m in me.materials]
    counts = {}
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < -0.3:
            continue
        c = f.calc_center_median()
        col, row = int(np.floor(c.x / U + W / 2)), int(np.floor(H / 2 - c.y / U))
        col, row = min(max(col, 0), W - 1), min(max(row, 0), H - 1)
        o, d = int(normal[row, col]), int(damaged[row, col])
        s = src[f.material_index]
        new = None
        if s in GREY:
            if 0 <= d <= 2 and o > d:
                new, kind = slot(1, 0.1, 0.9), "scorch"
            elif s in BALL:
                new, kind = slot(4, 0.4, 0.7), "ball"
        elif s in GLASS:
            if d in (112, 113) and o >= 114:
                new, kind = slot(112, 0.2, 0.5), "crack"
            elif d >= 118 and o < d:
                new, kind = slot(d, 0.1, 0.2, 3.0), "ember"
            elif s == 121 and 0 <= d < 118:
                new, kind = slot(116, 0.2, 0.12, 2.0), "glow off"
        if new is not None:
            f.material_index = new
            counts[kind] = counts.get(kind, 0) + 1
    # Merge the grid cuts back where they changed nothing (flat runs of one material).
    bmesh.ops.dissolve_limit(bm, angle_limit=np.radians(0.5), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:], delimit={"MATERIAL", "SHARP"})
    bm.to_mesh(me)
    bm.free()
    print(f"{NAME}: repainted {counts}")


def top_mask(objs, px=10):
    """Top orthographic alpha at px samples per sprite pixel, averaged to a 28 x 24 coverage mask."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    scene.render.resolution_x, scene.render.resolution_y = W * px, H * px
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.display.shading.light = "FLAT"
    cam_data = bpy.data.cameras.new("iou_top")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = H * U
    cam = bpy.data.objects.new("iou_top", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 10)
    scene.camera = cam
    hidden = [o for o in scene.objects if o not in objs and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    path = Path(tempfile.mkdtemp()) / "top.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    a = np.array(img.pixels[:], np.float32).reshape(H * px, W * px, 4)[::-1, :, 3]
    for o in hidden:
        o.hide_render = False
    return a.reshape(H, px, W, px).mean(axis=(1, 3))


def main():
    sprite = common.load_sprite(ROOT, INTACT)
    normal = frame_pixels(NORMAL)
    assert np.array_equal(normal, np.array(sprite["frames"][0]["pixels"])), "decoder disagrees with sprite.json"
    damaged = frame_pixels(FRAME)
    for i in np.unique(damaged[damaged >= 0]):
        assert str(int(i)) in sprite["colors"], f"index {i} has no colour in sprite.json"
    I.NAME = NAME  # the intact build names its collection, materials and object after this
    obj = I.build(sprite)
    repaint(obj, sprite, normal, damaged)
    print(f"{NAME}: {len(obj.data.polygons)} faces")

    if "--iou" in argv:
        cov = top_mask([obj])
        model, target = cov > 0.5, damaged >= 0
        iou = (model & target).sum() / max(1, (model | target).sum())
        print(f"{NAME}: top-view IoU vs frame {FRAME} mask {iou:.3f} (miss {(target & ~model).sum()},"
              f" extra {(model & ~target).sum()} px)")
    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        rgba = np.zeros((H, W, 4), np.float32)
        for (r, c), v in np.ndenumerate(damaged):
            if v >= 0:
                rgba[r, c, :3] = np.array(sprite["colors"][str(int(v))]) / 255
                rgba[r, c, 3] = 1
        img = bpy.data.images.new("frame275", W, H, alpha=True)
        img.pixels[:] = rgba[::-1].ravel()
        png = Path(tempfile.mkdtemp()) / f"frame-newshs-{FRAME}.png"
        img.filepath_raw = str(png)
        img.file_format = "PNG"
        img.save()
        common.render_preview([obj], out, str(png), size=2)
    if "--no-export" not in argv:
        common.export_sprite_model(ROOT, [obj], MODEL, SPRITES)


if __name__ == "__main__":
    main()
