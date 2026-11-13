"""Red slashed ring (newshv.shp frames 190, 209, 228): a 3D version of its sprite.

What it is: a small mine that the steel-blue beetle pod (newshv-197) drops in episode 2 (level 17).
It hangs where it's released and pulses brighter over frames 190 / 209 / 228. Seen from above it's a
dark-red ring (8x8 px, a squarish circle) crossed by a "/" slash: two wedge-shaped vanes, one in each
half, joined across the middle by a thin axle and to the ring at their outer corners by short stubs.
The upper-right vane carries the bright knob (pixel 7,5: 71 / 73 / 75), a glowing cap. On frame 228
the lower vane grows two little prongs (pixels 4,6 and 6,8, palette 66), shown on that frame only.

It flies free, so it's closed all round: the ring is a faired torus (squarish outside, round inside,
rounded section, a little lower below than above), the vanes are rounded cushions, the knob a dome.

Built in sprite pixels (x right, y down the sprite, z up; 12 px = 1 unit; the 12x14 block's centre
is pixel edge (6, 7)), converted to Blender units as it goes. Colours are the sprite's palette index
per region (ring 67, vanes and prongs 66, stubs and axle 65, knob 71), each stepping to the frame's
brighter index (palette_material frames=). Shading is the game's light. The ring and vanes glow
faintly (the pulse); the knob glows (metallic 1 / rough, D126/D173). Outline shell from a sealed
copy (D90/D118). Helpers adapted from lib_b054 (copied, not imported).

Run: blender --background --python assets/blender/enemies/newshv-190.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402

NAME = "newshv-190"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

CX, CY = 6.0, 7.0  # the ring's centre, in pixel-edge coordinates

# material slots
RING, VANE, DARK, KNOB = range(4)


def to_b(x, y, z=0.0):
    """Sprite pixel-edge coordinates (x right, y down, z up, in px) to Blender units."""
    return Vector(((x - CX) / 12, (CY - y) / 12, z / 12))


# --- helpers ------------------------------------------------------------------------------------

def ccw(poly):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return list(reversed(poly)) if area < 0 else list(poly)


def inset_polygon(poly, d):
    """Move each vertex of a counter-clockwise polygon `d` inward."""
    out = []
    n = len(poly)
    for i, (x, y) in enumerate(poly):
        ax, ay = poly[i - 1]
        bx, by = poly[(i + 1) % n]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        out.append((x - ty / ln * d, y + tx / ln * d))
    return out


def fillet(poly, r, steps=5):
    """Round every corner of a polygon with an arc of radius r (tangent to both edges)."""
    out = []
    n = len(poly)
    for i in range(n):
        p = Vector(poly[i])
        a = (Vector(poly[i - 1]) - p).normalized()
        b = (Vector(poly[(i + 1) % n]) - p).normalized()
        ang = math.acos(max(-1.0, min(1.0, a.dot(b))))
        t = r / math.tan(ang / 2)  # corner to the tangent points
        pa, pb = p + a * t, p + b * t
        c = p + (a + b).normalized() * (r / math.sin(ang / 2))
        a0 = math.atan2(pa.y - c.y, pa.x - c.x)
        a1 = math.atan2(pb.y - c.y, pb.x - c.x)
        d = a1 - a0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        for k in range(steps + 1):
            u = a0 + d * k / steps
            out.append((c.x + r * math.cos(u), c.y + r * math.sin(u)))
    return out


def cushion(bm, outline, z, top, bottom, bevel, steps=4, mat_index=0, crown=0.0, keel=0.0):
    """A closed cushion over a counter-clockwise outline (Blender units): its rim at height z, rounded
    shoulders (inset up to `bevel`) rising `top` above and sinking `bottom` below; the caps rise to a
    low crown (`crown` above the top) and sink to a keel (`keel` below the bottom) at their centres."""
    rings_top, rings_bot = [], []
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        inset = bevel * (1 - math.cos(a))
        poly = inset_polygon(outline, inset) if inset > 1e-9 else outline
        rings_top.append([bm.verts.new((x, y, z + top * math.sin(a))) for x, y in poly])
        rings_bot.append([bm.verts.new((x, y, z - bottom * math.sin(a))) for x, y in poly])
    n = len(outline)
    faces = []
    for rings in (rings_top, rings_bot):
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        faces.append(bm.faces.new(rings[-1]))
    caps = [faces[len(faces) // 2 - 1], faces[-1]]
    bmesh.ops.remove_doubles(bm, verts=rings_top[0] + rings_bot[0], dist=1e-7)
    for f in faces:
        if f.is_valid:
            f.material_index = mat_index
    for cap, dz in zip(caps, (crown, -keel)):
        res = bmesh.ops.poke(bm, faces=[cap])
        for v in res["verts"]:
            v.co.z += dz


def tube(bm, points, widths, heights, sides=10, mat_index=0):
    """A closed tube along a polyline (Blender units) with a horizontal and a vertical radius per
    point; its ends close with a short cone."""
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * math.cos(2 * math.pi * (k + 0.5) / sides) * widths[i]
                                   + up * math.sin(2 * math.pi * (k + 0.5) / sides) * heights[i])
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat_index
    for ring, p, t, w in ((rings[0], pts[0], pts[0] - pts[1], widths[0]),
                          (rings[-1], pts[-1], pts[-1] - pts[-2], widths[-1])):
        tip = bm.verts.new(p + t.normalized() * w * 0.6)
        for k in range(sides):
            bm.faces.new((ring[k], ring[(k + 1) % sides], tip)).material_index = mat_index


def ellipsoid(bm, centre, radii, segments=16, rings=10, mat_index=0):
    a, b, c = radii
    cx, cy, cz = centre
    top = bm.verts.new((cx, cy, cz + c))
    bot = bm.verts.new((cx, cy, cz - c))
    loops = []
    for i in range(1, rings):
        t = math.pi * i / rings
        loops.append([bm.verts.new((cx + a * math.sin(t) * math.cos(2 * math.pi * k / segments),
                                    cy + b * math.sin(t) * math.sin(2 * math.pi * k / segments),
                                    cz + c * math.cos(t))) for k in range(segments)])
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, loops[0][k], loops[0][j])).material_index = mat_index
        bm.faces.new((bot, loops[-1][j], loops[-1][k])).material_index = mat_index
    for l0, l1 in zip(loops, loops[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((l0[k], l1[k], l1[j], l0[j])).material_index = mat_index


# --- the parts ----------------------------------------------------------------------------------

R_IN = 3.2  # the ring's hole (px): round
R_OUT, N_OUT = 4.0, 3.0  # its outside: a superellipse, squarish like the sprite's corners
RING_TOP, RING_BOT = 0.85, 0.6  # its section's height above / below its rim (px)


def ring(bm):
    """A faired torus: per angle the section runs from R_IN to the superellipse outside, a rounded
    profile (superellipse in radius/height), domed a little more above than below."""
    major, sides = 64, 12
    rings = []
    for i in range(major):
        th = 2 * math.pi * i / major
        c, s = math.cos(th), math.sin(th)
        r_out = R_OUT / (abs(c) ** N_OUT + abs(s) ** N_OUT) ** (1 / N_OUT)
        rc, hw = (R_IN + r_out) / 2, (r_out - R_IN) / 2
        loop = []
        for k in range(sides):
            b = 2 * math.pi * (k + 0.5) / sides
            cb, sb = math.cos(b), math.sin(b)
            rr = rc + hw * math.copysign(abs(cb) ** (2 / 2.6), cb)
            zz = (RING_TOP if sb > 0 else RING_BOT) * math.copysign(abs(sb) ** (2 / 2.6), sb)
            loop.append(bm.verts.new(to_b(CX + rr * c, CY - rr * s, zz)))
        rings.append(loop)
    for i in range(major):
        r0, r1 = rings[i], rings[(i + 1) % major]
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = RING


def vane(bm, corners, top, bottom, mat_index=VANE):
    pts = fillet(corners, 0.3, steps=5)
    outline = ccw([tuple(to_b(x, y)[:2]) for x, y in pts])
    cushion(bm, outline, 0.05 / 12, top / 12, bottom / 12, 0.32 / 12, steps=4, mat_index=mat_index,
            crown=0.3 / 12, keel=0.2 / 12)


def build(bm):
    ring(bm)
    # Upper-right vane: the triangle right of the sprite's "\" edge through (5,5)-(8,8), pushed 0.5 px
    # past it so the edge pixels are covered and the gap pixels (5,6), (6,7) stay open.
    vane(bm, [(8.0, 5.0), (4.5, 5.0), (8.0, 8.5)], 0.95, 0.55)
    # Lower-left vane: the triangle (4,6.5)-(4,9)-(6.5,9).
    vane(bm, [(4.0, 6.5), (4.0, 9.0), (6.5, 9.0)], 0.85, 0.55)
    # The axle across the gap (along the slash), thin from above so pixel (5,7) stays open.
    tube(bm, [to_b(6.55, 6.45, 0.25), to_b(5.95, 7.05, 0.3), to_b(5.0, 8.0, 0.25)],
         [0.13 / 12] * 3, [0.3 / 12] * 3, sides=10, mat_index=DARK)
    # Stubs from the vanes' outer corners into the ring.
    tube(bm, [to_b(7.55, 5.45, 0.2), to_b(8.0, 5.0, 0.2), to_b(8.6, 4.4, 0.2)],
         [0.22 / 12] * 3, [0.32 / 12] * 3, sides=10, mat_index=DARK)
    tube(bm, [to_b(4.45, 8.55, 0.2), to_b(4.0, 9.0, 0.2), to_b(3.4, 9.6, 0.2)],
         [0.22 / 12] * 3, [0.32 / 12] * 3, sides=10, mat_index=DARK)
    # The knob: a glowing dome on the upper vane's corner, pixel (7,5).
    ellipsoid(bm, to_b(7.45, 5.5, 0.85), (0.52 / 12, 0.5 / 12, 0.45 / 12), segments=20, rings=10,
              mat_index=KNOB)


def prongs(bm):
    """Frame 228 only: two short prongs out of the lower vane's legs, over pixels (4,6) and (6,8)."""
    tube(bm, [to_b(4.45, 7.4, 0.15), to_b(4.5, 6.2, 0.15)], [0.36 / 12, 0.3 / 12], [0.3 / 12, 0.25 / 12],
         sides=10, mat_index=VANE)
    tube(bm, [to_b(5.6, 8.55, 0.15), to_b(6.8, 8.5, 0.15)], [0.36 / 12, 0.3 / 12], [0.3 / 12, 0.25 / 12],
         sides=10, mat_index=VANE)


