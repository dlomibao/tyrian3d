"""FLEET boss lower hull (newsho.shp, the 7 pieces of assembly-newsho-156, 120 x 56 px).

What it is: the underside unit of FLEET's (3.6, main=12) capital ship, a FLYING warship. It spawns on
tick 5020 on the same link as the blue upper hull (assembly-newsho-79) and the deck hatches
(assembly-newsho-191), rigidly stacked under them, drifts against the terrain with a weaving x cycle
and leaves on the left. The fire above its middle in the sprite (newshk-51/53/55) is a separate
falling column (assembly-newshk-51), not part of this hull.

Read from the sprite (mirror symmetric about pixel edge 59.5):
  * middle (newsho-120/122/124): the ventral pod (its top edge is the ink line under the fire, row 0), a blue armoured tub with rounded lower corners and a
    chamfered rim round a dark grey deck plate; slatted vent grilles at both ends of the deck, a rib
    across it, a grey front lip, and under the lip three grey skids: two wedge blocks and a middle one
    with a rounded nose. (The third deck hatch sits on this deck in game.)
  * each side (newsho-118 over newsho-156 on the left, newsho-126 over newsho-164 on the right): a gun
    arm hanging from the hull: a mounting bracket (a top beam with a lit front chamfer, an outer post,
    a lower beam and a dark slot between them), a square post with a dark recess beside it, a collar,
    two hydraulic rams side by side (the left one thicker), a cross bar with a side tab, the ram
    housing (a side box, the polished main ram, a small bracket) and at its end the gun turret drum
    (enemy types 735/736, armour 60): a chamfered drum with a dark face and a hub. The turrets do not
    rotate (single frame, no aim), so the drum is plain geometry in its piece.
Highlights are sheen and the outline ring is ink (art rule 2): nothing is modelled from them; parts
take the sprite's own median palette index per region.

Units: c, r = assembly pixel edges (120 x 56, the composite of the 7 pieces; (0, 0) = screen (56, 69));
Blender X = (c - 60) / 12, Y = (28 - r) / 12, Z units. Built once and cut into the pieces with
common.split_assembly; one outline shell (D90/D118/D185) for the whole unit, split open per piece.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsho-156.py
(--noexport, --out X.glb and --review DIR are for scratch work.)
"""

import math
import sys
from pathlib import Path

import bpy

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b093 as L  # noqa: E402

ROOT = WT
NAME = "assembly-newsho-156"
PIECES = ["newsho-156", "newsho-164", "newsho-118", "newsho-120", "newsho-122", "newsho-124", "newsho-126"]
CX0, CY0 = 116, 97  # screen pixel of composite edge (60, 28): the Blender origin
W, H = 120, 56
AX = 59.5  # mirror axis (pixel edges)
PX = L.PX
fillet = L.fillet

MAT = L.Mats(ROOT, PIECES, NAME, "nsho156")
K1 = MAT(1, 0.2, 0.75, 0.3)  # dark recesses, slots, the drum's face
K2 = MAT(2, 0.35, 0.55, 0.5)  # deck plate, beam tops
K3 = MAT(3, 0.45, 0.45)  # bracket posts, beams, skid tops
K4 = MAT(4, 0.45, 0.42)  # lip, rails, cross bar, drum
K5 = MAT(5, 0.5, 0.38, 0.65)  # skids, hub, drum rim
K6 = MAT(6, 0.5, 0.36, 0.7)  # collar
RAM = MAT(6, 0.6, 0.22, 0.9)  # polished rams (sprite median index 6; D176 F0: the sheen is lighting)
ROD = MAT(7, 0.6, 0.22, 0.9)  # polished piston rods (median index 7)
B56 = MAT(56, 0.4, 0.4, 0.6)  # the blue tub
KEEL = MAT(4, 0.4, 0.5, 0.5)  # underside


