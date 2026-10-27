"""Helpers shared by batch b104's model scripts (newsh0 blue and violet ground pods).

Coordinates: sprite column c / row r of a 24x28 block. px/row give a pixel's centre, ex/ey a pixel
edge (the left or top edge of column c / row r). ring_loft, tube and run follow lib_b007.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, cap_mats=None):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.

    `mats` gives a material index per band between consecutive rings (an int applies to all, or a
    list with one per band). Caps close the first/last ring (cap_mats = (start, end))."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band):
        return mats[band] if isinstance(mats, (list, tuple)) else mats

    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat(b)
    first = mat(0) if not cap_mats else cap_mats[0]
    last = mat(len(verts) - 2) if not cap_mats else cap_mats[1]
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = first
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = last
    return verts


def superellipse(cx, cy, z, rx, ry, n=16, p=2.0, phase=0.5):
    """n points of a superellipse |x/rx|^p + |y/ry|^p = 1 round (cx, cy) at height z, counter-clockwise.
    p = 2 is an ellipse, larger p is a rounded rectangle."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + phase) / n
        c, s = math.cos(a), math.sin(a)
        x = rx * math.copysign(abs(c) ** (2 / p), c)
        y = ry * math.copysign(abs(s) ** (2 / p), s)
        pts.append((cx + x, cy + y, z))
    return pts


def stack(bm, cx, cy, layers, n=16, mats=0, cap_bottom=True, cap_top=True):
    """A solid built up in Z from superellipse rings: layers = [(z, rx, ry, p), ...] bottom to top
    (rx = ry = 0 makes a point, for a dome's crown). Optional fifth/sixth items offset the ring's
    centre (dx, dy). Domes, rounded blocks, pods sitting on the ground."""
    rings = []
    for layer in layers:
        z, rx, ry, p = layer[:4]
        dx, dy = (layer[4], layer[5]) if len(layer) > 4 else (0.0, 0.0)
        if rx == 0 and ry == 0:
            rings.append([(cx + dx, cy + dy, z)])
        else:
            rings.append(superellipse(cx + dx, cy + dy, z, rx, ry, n=n, p=p))
    # ring_loft caps the first ring facing back along the loft: here that is down, as wanted.
    return ring_loft(bm, rings, mats, cap_start=cap_bottom, cap_end=cap_top)


def dome(bm, cx, cy, z0, rx, ry, h, n=16, steps=4, p=2.0, mats=0, base=0.0):
    """A dome of footprint rx, ry rising h above z0, with a short straight wall `base` below it."""
    layers = [(z0, rx, ry, p)]
    if base > 0:
        layers.append((z0 + base, rx, ry, p))
    for k in range(1, steps):
        a = (math.pi / 2) * k / steps
        layers.append((z0 + base + h * math.sin(a), rx * math.cos(a), ry * math.cos(a), p))
    layers.append((z0 + base + h, 0.0, 0.0, p))
    return stack(bm, cx, cy, layers, n=n, mats=mats)


def prism(bm, outline, z0, z1, mat_index=0, inset=0.0):
    """Extrude a 2D outline (counter-clockwise from above) from z0 to z1. `inset` shrinks the top
    face toward the outline's centroid by that fraction (a chamfered / sloped block)."""
    cx = sum(x for x, _ in outline) / len(outline)
    cy = sum(y for _, y in outline) / len(outline)
    bottom = [(x, y, z0) for x, y in outline]
    top = [(cx + (x - cx) * (1 - inset), cy + (y - cy) * (1 - inset), z1) for x, y in outline]
    return ring_loft(bm, [bottom, top], mat_index)


def tube(bm, p0, p1, radius, sides=8, mat_index=0, caps=True, r1=None):
    """A round bar between two 3D points (radius at p0, r1 at p1 if given)."""
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for c, r in ((a, radius), (b, radius if r1 is None else r1)):
        rings.append([tuple(c + r * (math.cos(t) * u + math.sin(t) * v))
                      for t in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview the first (-- --frames <png>:
    each of its frames).

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
    if "--frames" in sys.argv:  # every frame of the first model beside its sprite (animation check)
        out = sys.argv[sys.argv.index("--frames") + 1]
        common.render_frame_previews(models[0][1], out, sprite, root)
    return sprite
