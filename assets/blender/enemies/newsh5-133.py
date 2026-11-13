"""Small rocket probe (newsh5.shp frame 133), one frame.

What it is: an indestructible little rocket that shoots UP the screen (4.14 DREAD-NOT: spawned in
rows, (0,-5) px/tick, leaves by the top). The 12x14 sprite read top to bottom is a rocket engine
seen from above: a dark grey ogive nose cap (rows 1-3), a grey capsule body (rows 3-6) girdled by a
glowing red band (row 5), a lighter convergent waist (rows 7-8), a thin dark throat (row 9) and a
flared nozzle bell (rows 10-12) whose rear rim is the ink line of row 13. So the model is a body of
revolution lying along the screen's vertical, nose up (+Y), bell = tail.

Build (D65 hard surface, round where the sprite is round): one lathe profile through pchip stations
whose top-view half widths sit on the inner edge of the 1 px ink ring (D74): 1 px at rows 2, 7-8
and 10, 2 px at rows 3-6 and 11-12, under half a pixel at the throat (row 9, ink only). Machined
detail where the tilted camera sees it: a chamfered seam between nose cap and body, the red band
as a recessed glowing ring between two raised rims, a chamfered shoulder seam, two cooling grooves
on the waist, collars on the throat, a rolled rim on the bell and four swept fins in an X on the
bell (at 45 deg they stay inside the 2 px silhouette from above and from the side). The bell is
open at the rear behind a thick flat rim: a small dark nozzle exit, seen by the tilted camera. Underneath:
the same lathe (closed, nothing added).

Colours (median of each region, darkest shading and brightest highlights ignored): nose 5, body 9,
band 115 (glow), waist 8, throat 3, bell and fins 6, bell interior 3. The 14 streak down column 5
is sheen (art rule 2), the dark row 11 is shading on the bell's shoulder; neither is modelled.
Outline shell (D51) from a sealed copy (outer profile without grooves, bell closed, fins on),
islands="outer" (D189).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh5-133.py
Optional after "--": --top top.png K (top-view silhouette, K image px per sprite px, review only).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy


def arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


HERE = Path(__file__).resolve()


def find_root():
    for p in HERE.parents:  # promoted into assets/blender/enemies/
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    r = arg("--root") or os.environ.get("TYRIAN_ROOT")
    if not r:
        raise SystemExit("pass --root <repo> (or TYRIAN_ROOT) when the script is outside the repo")
    return Path(r).resolve()


ROOT = find_root()
sys.path[:0] = [str(ROOT / "assets" / "blender")]
import common  # noqa: E402

NAME = "newsh5-133"
W, H = 12, 14
PX = 1 / 12
SIDES = 32  # multiple of 8: the fins sit on the 45 deg lines

NOSE, BODY, BAND, WAIST, THROAT, BELL, INNER = 5, 9, 115, 8, 3, 6, 3
# (metallic, roughness, Specular IOR Level, emission strength): satin grey metal; the band glows
# (D126/D173: glow surfaces metallic 1, rough, the colour ~unlit).
FINISH = {
    5: (0.75, 0.38, 0.5, 0.0),
    9: (0.72, 0.34, 0.5, 0.0),
    8: (0.72, 0.36, 0.5, 0.0),
    6: (0.72, 0.4, 0.5, 0.0),
    3: (0.6, 0.55, 0.3, 0.0),
    115: (1.0, 0.85, 0.2, 1.7),
}


def Y(R):
    """Sprite row coordinate (row r spans R in [r, r+1]) to model Y (+Y = up the screen)."""
    return (H / 2 - R) / 12


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) through the stations; returns f(x)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


# --- The lathe profile, (R, radius px) ---------------------------------------------------------
TIP = 1.66
nose_f = pchip([TIP, 1.75, 1.95, 2.25, 2.65, 3.05, 3.4],
               [0.0, 0.42, 0.86, 1.28, 1.64, 1.88, 1.98])
R_BODY = 2.02
waist_f = pchip([7.32, 7.8, 8.3, 8.62, 8.86], [1.16, 1.1, 1.0, 0.86, 0.6])
bell_f = pchip([10.0, 10.2, 10.45, 10.75, 11.05, 11.4, 12.0, 12.6],
               [0.5, 0.72, 1.0, 1.42, 1.8, 1.96, 2.0, 2.0])
R_NECK = 0.34
R_COLLAR = 0.44


def profile():
    """List of (R, radius px, material of the band ending at this station, sharp?)."""
    P = []

    def add(R, r, mat, sharp=False):
        P.append((R, r, mat, sharp))

    # nose cap: rounded tip, ogive
    for R in [TIP, 1.68, 1.71, 1.75, 1.82, 1.9, 2.0, 2.12, 2.26, 2.42, 2.6, 2.8, 3.0, 3.2, 3.32]:
        add(R, nose_f(R), NOSE)
    # chamfered seam nose | body
    add(3.38, nose_f(3.38) - 0.05, NOSE)
    add(3.42, nose_f(3.38) - 0.17, NOSE, True)
    add(3.47, R_BODY - 0.17, THROAT, True)  # dark gap floor
    add(3.52, R_BODY - 0.05, BODY, True)
    add(3.58, R_BODY, BODY)
    add(4.2, R_BODY, BODY)
    # upper band rim (raised hoop, chamfered) then the recessed glowing band
    add(4.62, R_BODY, BODY)
    add(4.66, R_BODY + 0.04, BODY)
    add(4.86, R_BODY + 0.04, BODY)
    add(4.9, R_BODY - 0.02, BODY, True)
    add(4.94, R_BODY - 0.16, BODY, True)
    add(5.0, R_BODY - 0.12, BAND, True)
    add(5.5, R_BODY - 0.08, BAND)
    add(6.0, R_BODY - 0.12, BAND)
    add(6.06, R_BODY - 0.16, BAND, True)
    add(6.1, R_BODY - 0.02, BODY, True)
    add(6.14, R_BODY + 0.04, BODY)
    add(6.34, R_BODY + 0.04, BODY)
    add(6.38, R_BODY, BODY)
    add(6.82, R_BODY, BODY)
    # chamfered shoulder, seam, convergent waist
    add(6.9, R_BODY - 0.06, BODY)
    add(7.02, 1.72, BODY)
    add(7.14, 1.4, BODY)
    add(7.2, 1.3, BODY, True)
    add(7.24, 1.18, THROAT, True)  # seam
    add(7.28, 1.2, WAIST, True)
    add(7.32, waist_f(7.32), WAIST)
    for R in [7.5, 7.66]:
        add(R, waist_f(R), WAIST)
    # cooling grooves
    for g in (7.78, 8.18):
        add(g - 0.03, waist_f(g - 0.03), WAIST, False)
        add(g, waist_f(g) - 0.1, WAIST, True)
        add(g + 0.03, waist_f(g + 0.03), WAIST, True)
    for R in [8.4, 8.55, 8.68, 8.78, 8.86]:
        add(R, waist_f(R), WAIST)
    add(8.92, 0.46, WAIST)
    # throat: rod with two collars
    add(8.96, R_NECK, THROAT, True)
    for c in (9.18, 9.72):
        add(c - 0.06, R_NECK, THROAT)
        add(c - 0.04, R_COLLAR, THROAT, True)
        add(c + 0.04, R_COLLAR, THROAT)
        add(c + 0.06, R_NECK, THROAT, True)
    add(9.98, R_NECK, THROAT)
    # bell
    for R in [10.0, 10.08, 10.2, 10.33, 10.45, 10.6, 10.75, 10.9, 11.05, 11.2, 11.4, 11.6, 11.85]:
        add(R, bell_f(R), BELL, R == 10.0)
    # bell panel groove
    add(11.95, 2.0, BELL)
    add(11.98, 1.9, BELL, True)
    add(12.02, 1.9, BELL, True)
    add(12.05, 2.0, BELL, True)
    add(12.5, 2.0, BELL)
    # rolled rim
    add(12.7, 2.02, BELL)
    add(12.86, 1.98, BELL)
    add(12.94, 1.9, BELL)
    add(12.97, 1.78, BELL)
    # flat rear face (a thick annulus) round a smaller nozzle exit, chamfered into it
    add(12.97, 1.3, BELL, True)
    add(12.93, 1.2, BELL)
    add(12.86, 1.14, BELL)
    # interior cone down to the throat
    add(12.8, 1.1, INNER, True)
    add(12.4, 0.92, INNER)
    add(11.95, 0.7, INNER)
    add(11.55, 0.45, INNER)
    add(11.3, 0.2, INNER)
    add(11.25, 0.0, INNER)
    return P


def sealed_profile():
    """Outer profile without grooves or recesses, bell closed: for the outline shell."""
    P = [(R, nose_f(R)) for R in [TIP, 1.68, 1.72, 1.8, 1.9, 2.05, 2.25, 2.5, 2.8, 3.1, 3.4]]
    P += [(3.5, R_BODY), (6.82, R_BODY), (6.9, R_BODY - 0.06), (7.02, 1.72), (7.14, 1.4), (7.24, 1.2)]
    P += [(R, waist_f(R)) for R in [7.32, 7.6, 8.0, 8.4, 8.7, 8.86]]
    P += [(8.95, 0.42), (10.0, 0.42)]
    P += [(R, bell_f(R)) for R in [10.08, 10.2, 10.35, 10.5, 10.7, 10.9, 11.1, 11.4, 11.8]]
    P += [(12.7, 2.02), (12.88, 1.97), (12.95, 1.8), (12.96, 0.0)]
    return P


def ring_pts(R, r):
    y = Y(R)
    return [(r * PX * math.cos(2 * math.pi * (i + 0.5) / SIDES), y, r * PX * math.sin(2 * math.pi * (i + 0.5) / SIDES))
            for i in range(SIDES)]


def lathe(bm, prof, slot, sharp_edges):
    rings = []
    for R, r, *_ in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((0.0, Y(R), 0.0))])
        else:
            rings.append([bm.verts.new(p) for p in ring_pts(R, r)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        mat = prof[i + 1][2] if len(prof[i + 1]) > 2 else 0
        for k in range(SIDES):
            j = (k + 1) % SIDES
            if len(a) == 1:
                f = bm.faces.new((a[0], b[k], b[j]))
            elif len(b) == 1:
                f = bm.faces.new((a[k], b[0], a[j]))
            else:
                f = bm.faces.new((a[k], b[k], b[j], a[j]))
            f.material_index = slot.get(mat, 0)
            f.smooth = True
        if len(prof[i + 1]) > 3 and prof[i + 1][3] and len(b) > 1:
            for k in range(SIDES):
                sharp_edges.append((b[k], b[(k + 1) % SIDES]))
    return rings


def fins(bm, slot, sealed=False):
    """Four swept fins in an X on the bell. 2D outline in (R, radial px), extruded +-T."""
    T = 0.17  # half thickness, px
    outline = [(10.72, 1.1), (11.25, 2.62), (12.62, 2.72), (12.88, 2.5), (12.88, 1.7), (10.72, 1.1)]
    outline = outline[:-1]
    for q in range(4):
        a = math.radians(45 + 90 * q)
        u = (math.cos(a), math.sin(a))      # radial direction in XZ
        n = (-math.sin(a), math.cos(a))     # fin normal in XZ
        vs = []
        for s in (-1, 1):
            for R, rad in outline:
                rr = rad * PX
                vs.append(bm.verts.new((u[0] * rr + n[0] * s * T * PX, Y(R), u[1] * rr + n[1] * s * T * PX)))
        m = len(outline)
        faces = [list(reversed(vs[:m])), vs[m:]]
        for k in range(m):
            j = (k + 1) % m
            faces.append([vs[k], vs[j], vs[m + j], vs[m + k]])
        for fv in faces:
            f = bm.faces.new(fv)
            f.material_index = slot.get(BELL, 0)
            f.smooth = False
    return bm


def build(sprite, coll):
    indices = sorted(FINISH)
    mats = []
    for i in indices:
        met, rough, spec, em = FINISH[i]
        m = common.palette_material(sprite, i, NAME, metallic=met, roughness=rough, emission_strength=em)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        mats.append(m)
    slot = {i: k for k, i in enumerate(indices)}
    bm = bmesh.new()
    sharp = []
    lathe(bm, profile(), slot, sharp)
    fins(bm, slot)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    for a, b in sharp:
        e = bm.edges.get((a, b))
        if e:
            e.smooth = False
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=None)
    return obj


def sealed_shell(coll):
    bm = bmesh.new()
    prof = [(R, r) for R, r in sealed_profile()]
    lathe(bm, prof, {}, [])
    fins(bm, {}, sealed=True)
    src = common.mesh_object(f"{NAME}_sealed", bm, [], coll, smooth=True)
    sh = common.outline_shell(src, coll, voxel=0.006, faces=1200, inside=0.003, islands="outer")
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.context.view_layer.update()
    sh.name = f"{NAME}_outline"
    sh.data.name = f"{NAME}_outline"
    return sh


def render_top(obj, out, k):
    """Orthographic top-view silhouette on the sprite's grid (W*k x H*k), alpha = model."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = W * k, H * k
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filter_size = 0.0
    try:
        scene.display.render_aa = "OFF"
    except Exception:
        pass
    cam_d = bpy.data.cameras.new("top_cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = max(W, H) / 12
    cam = bpy.data.objects.new("top_cam", cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    hidden = []
    for o in scene.objects:
        if o.type == "MESH" and o is not obj and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    sh = sealed_shell(coll)
    assert len(sh.data.polygons) > 0, f"{sh.name}: empty outline shell"
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles, shell {len(sh.data.polygons)} faces")
    common.export_sprite_model(ROOT, [obj, sh], f"enemies/{NAME}", sprite["sprites"])
    if "--top" in sys.argv:
        i = sys.argv.index("--top")
        render_top(obj, str(Path(sys.argv[i + 1]).resolve()), int(sys.argv[i + 2]))


if __name__ == "__main__":
    main()