def build_arm(B):
    """One gun arm (left; called again mirrored)."""
    # Mounting bracket: top beam (rows 1-4) with a lit front chamfer, outer post, right lip, a lower
    # beam (rows 6-10) and the dark slot between it and the top beam.
    B.slab([(4.8, 0.8), (20.2, 0.8), (20.2, 4.0), (4.8, 4.0)], 0.20, 0.64, K2, K3, ch=0.8, chz=0.08, bevel=K4)
    B.slab([(4.8, 3.6), (9.2, 3.6), (9.2, 9.6), (7.8, 9.5), (5.8, 8.3), (4.8, 7.2)], 0.10, 0.58, K3, K3, ch=0.7,
           chz=0.06, bevel=K4)
    B.slab([(17.4, 3.6), (21.2, 3.9), (21.2, 5.9), (19.9, 6.9), (19.0, 7.5), (17.4, 7.5)], 0.10, 0.56, K4, K4, ch=0.6, chz=0.05)
    B.slab([(8.6, 3.8), (18.0, 3.8), (18.0, 6.4), (8.6, 6.4)], 0.05, 0.28, K1, K1, ch=0.2, chz=0.02)
    B.slab([(9.0, 6.2), (18.2, 6.2), (18.2, 10.0), (9.0, 10.0)], 0.05, 0.46, K3, K3, ch=0.6, chz=0.05, bevel=K4)
    for c in (11.0, 13.4, 15.8):  # bolt heads on the lower beam
        B.ellipsoid(c, 8.2, 0.455, 0.55, 0.55, 0.04, K5, seg=8, rings=4)
    # Square post (rows 10-17) and the dark recess beside it.
    B.slab([(9.0, 9.8), (13.2, 9.8), (13.2, 17.0), (9.0, 17.0)], 0.05, 0.46, K3, K3, ch=0.6, chz=0.06, bevel=K4)
    B.slab([(13.0, 9.9), (18.2, 9.9), (18.2, 12.2), (17.2, 12.5), (14.2, 13.0), (14.0, 13.9), (13.0, 13.9)], 0.0, 0.18, K1, K1,
           ch=0.2, chz=0.02)
    # Collar where the rams leave the post (rows 16.6-18.2).
    B.slab(fillet([(9.0, 16.6), (14.4, 16.6), (16.2, 17.2), (16.2, 18.3), (9.0, 18.3)], [0, 0.6, 0.4, 0, 0], 2), 0.05,
           0.44, K6, K6, ch=0.5, chz=0.05)
    # Two hydraulic rams (rows 18-27): the left one thicker, polished rods.
    for cc, rad in ((11.1, 2.2), (14.8, 1.4)):
        R = rad * PX
        B.sweep([(cc, 17.6, 0.30, rad, R), (cc, 26.0, 0.30, rad, R)], sides=12, mat=ROD)
        B.sweep([(cc, 17.4, 0.30, rad + 0.3, R + 0.3 * PX), (cc, 18.4, 0.30, rad + 0.3, R + 0.3 * PX)], sides=12,
                mat=K5)
    # Cross bar with its side tab (rows 23-27).
    B.slab([(8.2, 22.8), (9.6, 22.8), (9.6, 24.8), (13.6, 24.8), (13.6, 27.2), (6.8, 27.2), (6.8, 24.4)], 0.05, 0.40,
           K4, K4, ch=0.5, chz=0.05)
    # Ram housing (rows 27-37): side box, the polished main ram, a small bracket.
    B.slab([(6.8, 26.8), (11.4, 26.8), (11.4, 37.8), (6.8, 37.8)], 0.05, 0.44, K3, K3, ch=0.6, chz=0.06, bevel=K4)
    rr = 2.5
    R = rr * PX
    B.sweep([(13.7, 23.6, 0.34, rr * 0.8, R * 0.8), (13.7, 24.4, 0.34, rr, R), (13.7, 30.4, 0.34, rr, R),
             (13.7, 30.6, 0.34, rr * 0.85, R * 0.85), (13.7, 31.4, 0.34, rr * 0.85, R * 0.85),
             (13.7, 31.6, 0.34, rr, R), (13.7, 37.6, 0.34, rr, R)], sides=14, mat=RAM)
    B.slab(fillet([(15.8, 29.9), (16.9, 30.0), (17.2, 30.9), (19.0, 31.0), (19.2, 31.9), (20.2, 32.0), (20.2, 36.0),
                   (19.2, 36.2), (19.0, 37.2), (15.8, 37.2)], [0, 0, 0, 0, 0, 0.3, 0.3, 0, 0, 0], 2), 0.05, 0.30, K4, K4, ch=0.5, chz=0.04)
    # The gun turret drum (rows 37.5-46.5).
    # A rounded drum (the sprite's is nearly square: cols 8-19, rows 37-46), its stub barrel forward.
    drum = fillet([(7.9, 37.0), (19.1, 37.0), (19.1, 46.1), (7.9, 46.1)], 1.5, 3)
    B.slab(drum, 0.0, 0.46, K1, K4, ch=1.3, chz=0.09, bevel=K5)
    B.sweep([(15.0, 44.0, 0.22, 1.9, 1.9 * PX), (15.0, 46.4, 0.22, 1.9, 1.9 * PX), (15.0, 46.9, 0.22, 1.5, 1.5 * PX),
             (15.0, 47.0, 0.22, 0.0, 0.0)], sides=12, mat=K5)
    B.sweep([(15.0, 46.75, 0.22, 0.9, 0.9 * PX), (15.0, 47.02, 0.22, 0.9, 0.9 * PX)], sides=10, mat=K1)
    hub = [(14.2 + 1.9 * math.cos(2 * math.pi * (i + 0.5) / 16), 42.6 + 1.7 * math.sin(2 * math.pi * (i + 0.5) / 16))
           for i in range(16)]
    B.slab(hub, 0.30, 0.56, K3, K5, ch=0.5, chz=0.05)
    B.ellipsoid(14.2, 42.6, 0.56, 0.7, 0.6, 0.05, K1, seg=8, rings=4)


