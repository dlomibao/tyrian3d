"""A player ship's banking frames as the game draws them: the model rolled and moved sideways, measured
against each banking sprite (DECISIONS.md D92, docs/agents/OUTLINE-BORDER.md "Banking frames").

    blender -b --factory-startup --python tools/bank_roll.py -- <name> [--glb model.glb] [--fit] [--k 10]
            [--roll HALF,FULL] [--shift L2,L1,0,R1,R2] [--png sheet.png]

<name> is the ship's folder in reference/models (ship-u-ship, ship-usp-talon-light-fighter, ...).
The model is the one whose src/render/spriteModels/*.json entry replaces the ship's level frame
(public/models/<model>.glb), or --glb. Each frame is rendered top down (outline shell and
tyrian_ground hidden) the way src/render/drawListRenderer.ts draws it:

- rolled about the model's long axis by the entry's roll for that bank step (`bank.roll`, degrees at
  bank steps 1..max; without it 35 degrees * step / max, the game's old MAX_ROLL), the low wing on the
  side the ship moves to (frame base - step * n for moving left);
- moved sideways by the entry's `bank.shift` (game px per frame, left to right), or without it by
  the frame's opaque-column centre minus the level frame's (src/render/bankShift.ts, D62); a ship
  drawn in two halves (`group`) isn't moved;

and measured with tools/sprite_mask.py (iou_rule_grid, D74). Accept (D92): the level frame >= 0.95,
each half-bank frame >= 0.80 and each full-bank frame >= 0.70, at the ship's roll and shift.

--fit sweeps each bank step's roll (2.5 degree steps, never less than the step below it) and each
frame's shift (0.5 px steps, within 3 px of bankShift's; bankShift's kept unless another beats it by
more than SHIFT_TOL), for the mean IoU of the step's left and right frames, keeps the roll nearest
the default among those within FIT_TOL of the best (the game's roll stays unless the art clearly
draws another), and prints the `roll` (and `shift`, if any differs from bankShift's) to put in the
script's sprites entry (common.with_bank_roll). --roll and --shift try values without rebuilding.
--png writes a sheet: each frame's sprite beside the model's top view over the frame's masks (green
model on inner, red model outside it, blue inner not covered).
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as sm  # noqa: E402

PX = 1 / 12  # Blender units per sprite pixel (assets/blender/common.py)
DEFAULT_FULL_ROLL = 35.0  # degrees at full bank without bank.roll (src/render/spriteModels.ts)
LEVEL_MIN, HALF_MIN, FULL_MIN = 0.95, 0.80, 0.70
FIT_TOL = 0.02  # --fit keeps the roll nearest the default among those this close to the best mean IoU
SHIFT_TOL = 0.01  # ... and bankShift's shift unless another beats it by more than this


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = {"name": a[0], "glb": None, "fit": "--fit" in a, "k": 10, "roll": None, "shift": None, "png": None}
    for key in ("--glb", "--k", "--roll", "--shift", "--png"):
        if key in a:
            opt[key[2:]] = a[a.index(key) + 1]
    opt["k"] = int(opt["k"])
    for key in ("roll", "shift"):
        if opt[key]:
            opt[key] = [float(v) for v in opt[key].split(",")]
    return opt


def moved(top, dx_px):
    """The render moved dx_px image pixels right (exact for the orthographic top view), zero filled."""
    out = np.zeros_like(top)
    if dx_px > 0:
        out[:, dx_px:] = top[:, :-dx_px]
    elif dx_px < 0:
        out[:, :dx_px] = top[:, -dx_px:]
    else:
        out[:] = top
    return out


def frame_rows(sprite, index):
    f = next(f for f in sprite["frames"] if f["index"] == index)
    return [[int(v) for v in row.split()] for row in f["pixels"]]


def centre_x(rows):
    """bankShift.ts visibleCentreX: the middle of the opaque columns."""
    cols = [x for x in range(len(rows[0])) if any(r[x] >= 0 for r in rows)]
    return (cols[0] + cols[-1] + 1) / 2


def model_entry(ref):
    for p in sorted((ROOT / "src" / "render" / "spriteModels").glob("*.json")):
        e = json.loads(p.read_text())
        for s in e["sprites"]:
            if s["sheet"] == ref["sheet"] and s["size"] == ref["size"] and s["frames"][0] == ref["frames"][0]:
                return e, s
    raise SystemExit(f"no spriteModels entry replaces {ref['sheet']} frame {ref['frames'][0]}")


def rolls_of(bank, override=None):
    """Degrees at bank steps 1..max."""
    if override:
        return list(override)
    if bank.get("roll"):
        return [float(v) for v in bank["roll"]]
    return [DEFAULT_FULL_ROLL * n / bank["max"] for n in range(1, bank["max"] + 1)]


class TopView:
    """The model under an orthographic top camera on the sprite's grid."""

    def __init__(self, glb, w, h, k):
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.ops.import_scene.gltf(filepath=str(glb))
        for o in bpy.data.objects:
            if o.type == "MESH" and (o.get("tyrian_outline") or o.get("tyrian_ground")):
                o.hide_render = True
        self.root = bpy.data.objects.new("bank_root", None)
        bpy.context.scene.collection.objects.link(self.root)
        for o in bpy.data.objects:
            if o.parent is None and o is not self.root:
                o.parent = self.root
        sc = self.scene = bpy.context.scene
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "FLAT"
        sc.display.shading.color_type = "SINGLE"
        sc.display.shading.single_color = (1, 1, 1)
        sc.render.film_transparent = True
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.view_settings.view_transform = "Standard"
        sc.render.resolution_x, sc.render.resolution_y = w * k, h * k
        sc.display.render_aa = "OFF"
        cam = bpy.data.objects.new("bank_cam", bpy.data.cameras.new("bank_cam"))
        sc.collection.objects.link(cam)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = max(w, h) * PX
        cam.data.clip_end = 1000
        cam.location = (0, 0, 50)
        sc.camera = cam
        self.dir = Path(tempfile.mkdtemp(prefix="bank_roll_"))
        self.n = 0

    def render(self, roll_deg, shift_px):
        """(alpha mask as rows of bools, top row first; the PNG). The game's roll is three.js rotation.z =
        -roll (roll > 0 when moving right); glTF +Z is Blender -Y, so that is +roll about Blender +Y."""
        self.root.matrix_world = Matrix.Translation((shift_px * PX, 0, 0)) @ Matrix.Rotation(math.radians(roll_deg), 4, "Y")
        self.n += 1
        path = self.dir / f"t{self.n}.png"
        self.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(path))
        w, h = img.size
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, 3] > 0.5
        bpy.data.images.remove(img)
        return a, path


