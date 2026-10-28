"""Blue U-shaped craft (newsh^.shp frames 16, 18, 54, 56, an assembly of four pieces): a 3D
version of its sprites.

Seen in episode 4 (levels 4.10, 4.22, 4.50). Four 2x2 enemies make one 48x56 px object
(sprite.json `assemblyLayout`) shaped like a tuning fork: two big blue pods at the top
(newsh-caret-16, -18), each with a grey clamp round its outer side and a light pipe down its back,
run down into thinner struts with a grey rod and a dark grey joint, which bend inward and meet in a
round bar at the bottom (newsh-caret-54, -56). A small blue bulb on a grey stem points up from the
middle of the bar. Every piece has one frame.

The whole object is built once in assembly coordinates (left half, mirrored about the centre of
pixel column 24, the sprite's axis), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-54.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b012 import Grid, sweep, loft_y, plate, ellipsoid, mirror_all, to_object, merged_sprite, composite_png  # noqa: E402

NAME = "assembly-newsh-caret-54"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-16", "newsh-caret-18", "newsh-caret-54", "newsh-caret-56"]
# Assembly pixel (0, 0) is the top-left corner of newsh-caret-16 (screen 157 - 12, 31 - 14); the
# assembly is 48 x 56 px and its centre (screen 169, 45) is the Blender origin.
CX0, CY0 = 169, 45
G = Grid(48, 56)
AXIS_COL = 24  # mirror symmetric about the centre of pixel column 24


PXU = 1 / 12  # one sprite pixel in units


def surface(path):
    """The top of a sweep (path of (col, row, z, half_width_px, half_height_units), elliptic rings):
    a function (col, row) -> z of its upper surface there, or None off it."""
    def f(col, row):
        best = None
        for (c0, r0, z0, w0, h0), (c1, r1, z1, w1, h1) in zip(path, path[1:]):
            dc, dr = c1 - c0, r1 - r0
            ll = dc * dc + dr * dr
            t = 0.0 if ll == 0 else max(0.0, min(1.0, ((col - c0) * dc + (row - r0) * dr) / ll))
            d = math.hypot(col - (c0 + t * dc), row - (r0 + t * dr))
            w, h, z = w0 + t * (w1 - w0), h0 + t * (h1 - h0), z0 + t * (z1 - z0)
            if w > 0 and d < w:
                zz = z + h * math.sqrt(1 - (d / w) ** 2)
                best = zz if best is None else max(best, zz)
        return best
    return f


def top(surfs, col, row):
    zs = [z for z in (s(col, row) for s in surfs) if z is not None]
    return max(zs) if zs else 0.0


def on_top(surfs, pts, lift_px):
    """A detail path (col, row, half_width_px, half_height_px) riding lift_px above the surfaces."""
    return [(c, r, top(surfs, c, r) + lift_px * PXU, w, h * PXU) for c, r, w, h in pts]


def boolean_cut(bm, mats, build_target, build_cutters):
    """Build a closed target and cutters in their own meshes, subtract the cutters (their faces keep
    their own material index, so the cut walls and floor take the cutter's colour) and append the
    result to bm."""
    objs = []
    for i, fn in enumerate([build_target] + list(build_cutters)):
        b = bmesh.new()
        fn(b)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        me = bpy.data.meshes.new(f"_nshc54_tmp{i}")
        b.to_mesh(me)
        b.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(f"_nshc54_tmp{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    target = objs[0]
    for cutter in objs[1:]:
        cutter.hide_render = True
        mod = target.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"
        mod.material_mode = "INDEX"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    bm.from_mesh(me)
    for ob in objs:
        old = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(me)


def clamp_shell(bm, g, cx, a_in, b_in, a_out, b_out, col_end, rows, mats, bright_col, theta1_deg=190, n=12):
    """A curved clamp plate wrapped over the top and outer (-X) side of a pod whose centre is
    column cx: the shell between ellipses (a_in, b_in) and (a_out, b_out) (half-width px, half-height
    px) from the top inner end at column col_end round to theta1_deg, extruded along rows; rows is
    [(row, material of the band from this row to the next)], the last one's material unused."""
    th0 = math.acos((col_end - cx) / a_out)
    thb = math.acos((bright_col - cx) / a_out)
    th1 = math.radians(theta1_deg)
    ths = [th0, thb] + [thb + (th1 - thb) * k / (n - 1) for k in range(1, n)]
    rings = []
    for row, _ in rows:
        y = g.Y(row)
        outer = [bm.verts.new((g.X(cx) + a_out * PXU * math.cos(t), y, b_out * PXU * math.sin(t))) for t in ths]
        inner = [bm.verts.new((g.X(cx) + a_in * PXU * math.cos(t), y, b_in * PXU * math.sin(t))) for t in ths]
        rings.append(outer + inner[::-1])
    m = len(ths)
    for (ra, (_, mat)), rb in zip(zip(rings, rows), rings[1:]):
        L = len(ra)
        for k in range(L):
            j = (k + 1) % L
            f = bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
            f.material_index = mats[1] if k == 0 or k == L - 1 else mat
            f.smooth = False
    for ring in (rings[0], rings[-1]):
        outer, inner = ring[:m], ring[m:][::-1]
        for k in range(m - 1):
            f = bm.faces.new((outer[k], outer[k + 1], inner[k + 1], inner[k]))
            f.material_index = mats[1] if k == 0 else mats[0]
            f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc54"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(54, metallic=0.15, roughness=0.35),  # 0 blue pod hull (the sprite's pods average 53-55)
        pal(52, metallic=0.15, roughness=0.4),  # 1 dark blue struts and bar
        pal(60, metallic=0.4, roughness=0.25),  # 2 light blue pipe
        pal(50, metallic=0.2, roughness=0.6),  # 3 dark blue grooves and the plate in the U's mouth
        pal(5, metallic=0.7, roughness=0.35),  # 4 grey clamp and rod
        pal(3, metallic=0.5, roughness=0.5),  # 5 dark grey joint
        pal(106, metallic=0.7, roughness=0.3),  # 6 light grey edges
        pal(10, metallic=0.8, roughness=0.2),  # 7 bright grey edge
        pal(7, metallic=0.75, roughness=0.3),  # 8 grey stem collar
        pal(61, metallic=0.4, roughness=0.2),  # 9 pale blue highlights
        pal(56, metallic=0.35, roughness=0.3),  # 10 mid blue bumps
        pal(58, metallic=0.4, roughness=0.25),  # 11 lower arm highlight, knob
        pal(2, metallic=0.4, roughness=0.5),  # 12 near-black stem
    ]
    POD, STRUT, PIPE, GROOVE, GREY, JOINT, LIGHT, BRIGHT, STEM, PALE, BUMP, ARMLIGHT, BLACK = range(13)
    bm = bmesh.new()
    P = lambda pts: [(c, r, 0.0, w, h * PXU) for c, r, w, h in pts]  # noqa: E731

    # ---- left half (mirrored below) ----

    # The pod (columns 6-18, rows 0-22, outline included): a rounded nose, widest at rows 8-14,
    # running on under the clamp into the strut. Round in section: about 13 px wide, 10 px tall.
    pod = P([(12.0, -0.55, 0.0, 0.0), (12.0, -0.2, 2.0, 1.7), (11.8, 0.6, 3.0, 2.5), (11.5, 1.8, 4.0, 3.2),
             (11.3, 3.0, 4.8, 3.8), (11.3, 4.5, 5.4, 4.3), (11.5, 6.0, 6.0, 4.7), (11.9, 8.0, 6.5, 5.0),
             (12.0, 10.0, 6.4, 5.1), (12.0, 14.0, 6.4, 5.1), (12.6, 15.5, 6.3, 5.0), (12.9, 17.0, 6.4, 5.0),
             (12.9, 21.0, 6.3, 4.9), (12.6, 22.6, 5.8, 4.6)])
    # Strut below the pod (rows 22-31), the dark grey joint (rows 31-36) and the lower arm, which
    # bends inward into the bar along the bottom (rows 45-53) to the middle: a 7-8 px round tube.
    strut = P([(12.6, 22.0, 5.8, 4.6), (12.2, 24.5, 5.6, 4.4), (12.4, 27.0, 5.2, 4.1), (12.9, 29.0, 4.9, 3.9),
               (13.6, 31.0, 4.8, 3.8)])
    joint = P([(14.8, 30.8, 5.3, 4.1), (14.4, 36.2, 5.0, 4.0)])
    arm = P([(14.0, 35.8, 5.0, 4.0), (13.3, 38.5, 4.6, 3.8), (13.5, 41.5, 4.1, 3.5), (13.8, 43.8, 4.1, 3.5),
             (15.2, 46.6, 4.5, 3.8), (18.2, 48.4, 4.4, 3.8), (21.0, 49.7, 3.8, 3.4), (22.6, 50.0, 3.7, 3.3),
             (23.5, 50.0, 3.7, 3.3), (AXIS_COL, 50.0, 3.7, 3.3)])
    sp_pod, sp_strut, sp_joint, sp_arm = surface(pod), surface(strut), surface(joint), surface(arm)

    # Grey clamp round the top and outer side of the pod (columns 4-14, rows 16-22): a curved plate
    # 1.7 px proud of the pod top, sticking out 3 px past its outer side, with a light top edge and
    # a bright inner edge.
    CL_CX, CL_A, CL_B = 12.9, 9.3, 6.7
    clamp_shell(bm, G, CL_CX, 6.1, 4.7, CL_A, CL_B, 14.5, [(15.9, LIGHT), (17.3, GREY), (22.0, GREY)],
                (GREY, BRIGHT), 13.5)

    def sp_clamp(col, row):
        if not (15.9 <= row <= 22.0 and col <= 14.5):
            return None
        d = (col - CL_CX) / CL_A
        return CL_B * PXU * math.sqrt(1 - d * d) if abs(d) < 1 else None

    surfs = [sp_pod, sp_strut, sp_joint, sp_arm, sp_clamp]

    # The pod with the dark L groove cut into its top (column 9, rows 4-11, then across row 11).
    groove = [(9.6, 3.6, 0.0, 0.0), (9.4, 4.6, 0.6, 1.1), (9.0, 7.0, 0.6, 1.1), (9.0, 11.0, 0.6, 1.1),
              (10.4, 11.2, 0.6, 1.1), (11.8, 11.2, 0.6, 1.1), (12.6, 11.2, 0.0, 0.0)]
    boolean_cut(bm, mats, lambda b: sweep(b, G, pod, sides=16, mat=POD),
                [lambda b: sweep(b, G, on_top([sp_pod], groove, 0.0), sides=8, mat=GROOVE)])

    sweep(bm, G, strut, sides=14, mat=STRUT)
    sweep(bm, G, joint, sides=14, mat=JOINT)

    # A small blister on the inner flank of the pod (columns 17-20, rows 10-14) and a nub on the
    # strut's inner flank (columns 17-21, rows 22-29): round pods at the equator, half as tall as wide.
    ellipsoid(bm, G, 18.5, 12.0, 0.0, 2.3, 3.0, 2.6 * PXU, mat=BUMP)
    ellipsoid(bm, G, 18.9, 25.6, 0.0, 2.7, 4.2, 3.0 * PXU, mat=BUMP)
    # The dark blue fairing below the nub (columns 16-20, rows 29-34).
    ellipsoid(bm, G, 18.0, 31.2, 0.0, 2.6, 3.2, 3.2 * PXU, mat=STRUT)

    # Light pipe down the back of the pod (column 12, rows 12-19), over the clamp to column 8 and
    # down off it onto the strut.
    pipe = on_top(surfs, [(12.0, 11.6, 0.0, 0.0), (12.0, 12.2, 0.7, 0.6), (12.0, 15.5, 0.7, 0.6),
                          (12.0, 16.2, 0.7, 0.6), (12.0, 19.0, 0.7, 0.6), (10.0, 19.0, 0.7, 0.6),
                          (8.2, 19.0, 0.7, 0.6), (8.0, 21.6, 0.7, 0.6), (8.1, 22.4, 0.7, 0.6),
                          (8.4, 23.2, 0.6, 0.5)], 0.2)
    pipe.append((8.6, 23.8, pipe[-1][2], 0.0, 0.0))
    sweep(bm, G, pipe, sides=8, mat=PIPE)
    # The highlight down the inner flank of the pod (column 14, rows 4-11), nearly flush.
    sweep(bm, G, on_top([sp_pod], [(14.0, 3.6, 0.0, 0.0), (14.0, 4.6, 0.6, 0.5), (14.2, 10.8, 0.6, 0.5),
                                   (14.2, 11.6, 0.0, 0.0)], -0.25), sides=6, mat=PALE)

    # Grey rod down the strut (columns 12-13, rows 22-30), slanting through the joint to columns
    # 15-16 and on down the lower arm to the bar.
    rod_surfs = [sp_strut, sp_joint, sp_arm]
    sweep(bm, G, on_top(rod_surfs, [(12.5, 21.8, 1.1, 0.6), (12.5, 30.0, 1.1, 0.6), (14.4, 33.2, 1.0, 0.6),
                                    (14.9, 34.6, 0.0, 0.0)], 0.1), sides=8, mat=LIGHT)
    sweep(bm, G, on_top(rod_surfs, [(14.4, 33.0, 0.0, 0.0), (14.6, 33.6, 1.0, 0.6), (15.4, 36.8, 1.0, 0.6),
                                (15.4, 44.0, 1.0, 0.6), (15.9, 45.6, 0.0, 0.0)], 0.1), sides=8,
           mat=GREY)
    # Highlight down the crest of the lower arm (column 13, rows 37-44), nearly flush.
    sweep(bm, G, on_top([sp_arm], [(12.9, 36.6, 0.0, 0.0), (12.9, 37.4, 0.7, 0.5), (12.9, 43.0, 0.7, 0.5),
                                   (13.3, 44.4, 0.0, 0.0)], -0.25), sides=6, mat=ARMLIGHT)

    # Domes on the bar's top beside the stem (columns 18-20, rows 45-47), about 2.5 px proud.
    ellipsoid(bm, G, 19.0, 46.3, top(surfs, 19.0, 46.3) - 0.5 * PXU, 1.8, 1.6, 3.0 * PXU, mat=BUMP)

    mirror_all(bm, G.X(AXIS_COL))

    # ---- centre parts ----

    # The lower arms and the bar as one closed tube (both halves welded at the axis), with the dark
    # plate in the U's mouth (columns 21-27, rows 47-48) cut about 1 px into the bar's inner side.
    def u_tube(b):
        sweep(b, G, arm, sides=14, mat=STRUT, cap_end=False)
        mirror_all(b, G.X(AXIS_COL))
        ax = G.X(AXIS_COL)
        bmesh.ops.remove_doubles(b, verts=[v for v in b.verts if abs(v.co.x - ax) < 1e-4], dist=1e-4)
    plate_floor = 1.6 * PXU
    boolean_cut(bm, mats, u_tube,
                [lambda b: plate(b, G, [(21, 47), (28, 47), (28, 49), (21, 49)], plate_floor, 0.8, mat=GROOVE)])

    # Near-black stem (rows 42-44) and grey collar (rows 45-47) running from the bar up to the knob.
    stem_z = 2.4 * PXU
    loft_y(bm, G, AXIS_COL, [(41.6, 2.0, 1.3 * PXU, stem_z), (44.6, 2.2, 1.4 * PXU, stem_z)], sides=10, mat=BLACK)
    loft_y(bm, G, AXIS_COL, [(44.4, 2.3, 1.8 * PXU, stem_z), (45.3, 2.5, 2.0 * PXU, stem_z),
                             (47.4, 2.3, 1.8 * PXU, stem_z)], sides=10, mat=STEM)
    # The knob (columns 21-27, rows 36-42 with its outline): a ball about 6 px across, top at about
    # 6 px, with the dark slot down its middle (column 24) cut in. The slot sits 0.2 px left of the
    # pixel column so that both pieces' edges (x = 0) fall inside it, not on its wall.
    knob_z, knob_r = 2.8 * PXU, 3.1
    boolean_cut(bm, mats, lambda b: ellipsoid(b, G, AXIS_COL, 39.0, knob_z, knob_r, 3.6, knob_r * PXU,
                                              mat=ARMLIGHT, segments=16, rings=8),
                [lambda b: plate(b, G, [(23.8, 36), (24.8, 36), (24.8, 43), (23.8, 43)], knob_z + 1.4 * PXU, 0.8,
                                 mat=GROOVE)])
    # Glossy highlight on the crest of the bar (rows 49-50), nearly flush.
    ellipsoid(bm, G, AXIS_COL, 49.6, top([sp_arm], AXIS_COL, 49.6) - 0.3 * PXU, 3.4, 1.0, 0.5 * PXU, mat=PALE)

    return to_object(NAME, bm, mats, coll)


def main():
    sprite = merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    # The faces split_assembly fills where it cuts are smooth, which bends the shading of the
    # surface next to them into a dark crease along the cut (the bar's middle): make them flat.
    for piece in pieces.values():
        me = piece.data
        for poly in me.polygons:
            xs = [abs(me.vertices[v].co.x) for v in poly.vertices]
            ys = [abs(me.vertices[v].co.y) for v in poly.vertices]
            if all(abs(x - 1.0) < 1e-4 for x in xs) or all(abs(y - 14 / 12) < 1e-4 for y in ys):
                poly.use_smooth = False
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