def build_body(B):
    """The ventral pod (newsho-120/122/124), whole (not mirrored)."""
    B.mir = False
    # Row by row inside the sprite's ink (it is a pixel narrower on the right at rows 0-4 and 10-14).
    plan = [(33.9, 0.7), (33.9, 3.9), (32.9, 4.2), (31.9, 5.0), (31.9, 11.8), (32.9, 12.3), (33.2, 13.9),
            (34.9, 14.4), (36.9, 15.3), (38.9, 16.2), (39.8, 17.0), (79.2, 17.0), (80.1, 16.2), (83.1, 15.2),
            (84.1, 14.4), (86.1, 13.9), (86.1, 10.0), (87.1, 9.8), (87.1, 5.0), (85.1, 4.2), (84.1, 3.9), (84.1, 0.7)]
    # The blue tub: a closed loft, keel inset under it, a chamfered rim on top.
    keel = L.inset(plan, 4.0)
    rim = L.inset(plan, 1.6)
    B.rings([[(c, r, -0.40) for c, r in keel], [(c, r, -0.02) for c, r in plan], [(c, r, 0.14) for c, r in plan],
             [(c, r, 0.24) for c, r in rim]], lambda k, i: KEEL if k == 0 else B56, top=B56, bottom=KEEL)
    # Dark grey deck plate (cols 36-83, rows -2..11) and its side rails.
    B.slab([(36.0, 0.7), (83.0, 0.7), (83.0, 11.2), (36.0, 11.2)], 0.10, 0.32, K2, K3, ch=0.4, chz=0.03)
    for s in (0, 1):
        B.mir = bool(s)
        B.slab([(35.6, 0.7), (39.0, 0.7), (39.0, 11.0), (35.6, 11.0)], 0.10, 0.38, K4, K4, ch=0.5, chz=0.05)
        # Slatted vent grille at the deck's end (rows -1..6).
        B.slab([(39.6, 0.8), (45.6, 0.8), (45.6, 6.0), (39.6, 6.0)], 0.10, 0.33, K1, K1, ch=0.2, chz=0.02)
        for r0 in (1.0, 3.0, 5.0):
            B.sweep([(39.9, r0 + 0.45, 0.34, 0.0, 0.0), (40.2, r0 + 0.45, 0.34, 0.5, 0.035),
                     (45.3, r0 + 0.45, 0.34, 0.5, 0.035), (45.6, r0 + 0.45, 0.34, 0.0, 0.0)], sides=6, mat=K3,
                    power=0.7)
        # Skid under the lip: a wedge block sloping down to the front.
        B.slab([(45.6, 10.8), (51.2, 10.8), (51.2, 17.0), (45.6, 17.0)], -0.05, 0.0, K3, K5, ch=0.6, chz=0.05,
               zf=lambda c, r: 0.34 - 0.035 * (r - 10.8))
    B.mir = False
    # A rib across the deck (rows 6.6-7.8) and the grey front lip (rows 8.6-11).
    B.box(39.0, 6.6, 80.0, 7.8, 0.20, 0.355, K3, K3, ch=0.25, chz=0.02)
    B.slab([(36.0, 8.6), (83.0, 8.6), (83.0, 11.2), (36.0, 11.2)], 0.10, 0.36, K4, K4, ch=0.6, chz=0.06)
    for c in (52.0, 59.5, 67.0):  # bolts on the lip
        B.ellipsoid(c, 9.9, 0.358, 0.5, 0.5, 0.035, K6, seg=8, rings=4)
    # Middle skid with a rounded nose (rows 11-18).
    B.slab([(55.6, 10.8), (63.4, 10.8), (63.4, 15.4), (55.6, 15.4)], -0.05, 0.30, K3, K4, ch=0.6, chz=0.05)
    hn = 2.4
    B.sweep([(55.7, 15.6, 0.16, 0.0, 0.0), (55.9, 15.6, 0.16, hn, hn * PX * 0.9), (63.1, 15.6, 0.16, hn, hn * PX * 0.9),
             (63.3, 15.6, 0.16, 0.0, 0.0)], sides=14, mat=K5)