def rule_iou(m, top):
    """sprite_mask.measure's iou_rule_grid, in numpy (for the sweep)."""
    inner, free = np.array(m["inner"], bool), np.array(m["free"], bool)
    h, w = inner.shape
    k = top.shape[1] // w
    grid = top.reshape(h, k, w, k).mean(axis=(1, 3)) >= 0.5
    keep = ~free
    union = ((grid | inner) & keep).sum()
    return float(((grid & inner) & keep).sum() / union) if union else 1.0


def sheet_png(path, rows_list):
    """One row per frame: the sprite and the diff (green model on inner, red outside, blue missed),
    8x. rows_list: (rows, colors, masks, grid, label)."""
    s = 8
    tiles = []
    for rows, colors, m, grid, _ in rows_list:
        h, w = len(rows), len(rows[0])
        spr = np.zeros((h, w, 3), np.uint8) + 40
        dif = np.zeros((h, w, 3), np.uint8) + 25
        for y in range(h):
            for x in range(w):
                v = rows[y][x]
                if v >= 0:
                    spr[y, x] = colors[v]
                inner, border, g = m["inner"][y][x], m["border"][y][x], grid[y, x]
                dif[y, x] = ((60, 200, 60) if inner and g else (220, 60, 60) if g else (60, 90, 230) if inner
                             else (120, 90, 40) if border else (25, 25, 25))
        tiles.append(np.concatenate([spr, np.zeros((h, 1, 3), np.uint8), dif], axis=1).repeat(s, 0).repeat(s, 1))
    pad = np.zeros((s, tiles[0].shape[1], 3), np.uint8)
    out = np.concatenate([t for tile in tiles for t in (tile, pad)], axis=0)
    hh, ww = out.shape[:2]
    img = bpy.data.images.new("bank_sheet", ww, hh)
    rgba = np.concatenate([out[::-1].astype(np.float32) / 255, np.ones((hh, ww, 1), np.float32)], axis=2)
    img.pixels = rgba.ravel()
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()


