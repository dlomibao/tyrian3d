"""assembly-newsha-121 (newsha.shp 83 | 85 / 121 | 123): the tan concrete ball-turret bunker.

WHAT IT IS: a cast-concrete casemate standing on the ground (3.3 GAUNTLET, 3.12 MACES: custom49 ground
spawns, terrain-fixed, no motion of its own). 48 x 56 px, four 24 x 28 pieces. Read from the sprite:
- a flat tan deck (pal 26) with battered (sloped) walls: west and east walls 3-4 px wide in plan (pal 24),
  the north wall 1.5 px (pal 25); the top corners are cut at 45 degrees;
- the light line along the deck's north and west edges (rows 15, col 13) is the sun on the deck's
  chamfered edge (sheen), not paint: the edge is a modelled chamfer in the deck's own colour;
- the darker brown band at the bottom (rows 41-51, pal 20) is the casemate's front glacis, a two-tier
  stepped slope facing the player; its lighter rows 41 and 48 are the lit noses of the deck edge and of
  the step;
- a dark drainage / cable trench (pal 18) runs from the turret well down the glacis and out through the
  toe (the sprite's 3 px notch at the bottom);
- deck panel joints at rows 20 and 34 (the sprite's dark/light line pairs) run across the deck and down
  the side walls (formwork joints);
- the turret: a dark steel ball (pal 5, polished: the white spot is the sun's glint) sitting in a round
  steel-lined well (liner pal 6, its lit far wall is the grey crescent at the lower right); a short gun
  port faces the player.
The underside is a flat closed base.

Units while building: sprite px of the assembly grid (x = column, y = row, z up, pixel edges);
Blender X = (x - 24) / 12, Y = (28 - y) / 12, Z = z / 12 (assembly centre = screen (140, 24)).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsha-121.py
Exports the four pieces (enemies/newsha-83, -85, -121, -123: model + outline shell each) cut from the
whole bunker with common.split_assembly.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "assembly-newsha-121"
TAG = "nsha121"
LAYOUT = [("newsha-83", 128, 10), ("newsha-85", 152, 10), ("newsha-121", 128, 38), ("newsha-123", 152, 38)]
CX0, CY0 = 140, 24
W, H = 48, 56
U = 1 / 12

# --- dimensions (px) --------------------------------------------------------------------------------
FOOT = [(13, 14), (36, 14), (39, 17), (39, 52), (10, 52), (10, 17)]  # inner-mask footprint (pixel edges)
PLINTH = 0.6  # vertical plinth under the battered walls
HD = 5.0  # deck height
XL, XR, YT = 13.4, 35.6, 15.6  # deck edges (west, east, north)
YF = 41.2  # deck front edge (top of the glacis)
CH = 0.45  # deck edge chamfer
Y_STEP, Z_STEP_HI, Z_STEP_LO = 47.4, 3.0, 2.35  # glacis step: nose height, foot height
TOE = 0.9  # glacis toe height at the front edge
GX0, GX1 = 22.4, 25.0  # trench (cols 22-24; its outlet the sprite's bottom notch)
G_DEPTH = 1.0
G_Y0 = 34.2  # trench start (inside the well's rim)
WELL_C, WELL_R = (24.5, 26.8), 7.9  # turret well (outer edge of the steel liner)
LINER_IN = 7.05
BALL_C, BALL_R, BALL_Z = (24.1, 26.2), 6.35, HD - 1.1
PORT_EL = math.radians(12)  # gun port: elevation of its axis
JOINTS = [20.3, 33.9]
DOOR_X0, DOOR_X1, DOOR_H = 20.9, 24.1, 3.4  # rear doorway recess  # deck / wall panel joints (rows)

PALS = {
    "deck": 26, "wall": 24, "north": 25, "lip": 26, "glacis": 20, "nose": 22, "trench": 18,
    "joint": 23, "liner": 6, "rim": 7, "well": 3, "ball": 5, "port": 4, "bore": 2, "base": 20,
}


def V(x, y, z):
    return Vector(((x - W / 2) * U, (H / 2 - y) * U, z * U))


def merged_sprite():
    data = common.load_sprite(WT, "newsha-83")
    for name, _, _ in LAYOUT:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


# --- mesh helpers -------------------------------------------------------------------------------------

def hull_obj(name, pts, mat, coll, mats):
    """A closed convex solid from px points; every face gets material slot `mat`."""
    bm = bmesh.new()
    verts = [bm.verts.new(V(*p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.material_index = mat
    return bm_obj(name, bm, coll, mats)


def bm_obj(name, bm, coll, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def boolean(obj, cutter, op="DIFFERENCE"):
    mod = obj.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    apply_mods(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()


def apply_mods(obj):
    """Apply obj's modifiers (common._apply_modifiers, after a view-layer sync: removed cutters leave
    dead entries until then)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)