def make_obj(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(50))
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])

    def pal(i, b1, b2, **kw):
        return common.palette_material(sprite, i, f"{NAME}-pulse", frames={f1: b1, f2: b2}, **kw)

    mats = [
        pal(67, 68, 70, metallic=0.45, roughness=0.42, emission_strength=0.2),  # RING: dark red alloy
        pal(66, 67, 69, metallic=0.45, roughness=0.45, emission_strength=0.2),  # VANE: darker red
        pal(65, 66, 67, metallic=0.4, roughness=0.55),  # DARK: stubs and axle
        pal(71, 73, 75, metallic=1.0, roughness=0.85, emission_strength=1.2),  # KNOB: the glow
    ]
    bm = bmesh.new()
    build(bm)
    obj = make_obj(NAME, bm, mats, coll)
    bm = bmesh.new()
    prongs(bm)
    extra = make_obj(f"{NAME}_prongs", bm, mats, coll)
    common.frame_part(extra, [f2])
    shell = common.outline_shell(obj, coll, voxel=0.006, faces=3000)
    common.export_sprite_model(ROOT, [obj, extra, shell], MODEL, sprite["sprites"])
    print("tris", sum(len(p.vertices) - 2 for o in (obj, extra) for p in o.data.polygons))
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(ROOT) / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=1)


if __name__ == "__main__":
    main()