def main():
    o = args()
    sprite = json.loads((ROOT / "reference" / "models" / o["name"] / "sprite.json").read_text())
    ref = sprite["sprites"][0]
    entry, sref = model_entry(ref)
    bank = sref.get("bank") or ref.get("bank")
    base = ref["frames"][0]
    glb = Path(o["glb"]) if o["glb"] else ROOT / "public" / "models" / f"{entry['model']}.glb"
    rows0 = frame_rows(sprite, base)
    h, w = len(rows0), len(rows0[0])
    view = TopView(glb, w, h, o["k"])
    colors = {int(k): tuple(v) for k, v in sprite["colors"].items()}
    steps = bank["max"] if bank else 0
    grouped = bool(sref.get("group"))

    def frame_of(n):
        return base + n * (bank["step"] if bank else 0)

    def bank_shift(n):
        """bankShift.ts: the frame's opaque-column centre minus the level frame's."""
        return 0.0 if grouped or n == 0 else centre_x(frame_rows(sprite, frame_of(n))) - centre_x(rows0)

    given_shift = o["shift"] or (bank or {}).get("shift")

    def shift_of(n):
        return 0.0 if grouped or n == 0 else float(given_shift[n + steps]) if given_shift else bank_shift(n)

    masks = {n: sm.masks(frame_rows(sprite, frame_of(n)), colors) for n in range(-steps, steps + 1)}
    k = o["k"]

    def best_shift(n, deg):
        """(IoU, shift): the frame at roll deg, at bankShift's shift or a better one (D92)."""
        top = view.render(deg, bank_shift(n))[0]
        at = rule_iou(masks[n], top)
        if grouped:
            return at, 0.0
        tries = [(rule_iou(masks[n], moved(top, int(round(d * k)))), d) for d in np.arange(-3, 3.01, 0.5) if d]
        iou, d = max(tries)
        return (iou, bank_shift(n) + d) if iou > at + SHIFT_TOL else (at, bank_shift(n))

    if o["fit"] and steps:
        rolls_fit, shifts_fit, lo = [], {0: 0.0}, 0.0
        for n in range(1, steps + 1):
            curve = []
            for i in range(0, 33):
                deg = i * 2.5
                if deg < lo:
                    continue
                left, right = best_shift(-n, -deg), best_shift(n, deg)
                curve.append(((left[0] + right[0]) / 2, deg, left, right))
            top = max(c[0] for c in curve)
            # The game's roll stays unless the art clearly asks for another: of the angles within
            # FIT_TOL of the best, the one nearest the default.
            default = DEFAULT_FULL_ROLL * n / steps
            pick = min((c for c in curve if c[0] >= top - FIT_TOL), key=lambda c: (abs(c[1] - default), -c[0]))
            rolls_fit.append(pick[1])
            shifts_fit[-n], shifts_fit[n] = pick[2][1], pick[3][1]
            lo = pick[1]
            best = max(curve, key=lambda c: c[0])
            print(f"fit step {n}: {pick[1]:g} deg  frame {frame_of(-n)} {pick[2][0]:.4f} shift {pick[2][1]:+g}  "
                  f"frame {frame_of(n)} {pick[3][0]:.4f} shift {pick[3][1]:+g}  (best {best[1]:g} deg, mean "
                  f"{best[0]:.4f}; default {default:g} deg)")
        line = f'"roll": {json.dumps([round(v, 1) for v in rolls_fit])}'
        fitted_shift = [shifts_fit[n] for n in range(-steps, steps + 1)]
        if any(abs(fitted_shift[n + steps] - bank_shift(n)) > 1e-9 for n in range(-steps, steps + 1)):
            line += f', "shift": {json.dumps(fitted_shift)}'
        print(f"fit: {line}   (bankShift's: {[bank_shift(n) for n in range(-steps, steps + 1)]})")

    rolls = rolls_of(bank, o["roll"]) if bank else []
    report, ok, sheet = [], True, []
    for n in range(-steps, steps + 1):
        deg = math.copysign(rolls[abs(n) - 1], n) if n else 0.0
        shift = shift_of(n)
        top, path = view.render(deg, shift)
        r = sm.measure(masks[n], sm.read_png_mask(path))
        bar = LEVEL_MIN if n == 0 else FULL_MIN if abs(n) == steps else HALF_MIN
        good = r["iou_rule_grid"] >= bar
        ok &= good
        report.append({"frame": frame_of(n), "step": n, "roll": deg, "shift": shift, "iou_rule_grid": r["iou_rule_grid"],
                       "bar": bar, "ok": good})
        print(f"{o['name']} frame {frame_of(n)} step {n:+d} roll {deg:+.1f} shift {shift:+.1f}: "
              f"iou_rule_grid {r['iou_rule_grid']:.4f} (>= {bar}) {'ok' if good else 'FAIL'}")
        grid = top.reshape(h, k, w, k).mean(axis=(1, 3)) >= 0.5
        sheet.append((frame_rows(sprite, frame_of(n)), colors, masks[n], grid, f"{frame_of(n)}"))
    print(json.dumps({"name": o["name"], "model": entry["model"], "roll": rolls, "shift": given_shift, "frames": report, "ok": ok}))
    if o["png"]:
        sheet_png(o["png"], sheet)


main()