def build(coll):
    B = L.Builder(60, 28, AX)
    build_body(B)
    for s in (0, 1):
        B.mir = bool(s)
        build_arm(B)
    return B.to_object(NAME, MAT.list, coll)


def shell_and_split_parts(obj, lay, coll, voxel, faces, inside, margin, reach, min_area=0.05):
    """L.shell_and_split, but one outline shell per loose part: the hull and the two gun arms are
    separate islands, and common.outline_shell keeps only the largest island (the arms drew without
    ink). The sealed copy is voxel-remeshed once to find the parts (overlapping slabs fuse), each part
    above `min_area` (XY extent, Blender units^2) gets its own shell from the original faces inside its
    box, the shells are joined, sunk (D185) and split open per piece (D90/D118)."""
    import bmesh
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    probe = sealed.copy()
    probe.data = sealed.data.copy()
    coll.objects.link(probe)
    rm = probe.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pm = probe.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
    bm.from_mesh(pm)
    bm.verts.ensure_lookup_table()
    seen, boxes = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, xs, ys = [v], [], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            xs.append(x.co.x)
            ys.append(x.co.y)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        box = (min(xs), min(ys), max(xs), max(ys))
        if (box[2] - box[0]) * (box[3] - box[1]) >= min_area:
            boxes.append(box)
    bm.free()
    probe.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(probe, do_unlink=True)
    merged = True  # a part whose box overlaps another (the drum's stub barrel) joins it
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    boxes[i] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    print("outline parts", len(boxes), [tuple(round(b, 2) for b in bx) for bx in boxes])
    part_shells = []
    pad = 2 * voxel
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        part = sealed.copy()
        part.data = sealed.data.copy()
        part.name = f"{NAME}_part{i}"
        coll.objects.link(part)
        pb = bmesh.new()
        pb.from_mesh(part.data)
        drop = [f for f in pb.faces if not (x0 - pad <= f.calc_center_median().x <= x1 + pad
                                           and y0 - pad <= f.calc_center_median().y <= y1 + pad)]
        bmesh.ops.delete(pb, geom=drop, context="FACES")
        pb.to_mesh(part.data)
        pb.free()
        bpy.context.view_layer.update()
        part_shells.append(common.outline_shell(part, coll, voxel=voxel, faces=faces, inside=inside))
        bpy.data.objects.remove(part, do_unlink=True)
    bpy.data.objects.remove(sealed, do_unlink=True)
    bpy.context.view_layer.update()
    for o in coll.objects:
        o.select_set(False)
    for s in part_shells:
        s.select_set(True)
    bpy.context.view_layer.objects.active = part_shells[0]
    bpy.ops.object.join()
    shell = part_shells[0]
    shell.name = f"{NAME}_outline"
    L.sink_shell(shell, obj, margin, reach)
    shells = L.split_open(shell, lay, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for s in shells.values():
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.data.shade_smooth()
        print("shell", s.name, "faces", len(s.data.polygons))
    shell.hide_render = True
    pieces = common.split_assembly(obj, lay, coll)
    for p in pieces.values():
        L.flatten_cut_faces(p)
    return pieces, shells


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    print("whole tris", L.tris(obj))
    lay = L.layout(ROOT, PIECES, CX0, CY0)
    pieces, shells = shell_and_split_parts(obj, lay, coll, voxel=0.015, faces=2500, inside=0.005, margin=0.01,
                                       reach=0.05)
    total = sum(L.tris(p) for p in pieces.values())
    print("pieces total tris", total, "shell tris", sum(L.tris(s) for s in shells.values()))
    if "--noexport" not in argv:  # the game contract, as the old script
        for name in PIECES:
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}",
                                       common.load_sprite(ROOT, name)["sprites"])
    L.place(pieces, shells, lay)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + list(shells.values()), out)
    if "--review" in argv:
        obj.hide_render = True
        L.review(list(shells.values()), argv[argv.index("--review") + 1], W, H, quick="--quick" in argv,
                 dist=13.0, stats={"tris": total, "pal": sorted({k[0] for k in MAT.slots})})


if __name__ == "__main__":
    main()
