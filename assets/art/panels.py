"""Building blocks for the pictures that are screen furniture (the in-game frame, the item screen,
Destruct's status bars): worn bronze panels seen straight on, with bevelled bezels round dark
glass, ribbed pipes, greebles and glowing green labels.

Layouts are given in the original picture's pixels (320x200, y down) so they can be measured off
reference/pictures/pic-NN.png; px() turns them into Blender units under an orthographic camera
that frames exactly the 320x200 screen.
"""

import math
import random

import common as c

bpy = c.bpy
U = 0.1  # Blender units per original pixel: the screen is 32 x 20 units


def px(x, y, z=0.0):
    """An original-picture pixel position (x right, y down) to Blender (x right, y up, z out)."""
    return (x * U - 16.0, 10.0 - y * U, z)


def screen_camera():
    """Orthographic, straight down onto the 32x20-unit screen."""
    return c.camera((0, 0, 50), (0, 0, 0), ortho_scale=32.0)


def bronze(name="bronze", color=(176, 150, 112), grime=(48, 38, 28), roughness=0.4):
    """Worn bronze: metallic, its colour mottled by noise and darkened in creases (AO)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = 0.55
    bsdf.inputs["Roughness"].default_value = roughness
    tc = c.node(nt, "ShaderNodeTexCoord")
    mottle = c.node(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=10.0, Roughness=0.65)
    c.link(nt, tc.outputs["Object"], mottle.inputs["Vector"])
    base = c.ramp(nt, [(0.3, tuple(v * 0.75 for v in c.srgb(*color))), (0.7, c.srgb(*color))])
    c.link(nt, mottle.outputs["Fac"], base.inputs["Fac"])
    ao = c.node(nt, "ShaderNodeAmbientOcclusion", Distance=0.4)
    dirt = c.node(nt, "ShaderNodeMix", p_data_type="RGBA")
    c.link(nt, ao.outputs["AO"], dirt.inputs[0])
    dirt.inputs[6].default_value = (*c.srgb(*grime), 1)
    c.link(nt, base.outputs["Color"], dirt.inputs[7])
    c.link(nt, dirt.outputs[2], bsdf.inputs["Base Color"])
    pits = c.node(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=4.0)
    c.link(nt, tc.outputs["Object"], pits.inputs["Vector"])
    bump = c.node(nt, "ShaderNodeBump", Strength=0.12, Distance=0.02)
    c.link(nt, pits.outputs["Fac"], bump.inputs["Height"])
    c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])
    return mat


def glass(name="glass", color=(4, 6, 4)):
    """The dark glass of a readout: nearly black, with a faint reflection."""
    return c.material(name, c.srgb(*color), metallic=0.0, roughness=0.12)


def box(name, x0, y0, x1, y1, z0, z1, mat, bevel=0.06, segments=2):
    """A bevelled box over the pixel rectangle (x0, y0)-(x1, y1), from height z0 to z1."""
    a, b = px(x0, y0), px(x1, y1)
    o = c.primitive("cube", name, mat, size=1.0)
    o.scale = (abs(b[0] - a[0]), abs(b[1] - a[1]), z1 - z0)
    o.location = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (z0 + z1) / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = segments
        m.limit_method = "ANGLE"
    return o


def bezel(name, x0, y0, x1, y1, mat, glass_mat, rim=2.0, z=0.6, height=0.35):
    """A readout: dark glass sunk in a raised bevelled rim `rim` pixels wide."""
    box(f"{name}_glass", x0, y0, x1, y1, z - 0.2, z + 0.02, glass_mat, bevel=0)
    for i, (a, b, cc, d) in enumerate([(x0 - rim, y0 - rim, x1 + rim, y0), (x0 - rim, y1, x1 + rim, y1 + rim),
                                       (x0 - rim, y0, x0, y1), (x1, y0, x1 + rim, y1)]):
        box(f"{name}_rim{i}", a, b, cc, d, z - 0.1, z + height, mat, bevel=0.07, segments=3)


def pipe(name, points, radius, mat, z=0.7, ribs=0):
    """A pipe through pixel points at height z, optionally ribbed (`ribs` bulges per unit)."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    pts = [px(x, y, z) for x, y in points]
    if ribs:
        dense = []
        for (ax, ay, az), (bx, by, bz) in zip(pts, pts[1:]):
            n = max(2, int(math.dist((ax, ay), (bx, by)) * ribs * 2))
            dense += [(ax + (bx - ax) * t / n, ay + (by - ay) * t / n, az) for t in range(n)]
        pts = dense + [pts[-1]]
    spline.points.add(len(pts) - 1)
    for i, (p, sp) in enumerate(zip(pts, spline.points)):
        sp.co = (*p, 1)
        if ribs:
            sp.radius = 1.0 if i % 2 == 0 else 0.72
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def label(name, text, x, y, size, mat, z=0.65, vertical=False):
    """Glowing text with its top-left at pixel (x, y), `size` pixels tall; vertical stacks the
    letters one under another, as the original's SHIELD and ARMOR."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = "\n".join(text) if vertical else text
    curve.size = size * U * 1.3
    curve.space_line = 0.78 if vertical else 1.0
    curve.align_x = "CENTER" if vertical else "LEFT"
    curve.extrude = 0.01
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = px(x, y + size, z)
    curve.materials.append(mat)
    return obj


def greebles(name, x0, y0, x1, y1, mat, count, z=0.6, size=(2, 6), seed=1):
    """Small machined blocks and studs scattered over a pixel rectangle."""
    rnd = random.Random(seed)
    for i in range(count):
        w, h = rnd.uniform(*size), rnd.uniform(*size)
        x, y = rnd.uniform(x0, x1 - w), rnd.uniform(y0, y1 - h)
        if rnd.random() < 0.3:
            s = c.primitive("cylinder", f"{name}{i}", mat, vertices=16, radius=min(w, h) * U / 2, depth=0.2)
            s.location = px(x + w / 2, y + h / 2, z + 0.1)
        else:
            box(f"{name}{i}", x, y, x + w, y + h, z - 0.1, z + rnd.uniform(0.08, 0.25), mat, bevel=0.03)


def rivets(name, points, mat, radius=0.9, z=0.62):
    """Domed rivets at pixel points."""
    for i, (x, y) in enumerate(points):
        r = c.primitive("uv_sphere", f"{name}{i}", mat, segments=16, ring_count=8, radius=radius * U)
        r.scale = (1, 1, 0.5)
        r.location = px(x, y, z)
        c.smooth(r)


def lamp(name, x0, y0, x1, y1, color=(255, 50, 10), strength=1.4, z=0.7):
    """A small glowing lamp in a bronze cup (the red lights at the top of the HUD)."""
    lens = c.primitive("uv_sphere", f"{name}_lens", c.emission(f"{name}_glow", c.srgb(*color), strength),
                       segments=24, ring_count=12, radius=1.0)
    a, b = px(x0, y0), px(x1, y1)
    lens.scale = (abs(b[0] - a[0]) / 2, abs(b[1] - a[1]) / 2, 0.15)
    lens.location = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z)
    return lens


def key_lights():
    """Light for straight-on panels: a broad key from the top left, a cool fill from the right."""
    c.light("AREA", (-14, 12, 22), (0, 0, 0), energy=6000, color=c.srgb(255, 240, 220), size=18)
    c.light("AREA", (18, -10, 14), (0, 0, 0), energy=1500, color=c.srgb(190, 205, 255), size=14)
    # A warm room for the metal to reflect (the film can still be transparent).
    c.world_color(c.srgb(150, 135, 115), 0.8)
