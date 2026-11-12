"""Atom Bombs sidekick (items 7, 11, 13, 14, 15: Atom Bombs, Buster Rocket, MicroBomb,
8-Way MicroBomb, Post-It Mine; tyrian.shp#8 frames 165, 184, 203). Hard-surface
standard (DECISIONS D50-D53, D65, D74, D120/D122: built as what it is, a small mounted weapon pod).

What the sprite shows (12x14, read row by row, tools/calibration/rubric.md "Reading a sprite"):
- A brass launcher cradle: a horseshoe of side walls (columns 1 and 10, one px wide, index 25)
  round a dark open trough (the ink pixels inside, rows 5-8), the walls' front tips two px wide
  (rows 4-5) curling in to hold the warhead, rounded outer corners at rows 4 and 12.
- A domed breech housing at the back (rows 8-12, index 26) whose front (row 8, six px wide) is
  rounded, with a dark socket collar (row 7, index 19) where the bomb's body goes in.
- The bomb, nose forward along the pod: a 4 px fuse cap (rows 1-2, index 26, lighter polished
  metal), a 6 px bulbous warhead (rows 3-4, index 23), a 4 px body (rows 5-6, index 23) running
  back into the socket. The near-white column down its middle and the dome's bright band are
  sheen on round metal, not geometry.
- Frames 184 and 203: the same bomb block pasted 1 and 2 px further back (recoil after a shot);
  the launcher never changes. One model: the launcher always shows, three copies of the bomb
  (one shared mesh) each tagged for its frame (common.frame_part, D17).

Plan: every top-view edge sits on the INNER edge of the sprite's ink border (D74; the game's ink
outline is the border). Units: sprite px, x = column - 6, y = row (front small), z up; moved to
Blender at the end (X = x/12, Y = (7 - y)/12, Z = z/12).

Texture: AO + roughness bake only (no concept projection; "bake": "model"), outline shells (D51):
one per frame (launcher plus that frame's bomb), tagged for that frame.

Run: blender --background --python assets/blender/sidekicks/atom-bombs.py [-- --renders DIR --no-bake]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip, cbox, hull, TINT)

HERE = Path(__file__).resolve().parent
NAME = "atom-bombs"
SPRITE = "sidekick-atom-bombs"
P = 1 / 12
FRAMES = (165, 184, 203)
RECOIL = {165: 0.0, 184: 1.0, 203: 2.0}  # px the bomb sits back on each frame

# Heights (px).
ZB = -2.0    # belly
ZF = -1.2    # trough floor
ZT = 1.3     # wall tops
ZBOMB = 2.0  # bomb axis

# --- plan curves ---------------------------------------------------------------------------------

Y0, Y1 = 4.05, 12.95  # cradle front face and rear face
RF, RR = 1.6, 2.0     # plan corner radii, front and rear (rows 4 and 12 corners)


def W(y):
    """Outer half width of the cradle: the inner mask's rounded rectangle (x +-5, rows 4-12)."""
    if y < 4.0 + RF:
        d = (4.0 + RF) - y
        return 5 - RF + math.sqrt(max(0.0, RF * RF - d * d))
    if y > 13.0 - RR:
        d = y - (13.0 - RR)
        return 5 - RR + math.sqrt(max(0.0, RR * RR - d * d))
    return 5.0


_C = T.pchip([4.0, 5.2, 6.4, 13.0], [3.0, 3.0, 4.0, 4.0])


def C(y):
    """Trough half width: the tips curl in to 3 px round the warhead (rows 4-5), 4 px behind; never
    thinner walls than 0.9 px (the rounded rear corners)."""
    return min(_C(y), W(y) - 0.9)


def Wf(y):
    return max(W(y), C(y) + 0.9)


# --- mesh helpers ----------------------------------------------------------------------------------

def loft_loops(bm, loops, mats, cap0=True, cap1=True, sharp_caps=True):
    """Join loops (lists of 3D points, same length) into a closed tube; mats[k] = material of loop
    segment k. Caps are n-gons."""
    rings = [[bm.verts.new(p) for p in lp] for lp in loops]
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mats[k]
    if cap0:
        bm.faces.new(rings[0]).material_index = mats[0]
    if cap1:
        bm.faces.new(rings[-1]).material_index = mats[0]
    return rings


