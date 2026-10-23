"""Armoured eye sphere (newsh9.shp 153, 155, 157, 191, 193, 195, assembly of 6 pieces): a 3D
version of its sprites.

Seen in episode 4 (levels 4.4 and 4.20). Six 2x2 enemies side by side (sprite.json
`assemblyLayout`) make the top 72x56 px of a round machine about 72 px across: a grey ball of
armour plates with a raised swirl on top (a C-shaped boss with two bright studs, curling round
into a glowing blue strip), a latch rod set into each flank, and a big blue eye with a dark pupil
and a dark cross across it at the front (bottom of the screen). The bottom of the ball is drawn by
other pieces (newsh9-210, 212, 214, a separate assembly), so it is cut off here.

The whole ball is built once in assembly coordinates, then cut into the six pieces with
common.split_assembly. Each piece has one frame, so each gets one model.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-191.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh9-191"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]
# Assembly pixel (0, 0) is the top-left corner of newsh9-153 (screen cx 137 - 12, cy -18 - 14).
# The six pieces cover 72 x 56 px; their centre (screen 161, -4) is the Blender origin.
CX0, CY0 = 161, -4
PX = 1 / 12  # one sprite pixel in units

# The ball: centre and radii in assembly pixels (pixel edges), and its height above/below z = 0.
BU, BV, BRU, BRV = 36.0, 34.5, 36.0, 35.2
ZT, ZB = 0.55, 0.25
# The eye: centre and radii (pixels) and how far it bulges out of the ball.
EU, EV, ERU, ERV = 35.8, 50.5, 20.8, 14.6
EYE_LIFT, EYE_BULGE = 0.03, 0.11


def X(u):
    """Assembly x in pixels (pixel edges; a pixel's centre is col + 0.5) to Blender X."""
    return (u - 36) * PX


def Y(v):
    """Assembly y in pixels (pixel edges) to Blender Y: sprite up is +Y."""
    return (28 - v) * PX


def zs(u, v):
    """Height of the ball's top surface over assembly pixel (u, v)."""
    e = ((u - BU) / BRU) ** 2 + ((v - BV) / BRV) ** 2
    return ZT * math.sqrt(max(0.0, 1 - e))


def zeye(u, v):
    """Height of the eye's surface (a lens bulging out of the ball)."""
    e = ((u - EU) / ERU) ** 2 + ((v - EV) / ERV) ** 2
    return zs(u, v) + EYE_LIFT + EYE_BULGE * math.sqrt(max(0.0, 1 - e))


# --- geometry helpers --------------------------------------------------------------------------

def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=8, mat=0, smooth=True, surface=zs):
    """A flattened tube lying on a surface along a path of (u, v, lift, half_width_px,
    half_height). The tube's centre sits `lift` above the surface; rings stand across the path.
    A ring of zero size collapses to a point (a rounded or pointed end)."""
    before = set(bm.faces)
    pts = [Vector((X(u), Y(v), surface(u, v) + lift)) for u, v, lift, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _tag(bm, before, mat, smooth)


def cap(bm, cu, cv, ru, rv, top, bottom, mat=0, rings=5, segs=24, smooth=True):
    """An elliptical cap centred on assembly pixel (cu, cv) with radii (ru, rv) px: a top surface
    at height top(u, v) and a bottom at bottom(u, v), joined round the rim. The top is a grid of
    concentric rings, so it follows a curved surface."""
    before = set(bm.faces)

    def ring(t, fn):
        if t == 0:
            return [bm.verts.new((X(cu), Y(cv), fn(cu, cv)))]
        out = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            u, v = cu + ru * t * math.cos(a), cv - rv * t * math.sin(a)
            out.append(bm.verts.new((X(u), Y(v), fn(u, v))))
        return out

    ts = [i / rings for i in range(rings + 1)]
    tops = [ring(t, top) for t in ts]
    rim_bottom = ring(1.0, bottom)
    centre_bottom = ring(0.0, bottom)
    for r0, r1 in zip(tops, tops[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[k], r1[j]))
            else:
                bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
    rim = tops[-1]
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new((rim[k], rim_bottom[k], rim_bottom[j], rim[j]))
        bm.faces.new((rim_bottom[j], rim_bottom[k], centre_bottom[0]))
    _tag(bm, before, mat, smooth)


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def on(lift):
    """A height function: `lift` above the ball's surface."""
    return lambda u, v: zs(u, v) + lift


# --- the machine -------------------------------------------------------------------------------

def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9a191"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.55, roughness=0.4),  # 0 grey armour
        pal(4, metallic=0.4, roughness=0.6),  # 1 seams between plates and recesses
        pal(11, metallic=0.6, roughness=0.35),  # 2 raised swirl
        pal(13, metallic=0.7, roughness=0.3),  # 3 swirl rims, latch rods
        pal(14, metallic=0.8, roughness=0.2),  # 4 bright studs
        pal(132, metallic=0.3, roughness=0.2, emission_strength=2.0),  # 5 glowing blue strip
        pal(156, metallic=0.2, roughness=0.15, emission_strength=2.0),  # 6 blue eye
        pal(97, metallic=0.4, roughness=0.1),  # 7 pupil
        pal(53, metallic=0.3, roughness=0.3),  # 8 dark cross over the eye
        pal(8, metallic=0.6, roughness=0.35),  # 9 plates round the swirl
        pal(2, metallic=0.4, roughness=0.6),  # 10 dark slots, pupil ring
    ]
    ARMOUR, SEAM, SWIRL, RIM, STUD, STRIP, EYE, PUPIL, CROSS, PLATE, SOCKET = range(11)
    bm = bmesh.new()

    # The ball: a squashed sphere, taller above than below.
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    for v in res["verts"]:
        x, y, z = v.co
        v.co = Vector((X(BU) + x * BRU * PX, Y(BV) + y * BRV * PX, z * (ZT if z > 0 else ZB)))
    _tag(bm, before, ARMOUR, True)

    # Seams between the armour plates.
    def seam(points, w=1.1, h=0.014, lift=0.0):
        sweep(bm, [(u, v, lift, w, h) for u, v in points], sides=6, mat=SEAM)

    seam([(24.5, 3.0), (26.5, 6.5), (28.5, 9.6), (34.5, 9.6), (36.0, 5.5), (37.5, 2.0)])
    seam([(49.5, 14.2), (54.0, 14.0), (58.0, 13.6), (63.2, 13.8)])
    seam([(49.8, 13.0), (49.6, 20.0), (49.6, 27.0), (50.4, 35.0)])
    seam([(50.0, 26.0), (54.0, 25.8), (58.5, 26.2)])
    seam([(3.5, 20.0), (6.5, 22.0), (9.5, 24.5), (15.5, 25.6)])
    seam([(3.0, 38.0), (8.0, 40.0), (14.5, 43.5)])
    seam([(36.0, 9.8), (42.0, 9.0), (49.5, 13.0)])

    # Raised swirl on top: a rounded boss with a rim round its left and top (the C) ...
    cap(bm, 38.5, 20.5, 5.0, 9.5, on(0.035), on(-0.03), mat=PLATE, rings=3, segs=20)
    cap(bm, 28.0, 21.0, 11.8, 11.6, lambda u, v: zs(u, v) + 0.04 + 0.06 * math.sqrt(
        max(0.0, 1 - ((u - 28.0) / 11.8) ** 2 - ((v - 21.0) / 11.6) ** 2)), on(-0.03), mat=SWIRL, rings=4, segs=28)
    sweep(bm, [(18.5, 29.5, 0.06, 0.0, 0.0), (18.0, 27.5, 0.06, 1.6, 0.04), (17.6, 21.0, 0.065, 2.4, 0.05),
               (18.6, 15.0, 0.07, 2.5, 0.05), (21.5, 11.6, 0.07, 2.5, 0.05), (26.0, 10.2, 0.07, 2.4, 0.05),
               (31.0, 10.4, 0.06, 1.8, 0.04), (34.5, 11.8, 0.055, 0.0, 0.0)], sides=8, mat=RIM)
    # ... a lower arm curling right and up towards the blue strip ...
    sweep(bm, [(22.0, 31.0, 0.05, 0.0, 0.0), (24.0, 31.2, 0.055, 1.6, 0.04), (31.0, 31.8, 0.065, 2.4, 0.05),
               (37.5, 30.2, 0.065, 2.4, 0.05), (41.0, 27.8, 0.06, 1.9, 0.045), (42.6, 25.0, 0.055, 1.6, 0.04),
               (43.0, 23.5, 0.05, 0.0, 0.0)], sides=8, mat=RIM)
    # ... and two bright studs.
    cap(bm, 26.5, 17.5, 2.8, 2.6, lambda u, v: zs(u, v) + 0.05 + 0.08 * math.sqrt(
        max(0.0, 1 - ((u - 26.5) / 2.8) ** 2 - ((v - 17.5) / 2.6) ** 2)), on(0.0), mat=STUD, rings=3, segs=14)
    cap(bm, 33.0, 21.8, 2.3, 3.0, lambda u, v: zs(u, v) + 0.05 + 0.07 * math.sqrt(
        max(0.0, 1 - ((u - 33.0) / 2.3) ** 2 - ((v - 21.8) / 3.0) ** 2)), on(0.0), mat=STUD, rings=3, segs=14)

    # The glowing blue strip curving from the top of the swirl round and down its right side.
    sweep(bm, [(38.6, 9.8, 0.03, 0.0, 0.0), (39.2, 10.6, 0.035, 2.4, 0.04), (41.0, 12.5, 0.04, 3.4, 0.045),
               (43.8, 15.0, 0.04, 3.4, 0.045), (45.6, 17.8, 0.04, 3.2, 0.045), (46.5, 21.0, 0.04, 2.8, 0.045),
               (46.6, 24.0, 0.04, 2.6, 0.045), (46.6, 26.0, 0.035, 2.4, 0.04)], sides=8, mat=STRIP)

    # A latch rod set into each flank, slanting down and in, in a dark slot.
    for path in ([(9.2, 30.5), (11.2, 34.5), (13.6, 39.6)], [(61.8, 31.0), (60.0, 34.6), (57.8, 38.6)]):
        (u0, v0), _, (u1, v1) = path
        dx = 1.4 if u0 < 36 else -1.4
        sweep(bm, [(u0 - dx, v0 + 0.4, 0.0, 0.0, 0.0)] + [(u - dx * 0.8, v + 0.3, 0.0, 1.6, 0.025) for u, v in path]
              + [(u1 - dx * 0.4, v1 + 1.0, 0.0, 0.0, 0.0)], sides=6, mat=SOCKET)
        sweep(bm, [(u0, v0, 0.03, 0.0, 0.0)] + [(u, v, 0.035, 1.0, 0.035) for u, v in path]
              + [(u1 + (u1 - u0) * 0.08, v1 + 0.6, 0.03, 0.0, 0.0)], sides=6, mat=RIM)

    # The eye: a dark socket, the blue lens, the pupil and the dark cross over it.
    cap(bm, EU, EV, ERU + 1.0, ERV + 1.0, on(0.02), on(-0.04), mat=SOCKET, rings=2, segs=40)
    cap(bm, EU, EV, ERU, ERV, zeye, on(-0.03), mat=EYE, rings=6, segs=40)
    cap(bm, 35.8, 51.4, 5.2, 6.4, lambda u, v: zeye(u, v) + 0.012, lambda u, v: zeye(u, v) - 0.02,
        mat=PUPIL, rings=3, segs=16)
    sweep(bm, [(36.5, EV - ERV - 0.2, 0.002, 0.0, 0.0), (36.5, EV - ERV + 0.6, 0.004, 0.65, 0.014),
               (36.5, EV - 7.0, 0.006, 0.65, 0.016), (36.5, EV + 7.0, 0.006, 0.65, 0.016),
               (36.5, EV + ERV - 0.6, 0.004, 0.65, 0.014), (36.5, EV + ERV + 0.2, 0.002, 0.0, 0.0)],
          sides=6, mat=CROSS, surface=zeye)
    sweep(bm, [(EU - ERU - 0.2, 51.0, 0.002, 0.0, 0.0), (EU - ERU + 0.6, 51.0, 0.004, 0.65, 0.014),
               (EU - 10.0, 51.0, 0.006, 0.65, 0.016), (EU + 10.0, 51.0, 0.006, 0.65, 0.016),
               (EU + ERU - 0.6, 51.0, 0.004, 0.65, 0.014), (EU + ERU + 0.2, 51.0, 0.002, 0.0, 0.0)],
          sides=6, mat=CROSS, surface=zeye)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh9-191's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh9-191")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole object's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 6 (72 x 84 px, the object in the middle)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 36 - 12, cy + 42 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
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
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