def lathe(name, profile, centre, coll, mats, mat_of, segs=48, smooth=True):
    """Revolve a closed (r, z) profile (px) round a vertical axis at centre (px); mat_of(k) gives the
    slot of profile edge k (point k -> k + 1)."""
    bm = bmesh.new()
    cx, cy = centre
    n = len(profile)
    rings = []
    for s in range(segs):
        a = 2 * math.pi * s / segs
        rings.append([bm.verts.new(V(cx + r * math.cos(a), cy + r * math.sin(a), z)) for r, z in profile])
    for s in range(segs):
        A, B = rings[s], rings[(s + 1) % segs]
        for k in range(n):
            k1 = (k + 1) % n
            f = bm.faces.new([A[k], B[k], B[k1], A[k1]])
            f.material_index = mat_of(k)
            f.smooth = smooth
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_obj(name, bm, coll, mats)


def sphere(name, c, z, r, coll, mats, mat, segs=48, rings=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r * U)
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=V(c[0], c[1], z))
    for f in bm.faces:
        f.material_index = mat
        f.smooth = True
    return bm_obj(name, bm, coll, mats)


def tube(name, a, b, r, coll, mats, mat_side, mat_cap0, mat_cap1, segs=20, ch=0.0):
    """A closed cylinder from px point a to b (3D px), radius r, optional chamfer ch on the b end."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    u = d.cross(Vector((0, 0, 1)))
    if u.length < 1e-6:
        u = Vector((1, 0, 0))
    u.normalize()
    v = d.cross(u)
    bm = bmesh.new()

    def ring(p, rr):
        return [bm.verts.new(V(*(p + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * rr)))
                for k in range(segs)]
    rs = [ring(a, r)]
    if ch > 0:
        rs.append(ring(b - d * ch, r))
        rs.append(ring(b, r - ch))
    else:
        rs.append(ring(b, r))
    for i in range(len(rs) - 1):
        for k in range(segs):
            k1 = (k + 1) % segs
            f = bm.faces.new([rs[i][k], rs[i][k1], rs[i + 1][k1], rs[i + 1][k]])
            f.material_index = mat_side
            f.smooth = True
    bm.faces.new(list(reversed(rs[0]))).material_index = mat_cap0
    bm.faces.new(rs[-1]).material_index = mat_cap1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_obj(name, bm, coll, mats)


# --- the bunker --------------------------------------------------------------------------------------

def wall_x(z, side):
    """x of the battered west (side -1) / east (+1) wall at height z."""
    t = min(max((z - PLINTH) / (HD - CH - PLINTH), 0.0), 1.0)
    return (10 + (XL - 10) * t) if side < 0 else (39 + (XR - 39) * t)


def deck_ring(z, inset):
    """The deck-top outline (chamfered north corners) at height z, grown by -inset."""
    xl, xr, yt = XL + inset, XR - inset, YT + inset
    c = 1.6
    return [(xl + c, yt), (xr - c, yt), (xr, yt + c), (xr, YF), (xl, YF), (xl, yt + c)]


def build_block(coll, mats, S):
    """Body: plinth + battered walls + deck (chamfered edge) + the glacis as two stepped tiers."""
    pts = []
    for x, y in FOOT:
        pts += [(x, y, 0.0), (x, y, PLINTH)]
    for x, y in deck_ring(0, 0):
        pts.append((x, y, HD - CH))
    for x, y in deck_ring(0, CH):
        pts.append((x, y, HD))
    # the body ends at the deck front edge; the glacis tiers make the front
    body = hull_obj("body", [p for p in pts if p[1] <= YF] + [(x, YF, z) for x, z in
                    ((wall_x(0, -1), 0), (wall_x(0, 1), 0), (10, PLINTH), (39, PLINTH),
                     (XL, HD - CH), (XR, HD - CH), (XL + CH, HD), (XR - CH, HD))], S["deck"], coll, mats)
    # upper glacis tier: deck front edge (chamfered nose) down to the step nose
    def tier(y0, z0, y1, z1, nose_ch):
        p = []
        for y, z, chm in ((y0, z0, nose_ch), (y1, z1, nose_ch)):
            for side in (-1, 1):
                p += [(10 if side < 0 else 39, y, 0.0), (10 if side < 0 else 39, y, PLINTH),
                      (wall_x(z - chm, side), y, z - chm), (wall_x(z - chm, side) - side * chm * 0.8, y, z)]
        return p
    up = tier(YF - 0.01, HD, Y_STEP, Z_STEP_HI, 0.3)
    # the nose of the step: drop the last section's top by a small chamfer at y = Y_STEP
    upper = hull_obj("glacis_hi", up, S["glacis"], coll, mats)
    lo = tier(Y_STEP - 0.01, Z_STEP_LO, 52.0, TOE, 0.25)
    lower = hull_obj("glacis_lo", lo, S["glacis"], coll, mats)
    return body, upper, lower


def colour_by_normal(obj, S):
    """Faces of the block by orientation: deck top, battered walls, north wall, glacis, chamfers."""
    me = obj.data
    for p in me.polygons:
        n = p.normal
        c = p.center
        y_px = H / 2 - c.y / U
        z_px = c.z / U
        if n.z < -0.5:
            p.material_index = S["base"]
        elif n.z > 0.97:
            if y_px > YF + 0.3:
                p.material_index = S["glacis"]
            elif z_px > HD - 0.05:
                p.material_index = S["deck"]
        elif y_px > YF - 0.05 and n.z > -0.5:  # glacis slopes, its battered flanks, the step risers
            p.material_index = S["nose"] if (abs(n.z) < 0.05 and n.y < -0.9 and z_px > 1.2) else S["glacis"]
        elif abs(n.z) < 0.05 and n.y < -0.9:  # step risers / toe face (south)
            p.material_index = S["nose"] if z_px > 1.0 else S["glacis"]
        elif z_px >= HD - CH - 0.05 and n.z > 0.2:  # deck chamfer
            p.material_index = S["lip"]
        elif n.y > 0.3 and abs(n.x) < 0.75:  # north wall (and NE/NW corner faces)
            p.material_index = S["north"]
        else:
            p.material_index = S["wall"]


def build(sprite):
    coll = common.reset_collection(NAME)
    order = ["deck", "wall", "north", "lip", "glacis", "nose", "trench", "joint", "liner", "rim",
             "well", "ball", "port", "bore", "base"]
    S = {k: i for i, k in enumerate(order)}
    mats = []
    seen = {}
    for k in order:
        p = PALS[k]
        if k in ("ball",):
            m = common.palette_material(sprite, p, TAG + "_ball", metallic=0.3, roughness=0.24)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 1.0
        elif k in ("liner", "rim", "port"):
            m = common.palette_material(sprite, p, TAG + "_" + k, metallic=0.45, roughness=0.42)
        elif k in ("bore", "well"):
            m = common.palette_material(sprite, p, TAG + "_" + k, metallic=0.3, roughness=0.7)
        else:  # one material per slot: duplicate slots get merged (and faces renumbered wrongly) on join
            m = common.palette_material(sprite, p, TAG + "_" + k, metallic=0.0, roughness=0.85)
        mats.append(m)

    body, upper, lower = build_block(coll, mats, S)
    boolean(body, upper, "UNION")
    boolean(body, lower, "UNION")
    colour_by_normal(body, S)

    # trench: from inside the well rim down the deck and the glacis, out through the toe
    deck_cut = hull_obj("cut_trench_deck", [(x, y, z) for x in (GX0, GX1) for y in (G_Y0, YF + 0.6)
                                            for z in (HD - G_DEPTH, 20)], S["trench"], coll, mats)
    gl_pts = []
    for x in (GX0, GX1):
        for y, z in ((YF - 0.4, HD - G_DEPTH), (Y_STEP, Z_STEP_LO - G_DEPTH + 0.15), (53.0, TOE - G_DEPTH * 0.6)):
            gl_pts += [(x, y, z), (x, y, 20)]
    gl_cut = hull_obj("cut_trench_glacis", gl_pts, S["trench"], coll, mats)
    outlet = hull_obj("cut_outlet", [(x, y, z) for x in (GX0 + 0.5, GX1 + 0.3) for y in (51.15, 53.0) for z in (-1, 20)],
                      S["trench"], coll, mats)
    # panel joints across the deck and down the side walls
    joints = []
    for i, r in enumerate(JOINTS):
        joints.append(hull_obj(f"cut_joint{i}", [(x, y, z) for x in (8, 41) for y in (r - 0.2, r + 0.2)
                                                 for z in (HD - 0.35, 20)], S["joint"], coll, mats))
        # down the walls: a wedge following the batter, 0.3 deep
        for side in (-1, 1):
            xa = 9.0 if side < 0 else 40.0
            pts = []
            for y in (r - 0.2, r + 0.2):
                pts += [(xa, y, PLINTH + 0.1), (xa, y, HD + 1),
                        (wall_x(PLINTH + 0.1, side) - side * 0.3, y, PLINTH + 0.1),
                        (wall_x(HD - CH, side) - side * 0.3, y, HD - CH), (xa, y, HD - CH)]
            joints.append(hull_obj(f"cut_jw{i}{side}", pts, S["joint"], coll, mats))
    well_cut = lathe("cut_well", [(0.0, HD - 3.2), (WELL_R, HD - 3.2), (WELL_R, 20), (0.0, 20)], WELL_C, coll, mats,
                     lambda k: S["well"], segs=48, smooth=False)

    def tag_new(cut, slot):
        # faces the cutter leaves get the cutter's material through the boolean (EXACT keeps materials)
        for p in cut.data.polygons:
            p.material_index = slot

    tag_new(deck_cut, S["trench"])
    tag_new(gl_cut, S["trench"])
    tag_new(outlet, S["trench"])
    for j in joints:
        tag_new(j, S["joint"])
    tag_new(well_cut, S["well"])
    # rear doorway: a recess in the north wall (the sprite's 3 px notch at the top, cols 21-23)
    door_cut = hull_obj("cut_door", [(x, y, z) for x in (DOOR_X0, DOOR_X1) for y in (10, 15.2) for z in (-1, DOOR_H)],
                        S["port"], coll, mats)
    for c in [deck_cut, gl_cut, outlet] + joints + [well_cut, door_cut]:
        boolean(body, c)

    # steel liner + rim collar in the well
    liner = lathe("liner", [(LINER_IN, HD - 3.3), (WELL_R - 0.02, HD - 3.3), (WELL_R - 0.02, HD + 0.05),
                            (WELL_R - 0.35, HD + 0.4), (LINER_IN + 0.3, HD + 0.4), (LINER_IN, HD + 0.1)],
                  WELL_C, coll, mats, lambda k: S["rim"] if k in (2, 3, 4) else S["liner"], segs=64)
    # bearing ring: the ball's seat, low in the well
    seat = lathe("seat", [(BALL_R - 1.4, HD - 3.25), (LINER_IN + 0.01, HD - 3.25), (LINER_IN + 0.01, HD - 2.0),
                          (BALL_R - 0.5, HD - 1.6)], WELL_C, coll, mats, lambda k: S["liner"], segs=48)
    ball = sphere("ball", BALL_C, BALL_Z, BALL_R, coll, mats, S["ball"])
    clip = hull_obj("cut_ball", [(x, y, z) for x in (0, 48) for y in (0, 56) for z in (-5, HD - 3.0)], S["ball"], coll, mats)
    boolean(ball, clip)
    # gun port: a short barrel stub facing the player (south = +row), elevated
    d = Vector((0, math.cos(PORT_EL), math.sin(PORT_EL)))
    c0 = Vector((BALL_C[0], BALL_C[1], BALL_Z))
    port = tube("port", c0 + d * (BALL_R - 0.8), c0 + d * (BALL_R + 0.9), 1.15, coll, mats,
                S["port"], S["port"], S["port"], segs=24, ch=0.3)
    bore = tube("bore", c0 + d * (BALL_R + 0.3), c0 + d * (BALL_R + 0.93), 0.55, coll, mats,
                S["bore"], S["bore"], S["bore"], segs=16)
    door = hull_obj("door", [(x, y, z) for x in (DOOR_X0 + 0.05, DOOR_X1 - 0.05) for y in (14.9, 15.6)
                             for z in (0.0, DOOR_H - 0.05)], S["port"], coll, mats)
    parts = [body, liner, seat, ball, port, bore, door]
    return coll, mats, S, parts


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def sink_shell(shell, model, margin, reach):
    """newshv-10.py's sink_shell (D185): every shell vertex dropped to `margin` under the lowest top
    surface within `reach`, so the ink stays on the silhouette (no back faces over the deck)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = merged_sprite()
    coll, mats, S, parts = build(sprite)
    obj = join(parts, NAME)
    # outline shell from a sealed pre-cull copy (D90/D118): the joined solids, before hidden faces go
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, smooth=4, inside=0.004)
    sink_shell(shell, sealed, margin=0.02, reach=0.12)
    bpy.data.objects.remove(sealed, do_unlink=True)
    shell.name = f"{NAME}_outline"
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import usp_talon as T
    T.cull_hidden(obj, grid=4, ndirs=40)
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    zmax = max(v.co.z for v in me.vertices) / U
    print(f"{NAME}_A: {tris} tris, z max {zmax:.2f} px, shell {len(shell.data.polygons)} faces")
    lay = [(n, cx - CX0, cy - CY0) for n, cx, cy in LAYOUT]
    bodies = common.split_assembly(obj, lay)
    shells = common.split_assembly(shell, lay)
    for n, _, _ in LAYOUT:
        sh = shells[n]
        sh.name = f"{n}_outline"
        sh["tyrian_outline"] = True
        bodies[n].data.shade_smooth()
        bodies[n].data.set_sharp_from_angle(angle=math.radians(35))
        common.export_sprite_model(WT, [bodies[n], sh], f"enemies/{n}", common.load_sprite(WT, n)["sprites"])


if __name__ == "__main__":
    main()