def revolve_y(bm, profile, z, n, mats, x=0.0):
    """Revolve an open (y, r) profile round the Y axis at height z; r == 0 ends are poles.
    mats[k] = material between profile points k and k+1."""
    rings = []
    for y, r in profile:
        if r <= 1e-9:
            rings.append([bm.verts.new((x, y, z))])
        else:
            rings.append([bm.verts.new((x + r * math.cos(2 * math.pi * (i + 0.5) / n), y,
                                        z + r * math.sin(2 * math.pi * (i + 0.5) / n))) for i in range(n)])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mats[k]
    if len(rings[0]) > 1:
        bm.faces.new(rings[0]).material_index = mats[0]
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mats[-1]


def revolve_closed_y(bm, profile, z, n, mat, x=0.0):
    """Revolve a closed (y, r) polygon (a ring's cross-section) round the Y axis at height z."""
    rings = [[bm.verts.new((x + r * math.cos(2 * math.pi * (i + 0.5) / n), y,
                            z + r * math.sin(2 * math.pi * (i + 0.5) / n))) for i in range(n)]
             for y, r in profile]
    m = len(rings)
    for k in range(m):
        r0, r1 = rings[k], rings[(k + 1) % m]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat


def cyl_z(bm, x, y, z0, z1, r, n, mat, ch=0.08):
    """A small upright bolt head: a cylinder with a chamfered top."""
    prof = [(r, z0), (r, z1 - ch), (r - ch, z1)]
    rings = [[bm.verts.new((x + rr * math.cos(2 * math.pi * (i + 0.5) / n), y + rr * math.sin(2 * math.pi * (i + 0.5) / n), zz))
              for i in range(n)] for rr, zz in prof]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    bm.faces.new(rings[0]).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


