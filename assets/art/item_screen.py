"""Picture 1: the item screen, where the shop and the level map are (JE_itemScreen, game_menu.c:
JE_loadPic 1).

On the left, an ornate bronze frame round the window where the ship is shown: ribbed pipes up
its sides, a pod either side at mid height, and under the window the helmet and shield icons
each beside a gauge, with a slot under them. On the right, a large dark panel with a title strip
over the menu area; along the bottom, the help-text bar. Writes public/art/item_screen.webp.
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
import panels as p  # noqa: E402

NAME = "item_screen"

c.new_scene(samples=128)

metal = p.bronze()
dark = p.bronze("dark_bronze", color=(96, 78, 58), roughness=0.45)
panel = p.bronze("panel", color=(92, 66, 40), grime=(30, 20, 12), roughness=0.55)
inset = c.material("inset", c.srgb(62, 42, 24), metallic=0.2, roughness=0.6)
window = c.material("window", c.srgb(34, 20, 10), roughness=0.5)
glass = p.glass("glass", (8, 6, 4))

# The backing: the whole screen.
p.box("backing", 0, 0, 320, 200, -0.3, 0.0, dark, bevel=0)

# ---- The frame round the ship window -------------------------------------------------------
p.box("frame", 1, 1, 155, 182, 0.0, 0.55, metal, bevel=0.15, segments=3)
p.box("window", 20, 17, 135, 147, 0.5, 0.58, window, bevel=0)
# Its rim: thick rounded bars, the top corners cut off.
for i, (a, b, cc, d) in enumerate([(26, 12, 129, 17), (15, 22, 20, 147), (135, 22, 140, 147), (15, 147, 140, 151)]):
    p.box(f"rim{i}", a, b, cc, d, 0.5, 1.05, metal, bevel=0.2, segments=4)
for i, (x0, x1) in enumerate([(15, 26), (129, 140)]):
    p.box(f"corner{i}", x0, 12, x1, 22, 0.5, 1.05, metal, bevel=0.2, segments=4)
# Ribbed pipes up both sides and across the top, joined by elbows in the top corners.
p.pipe("pipe_l", [(8, 16), (8, 178)], 0.3, dark, ribs=4)
p.pipe("pipe_r", [(147, 16), (147, 178)], 0.3, dark, ribs=4)
p.pipe("pipe_top", [(18, 6), (137, 6)], 0.25, dark, ribs=4)
for i, (cx, s_) in enumerate(((18, -1), (137, 1))):
    arc = [(cx + s_ * 10 * math.sin(t), 16 - 10 * math.cos(t)) for t in [k * math.pi / 24 for k in range(13)]]
    p.pipe(f"elbow{i}", arc, 0.3, metal, z=0.72)
# The pods either side at mid height.
for i, (x0, x1) in enumerate([(2, 28), (127, 153)]):
    p.box(f"pod{i}", x0 - 1, 77, x1 + 1, 113, 0.4, 1.1, metal, bevel=0.25, segments=4)
    p.box(f"pod{i}_mouth", x0 + 2, 82, x1 - 2, 108, 1.0, 1.12, glass, bevel=0.05)
# Greebles where the original is busiest.
p.greebles("g_l", 2, 30, 14, 76, dark, 10, z=0.6, seed=21)
p.greebles("g_r", 141, 30, 154, 76, dark, 10, z=0.6, seed=22)
p.greebles("g_l2", 2, 115, 14, 145, dark, 8, z=0.6, seed=23)
p.greebles("g_r2", 141, 115, 154, 145, dark, 8, z=0.6, seed=24)

# ---- Under the window: helmet and shield, each by its gauge --------------------------------
helmet_mat = c.material("helmet", c.srgb(200, 110, 40), metallic=0.8, roughness=0.3)
visor = c.material("visor", c.srgb(20, 8, 4), roughness=0.2)
shield_mat = c.material("shield", c.srgb(210, 90, 30), metallic=0.8, roughness=0.3)
for i, (x0, x1) in enumerate([(16, 34), (78, 97)]):
    p.box(f"icon_cup{i}", x0, 151, x1, 168, 0.4, 0.9, dark, bevel=0.15, segments=3)
helmet = c.primitive("uv_sphere", "helmet", helmet_mat, segments=32, ring_count=16, radius=0.62)
helmet.location = p.px(25, 159.5, 0.95)
helmet.scale = (0.85, 1.0, 0.6)
c.smooth(helmet)
p.box("helmet_visor", 21.5, 157.5, 28.5, 159.5, 1.15, 1.3, visor, bevel=0.03)
p.box("helmet_nose", 24.4, 159.5, 25.6, 164, 1.15, 1.3, visor, bevel=0.03)
# The shield: a heater-shaped slab, flat top, pointed foot.
bm = bmesh.new()
outline = [(-0.6, 0.6), (0.6, 0.6), (0.6, 0.05), (0.0, -0.75), (-0.6, 0.05)]
face = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in outline])
ext = bmesh.ops.extrude_face_region(bm, geom=[face])
for v in [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.z += 0.3
mesh = c.bpy.data.meshes.new("shield")
bm.to_mesh(mesh)
bm.free()
shield = c.mesh_object("shield", mesh, shield_mat, location=p.px(87.5, 159.5, 0.85))
bev = shield.modifiers.new("bevel", "BEVEL")
bev.width = 0.08
bev.segments = 3
for i, (x0, x1) in enumerate([(40, 74), (102, 137)]):
    p.bezel(f"gauge{i}", x0, 153, x1, 166, metal, glass, rim=1.5)
    for k in range(int(x0) + 2, int(x1) - 1, 3):
        p.box(f"gauge{i}_tick{k}", k, 156, k + 1, 163, 0.55, 0.66, dark, bevel=0.02)
p.bezel("slot", 47, 171, 110, 180, metal, glass, rim=1.5)

# ---- The panel on the right ----------------------------------------------------------------
p.box("panel", 155, 2, 318, 182, 0.0, 0.4, panel, bevel=0.12, segments=3)
p.box("title", 158, 5, 315, 31, 0.3, 0.45, inset, bevel=0.06)
p.box("menu", 158, 35, 315, 179, 0.3, 0.45, inset, bevel=0.06)

# ---- The help bar along the bottom ---------------------------------------------------------
p.box("bar", 1, 183, 319, 199, 0.0, 0.5, metal, bevel=0.15, segments=3)
p.box("bar_slot", 4, 185.5, 316, 197, 0.4, 0.55, inset, bevel=0.06)

p.key_lights()
p.screen_camera()
c.save(NAME)