def hull_pts(bm, pts, mat):
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in live if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def finish(name, bm, mats, coll, smooth_angle=32.0):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((P, 0, 0, 0), (0, -P, 0, 7 * P), (0, 0, P, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y reflection flipped them
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


# --- the launcher -------------------------------------------------------------------------------

# Material slots of the launcher.
L_WALL, L_TROUGH, L_DOME, L_SEAM, L_BOLT = range(5)


def cradle_loop(y, i):
    """U section of the cradle at row y, inset i (chamfered ends): belly, outer wall with a panel
    groove, chamfered wall top, inner wall, filleted trough floor. Returns (points, mats)."""
    Wo, Ci = Wf(y) - i, C(y) + i
    t, f, b = ZT - i, ZF - i, ZB + i
    left = [
        (-(Wo - 1.1), b, "o"), (-(Wo - 0.35), b + 0.3, "o"), (-Wo, b + 0.95, "o"),
        (-Wo, -0.35, "o"), (-(Wo - 0.14), -0.24, "o"), (-(Wo - 0.14), -0.02, "o"), (-Wo, 0.09, "o"),
        (-Wo, t - 0.22, "o"), (-(Wo - 0.2), t, "o"),
        (-(Ci + 0.15), t, "o"), (-Ci, t - 0.15, "i"),
        (-Ci, f + 0.25, "i"), (-(Ci - 0.25), f, "i"),
    ]
    right = [(-x, z, tag) for x, z, tag in reversed(left)]
    pts = left + right
    mats = []
    for k in range(len(pts)):
        a, c = pts[k][2], pts[(k + 1) % len(pts)][2]
        mats.append(L_TROUGH if a == "i" and c == "i" else L_WALL)
    return [(x, y, z) for x, z, _ in pts], mats


def build_cradle(bm):
    ys = [Y0 + 0.2, Y0 + 0.45, Y0 + 0.75, 5.1, 5.45, 5.8, 6.15, 6.5, 7.0, 7.6, 8.4, 9.2, 10.0, 10.8,
          11.3, 11.7, 12.05, 12.35, 12.6, Y1 - 0.2]
    loops = [cradle_loop(Y0, 0.18)[0]] + [cradle_loop(y, 0.0)[0] for y in ys] + [cradle_loop(Y1, 0.18)[0]]
    _, mats = cradle_loop(8.0, 0.0)
    loft_loops(bm, loops, mats)


# Breech dome: (y, half width, top z) stations; the front rounded in plan (row 8 six px wide).
DOME = [(7.85, 2.75, 4.25), (8.05, 3.05, 4.55), (8.4, 3.55, 4.85), (8.9, 3.9, 5.05), (9.5, 4.0, 5.15),
        (10.4, 4.0, 5.15), (11.4, 4.0, 5.1), (12.0, 4.0, 5.0), (12.4, 4.0, 4.85), (12.75, 4.0, 4.65), (Y1, 4.0, 4.4)]
DOME_SIDE = 1.75  # the dome's sides run straight up to this z, then the arch


def dome_loop(y, d, h):
    d = min(d, C(y))
    zs = min(DOME_SIDE, h - 0.6)
    pts = [(-d, ZF - 0.1), (-d, zs - 0.12), (-(d - 0.12), zs)]
    k = 9
    a = d - 0.12
    for s in range(1, k):
        t = math.pi / 2 * s / k
        pts.append((-a * math.cos(t), zs + (h - zs) * math.sin(t)))
    pts.append((0.0, h))
    pts += [(-x, z) for x, z in reversed(pts[:-1])]
    return [(x, y, z) for x, z in pts]


def build_dome(bm):
    loops = [dome_loop(y, d, h) for y, d, h in DOME]
    loft_loops(bm, loops, [L_DOME] * len(loops[0]))
    # The seam groove faces in the seam colour: the faces between the two same-y stations.


def build_collar(bm):
    """The socket collar on the dome's front face (row 7, dark): a chamfered ring round the bore."""
    revolve_closed_y(bm, [(7.3, 2.1), (7.3, 2.25), (7.45, 2.45), (8.2, 2.45), (8.2, 2.1)], ZBOMB, 20, L_SEAM)
    # The bore's dark back wall (seen as a thin ring round the bomb body).
    revolve_y(bm, [(7.7, 0.0), (7.7, 2.14), (8.3, 2.14), (8.3, 0.0)], ZBOMB, 20, [L_TROUGH] * 3)


def build_hatch(bm):
    """A small raised loading hatch on the dome's back, two bolts on its front corners."""
    hull_pts(bm, T.cbox(-1.35, 1.35, 10.85, 12.2, 4.3, 5.32, 0.18, 0.12), L_DOME)
    for sx in (-1, 1):
        cyl_z(bm, sx * 0.85, 11.2, 5.1, 5.48, 0.26, 8, L_BOLT, ch=0.07)


def build_breech_cap(bm):
    """The breech's rear cap on the dome's back face: a chamfered disc with a centre bolt (the game
    camera, from the bottom of the screen, sees the pod's rear)."""
    revolve_y(bm, [(12.7, 0.0), (12.7, 1.45), (13.0, 1.45), (13.08, 1.33), (13.08, 0.0)], 1.45, 20, [L_SEAM] * 4)
    revolve_y(bm, [(12.9, 0.0), (12.9, 0.42), (13.16, 0.42), (13.2, 0.34), (13.2, 0.0)], 1.45, 8, [L_BOLT] * 4)


def build_tip_bolts(bm):
    """A bolt on each wall tip (the wide part, rows 4-5)."""
    for sx in (-1, 1):
        cyl_z(bm, sx * 3.95, 4.95, ZT - 0.2, ZT + 0.16, 0.3, 8, L_BOLT, ch=0.08)


def seam_material(obj):
    """Colour the dome's seam-groove faces (the faces whose centre is in the groove) in the seam index."""
    me = obj.data
    for poly in me.polygons:
        if poly.material_index != L_DOME:
            continue
        c = poly.center
        row = 7 - c.y / P
        if 10.24 < row < 10.51 and c.z / P > DOME_SIDE - 0.3:
            poly.material_index = L_SEAM


# --- the bomb -----------------------------------------------------------------------------------

B_CAP, B_BULB, B_GROOVE, B_PIN, B_BAND = range(5)


def bomb_profile():
    """(y, r, material of the segment that starts here) from the nose pin back to the tail, at the
    frame-165 position (fuse face at row 1, the warhead's widest at row 4)."""
    prof = [(1.02, 0.0, B_PIN), (1.02, 0.5, B_PIN), (1.3, 0.5, B_CAP), (1.3, 1.55, B_CAP), (1.62, 1.93, B_CAP),
            (2.62, 1.93, B_CAP), (2.72, 1.62, B_GROOVE), (2.92, 1.62, B_BULB)]
    yc, a, R = 4.1, 1.77, 3.0
    # the bulb: an oblate ellipsoid, a crisp shoulder at the groove, an equator seam groove
    def r_at(y):
        return R * math.sqrt(max(0.0, 1 - ((y - yc) / a) ** 2))
    front = [2.92 + (3.98 - 2.92) * s / 6 for s in range(7)]
    for y in front:
        prof.append((y, r_at(y), B_BULB))
    prof[-1] = (prof[-1][0], prof[-1][1], B_GROOVE)
    prof += [(3.98, 2.84, B_GROOVE), (4.2, 2.84, B_GROOVE), (4.2, r_at(4.2), B_BULB)]
    y_end = yc + a * math.sqrt(1 - (1.9 / R) ** 2)
    back = [4.2 + (y_end - 4.2) * s / 6 for s in range(1, 7)]
    for y in back:
        prof.append((y, r_at(y), B_BULB))
    prof[-1] = (prof[-1][0], 1.9, B_BULB)
    prof += [(6.0, 1.9, B_BAND), (6.0, 2.06, B_BAND), (6.4, 2.06, B_BULB), (6.4, 1.9, B_BULB),
             (10.0, 1.9, B_BULB), (10.4, 1.5, B_BULB), (10.4, 0.0, B_BULB)]
    return prof


def build_bomb(coll, mats):
    bm = bmesh.new()
    prof = bomb_profile()
    revolve_y(bm, [(y, r) for y, r, _ in prof], ZBOMB, 18, [m for _, _, m in prof[:-1]])
    return finish(f"{NAME}-bomb", bm, mats, coll, smooth_angle=34.0)


# --- materials ------------------------------------------------------------------------------------

def make_materials(sprite):
    def pal(i, tag, metallic, roughness):
        return common.palette_material(sprite, i, f"{NAME}-A-{tag}", metallic=metallic, roughness=roughness)
    launcher = [
        pal(25, "wall", 0.17, 0.4),    # cradle walls and belly (sprite columns 1/10: 25)
        pal(16, "trough", 0.1, 0.75),  # the dark trough and inner walls (the sprite's ink there)
        pal(26, "dome", 0.18, 0.36),   # breech dome (rows 8-12: 26)
        pal(19, "seam", 0.15, 0.5),    # socket collar (row 7: 19), dome seam
        pal(22, "bolt", 0.18, 0.4),    # bolts
    ]
    bomb = [
        pal(26, "cap", 0.2, 0.3),      # fuse cap (rows 1-2: 26), polished
        pal(23, "bulb", 0.17, 0.36),   # warhead and body (rows 3-6: 23)
        pal(19, "groove", 0.15, 0.5),  # grooves
        pal(22, "pin", 0.18, 0.4),     # impact pin
        pal(22, "band", 0.18, 0.4),    # body band
    ]
    return launcher, bomb


# --- bake (copied from usp_talon.bake_maps, per object, every material textured) -----------------

def bake_maps(obj, out_dir, tag, size=512, samples=64, hide=()):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    for o in hide:
        o.hide_render = True
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        # distances scaled to this small model (1 px = 0.083)
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.09
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, T.TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    for o in hide:
        o.hide_render = False


# --- build -----------------------------------------------------------------------------------------

def build(sprite, coll):
    lmats, bmats = make_materials(sprite)
    bm = bmesh.new()
    build_cradle(bm)
    build_dome(bm)
    build_collar(bm)
    build_hatch(bm)
    build_tip_bolts(bm)
    build_breech_cap(bm)
    launcher = finish(NAME, bm, lmats, coll)
    bomb = build_bomb(coll, bmats)
    return launcher, bomb, lmats, bmats


def apply_mods(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def frame_bombs(bomb, coll):
    """Three nodes sharing the bomb mesh, each at its frame's recoil and tagged for that frame."""
    out = {}
    for f in FRAMES:
        o = bomb if f == FRAMES[0] else bomb.copy()
        if o is not bomb:
            coll.objects.link(o)
        o.name = f"{NAME}-bomb-{f}"
        o.location = (0.0, -RECOIL[f] * P, 0.0)
        common.frame_part(o, [f])
        out[f] = o
    return out


def shells(launcher, bombs, coll):
    """One outline shell per frame: launcher plus that frame's bomb, remeshed together (D51)."""
    out = {}
    for f, b in bombs.items():
        tmp_me = launcher.data.copy()
        tmp = bpy.data.objects.new(f"tmp-{f}", tmp_me)
        coll.objects.link(tmp)
        bm = bmesh.new()
        bm.from_mesh(tmp_me)
        bm2 = b.data.copy()
        bm2.transform(Matrix.Translation(b.location))
        bm.from_mesh(bm2)
        bm.to_mesh(tmp_me)
        bm.free()
        bpy.data.meshes.remove(bm2)
        s = common.outline_shell(tmp, coll, voxel=0.01, faces=900, smooth=4, inside=0.003)
        s.name = f"{NAME}_outline_{f}"
        common.frame_part(s, [f])
        bpy.data.objects.remove(tmp, do_unlink=True)
        out[f] = s
    return out


# --- measuring and rendering (scratch only) ------------------------------------------------------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if want.split("_")[1] in w]
        scene.render.engine = names[0]


def camera(scene, name, loc, look, ortho=None, lens=80):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_start = 0.01
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def show_only(objs):
    keep = {o.name for o in objs}
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep
            o.hide_viewport = o.name not in keep


def top_mask(objs, out_png, k=10):
    scene = bpy.context.scene
    show_only(objs)
    set_engine(scene, "BLENDER_WORKBENCH")
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_cavity = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 12 * k, 14 * k
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0
    cam = camera(scene, "mask_cam", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)


def region_colours(objs, sprite, frame):
    """The palette index under each sprite pixel centre from straight above, and per region the
    median sprite index (shading extremes trimmed) against the model's."""
    show_only(objs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    fr = next(x for x in sprite["frames"] if x["index"] == frame)
    pix = fr["pixels"]
    got = {}
    for r in range(14):
        for c in range(12):
            X, Y = (c + 0.5 - 6) * P, (7 - (r + 0.5)) * P
            hit, loc, nor, idx, obj, mw = scene.ray_cast(dg, Vector((X, Y, 2.0)), Vector((0, 0, -1)))
            if hit:
                ev = obj.evaluated_get(dg)
                mi = ev.data.polygons[idx].material_index
                name = ev.data.materials[mi].name
                got[(r, c)] = int(name.split("_")[1])
    d = int(RECOIL[frame])
    regions = {
        "fuse cap 26": [(r + d, c) for r in (1, 2) for c in range(4, 8)],
        "warhead 23": [(r + d, c) for r in (3, 4) for c in range(3, 9)],
        "body 23": [(r, c) for r in range(5 + int(d), 7) for c in range(4, 8)] if d < 2 else [(7, c) for c in range(4, 8)],
        "walls 25": [(r, c) for r in range(5, 12) for c in (1, 10)],
        "dome 26": [(r, c) for r in range(9, 12) for c in range(2, 10)],
        "socket 19": [(7, c) for c in range(4, 8)] if d == 0 else [],
        "trough (ink)": [(r, c) for r, c in ((6, 3), (7, 2), (7, 3), (6, 8), (6, 9), (7, 8), (7, 9))] if d == 0 else [],
    }
    import statistics as st
    out = {}
    for name, cells in regions.items():
        if not cells:
            continue
        sv = sorted(pix[r][c] for r, c in cells if pix[r][c] > 1)
        mv = sorted(got.get((r, c), -1) for r, c in cells)
        k = len(sv) // 6
        sv_t = sv[k:len(sv) - k] if len(sv) > 5 else sv
        out[name] = {"sprite": st.median(sv_t) if sv_t else 1, "model": st.median(mv)}
    grid = ["".join(f"{got.get((r, c), -1):>3}" for c in range(12)) for r in range(14)]
    return out, grid


def setup_eevee(scene, res):
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filter_size = 1.2
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 0.9
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    for name, rot, e in (("key", (math.radians(40), math.radians(-25), math.radians(20)), 3.2),
                         ("fill", (math.radians(65), math.radians(40), math.radians(200)), 1.0)):
        if bpy.data.objects.get(name):
            continue
        L = bpy.data.lights.new(name, "SUN")
        L.energy = e
        L.angle = math.radians(8)
        o = bpy.data.objects.new(name, L)
        o.rotation_euler = rot
        scene.collection.objects.link(o)


def render_views(launcher, bombs, out_dir):
    scene = bpy.context.scene
    setup_eevee(scene, (420, 420))
    D = 3.2
    tilt = math.radians(15)
    views = {
        "top": ((0, 0, 4), (0, 0, 0), 1.35),
        "game": ((0, -D * math.sin(tilt), D * math.cos(tilt)), (0, 0, 0), None),
        "side": ((D, 0, 0.05), (0, 0, 0.05), 1.35),
        "front": ((0, D, 0.05), (0, 0, 0.05), 1.35),
        "rear": ((0, -D, 0.05), (0, 0, 0.05), 1.35),
        "q34": ((D * 0.62, -D * 0.6, D * 0.55), (0, 0, 0.05), None),
        "q34f": ((-D * 0.62, D * 0.62, D * 0.5), (0, 0, 0.05), None),
        "under": ((D * 0.4, -D * 0.5, -D * 0.75), (0, 0, 0), None),
    }
    per_frame = {"top", "game"}
    for v, (loc, look, ortho) in views.items():
        cam = camera(scene, f"cam_{v}", loc, look, ortho=ortho, lens=95)
        if v == "top":
            cam.rotation_euler = (0, 0, 0)
        scene.camera = cam
        for f in (FRAMES if v in per_frame else FRAMES[:1]):
            show_only([launcher, bombs[f]])
            scene.render.filepath = str(out_dir / f"{f}_{v}.png")
            bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="atom_bombs_")) / "atom-bombs.glb"
    renders = Path(argv[argv.index("--renders") + 1]) if "--renders" in argv else None
    sprite = common.load_sprite(WT, SPRITE)
    coll = common.reset_collection(NAME)
    launcher, bomb, lmats, bmats = build(sprite, coll)
    apply_mods(launcher)
    apply_mods(bomb)
    bombs = frame_bombs(bomb, coll)
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (launcher, bomb)}
    print("atom-bombs A: triangles", tris)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        others = [bombs[f] for f in FRAMES[1:]]
        bake_maps(launcher, bake_dir, "atom_bombs_launcher", size=512, hide=list(bombs.values()))
        bake_maps(bomb, bake_dir, "atom_bombs_bomb", size=256, hide=others)
        fmt = "WEBP"
    sh = shells(launcher, bombs, coll)
    objs = [launcher, *bombs.values(), *sh.values()]
    common.export_sprite_model(WT, objs, f"sidekicks/{NAME}", sprite["sprites"], image_format=fmt)
    if renders:
        renders.mkdir(parents=True, exist_ok=True)
        report = {"triangles": tris, "shell_faces": {f: len(s.data.polygons) for f, s in sh.items()},
                  "colours": {}, "grid": {}}
        for f in FRAMES:
            top_mask([launcher, bombs[f]], renders / f"mask_{f}.png")
            report["colours"][f], report["grid"][f] = region_colours([launcher, bombs[f]], sprite, f)
        render_views(launcher, bombs, renders)
        (renders / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
