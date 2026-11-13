"""FLEET boss deck hatch (newsho.shp, the 2-piece assembly-newsho-191: newsho-191 + newsho-193, 48 x 22 px).

What it is: a launch hatch on the deck of FLEET's (3.6, main=12) flying capital ship. Three of them
(enemy types 737/738, armour 60) spawn on tick 5020 on the same link as the upper hull
(assembly-newsho-79) and the lower hull (assembly-newsho-156), rigidly stacked on them (two over the
wing bays, one on the ventral pod's deck); their lids open in five frames and they launch type 703
(newshk-245).

Read from the sprite: an armoured coaming (a grey frame with a chamfered outer edge; its lit top/left
and dark bottom/right edges are lighting and ink, not paint) round a black launch well, closed by one
heavy lid. The lid has three hinge blocks along its back edge (row 6-8, split at columns 19-20 and
28-29), a raised stepped hump (a wide block, rows 12-18, under a narrower one, rows 9-12), slatted vents
with studs on both sides, a chamfered front lip and two latches over it. The five frames are the lid
swinging up on its back hinge (front edge towards the camera): ANGLES are fitted so the lit lip lands
on sprite rows 19 (closed), 14, 12, 9 and 7 (cos(angle) ~ (lip row - 6) / 13).

Each frame is its own model (newsho-191, newsho-191-f2 ... -f5 and the same for newsho-193): the whole
hatch is built once per frame in assembly coordinates, gets one outline shell (D90/D118, sunk under
the creases, D185) and is cut into the two pieces with common.split_assembly.

Units: c, r = assembly pixel edges (48 x 28; (0, 0) = newsho-191's top-left, screen (117, 25));
Blender X = (c - 24) / 12, Y = (14 - r) / 12, Z units.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsho-191.py
(--noexport and --review DIR are for scratch work.)
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
NAME = "assembly-newsho-191"
PIECES = ["newsho-191", "newsho-193"]
CX0, CY0 = 141, 39  # screen centre of the hatch: the Blender origin (assembly edge (24, 14))
W, H = 48, 28
AX = 24.0
PX = L.PX
fillet = L.fillet

ANGLES = [0.0, 52.0, 62.0, 77.0, 86.0]  # lid angle per frame (degrees, front edge up)
RIM_TOP = 0.30  # top of the coaming
FLOOR = 0.03  # floor of the launch well
LID_TOP = 0.27  # the lid's top face when closed (also the hinge height)
LID_T = 2.4 * PX  # lid plate thickness

MAT = L.Mats(ROOT, PIECES, NAME, "nsho191")
FRAME = MAT(4, 0.45, 0.45)  # the coaming (sprite median index 4)
FRAME_CH = MAT(5, 0.5, 0.4, 0.65)  # its chamfer
PIT = MAT(1, 0.1, 0.85, 0.2)  # the black launch well
TOP = MAT(2, 0.45, 0.42)  # the lid's top (median index 2)
LIP = MAT(3, 0.5, 0.36, 0.65)  # chamfers, hump edges
STUD = MAT(5, 0.6, 0.3, 0.75)  # studs, latches
PIN = MAT(1, 0.5, 0.5, 0.4)  # the hinge barrel: black in the sprite's gaps between the blocks (index 1)
KEEL = MAT(4, 0.4, 0.5, 0.5)  # underside


def rect(c0, r0, c1, r1, rad, k=2):
    return fillet([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], rad, k)


def build_coaming(B):
    """The frame and the well as one closed loft: outer wall, chamfer, top, inner wall, well floor."""
    outer = rect(1.0, 2.0, 46.0, 23.0, 0.8)
    top_out = rect(1.9, 2.9, 45.1, 22.1, 0.5)
    top_in = rect(4.0, 4.0, 44.0, 21.0, 0.3)
    loops = [[(c, r, -0.12) for c, r in outer], [(c, r, RIM_TOP - 0.08) for c, r in outer],
             [(c, r, RIM_TOP) for c, r in top_out], [(c, r, RIM_TOP) for c, r in top_in],
             [(c, r, FLOOR) for c, r in top_in]]
    mats = [FRAME, FRAME_CH, FRAME, PIT]
    B.rings(loops, lambda k, i: mats[k], top=PIT, bottom=KEEL)
    # Ribs across the well floor (black like it; only their shading shows when the lid is open).
    for r in (7.5, 11.0, 14.5, 18.0):
        B.box(4.6, r, 43.4, r + 0.9, FLOOR - 0.01, FLOOR + 0.05, PIT, PIT, ch=0.2, chz=0.015)


def build_lid(B):
    t, b = LID_TOP, LID_TOP - LID_T
    # Main plate (rows 8-19.6), its front top edge chamfered into the lip.
    B.slab(rect(5.0, 8.0, 43.0, 19.6, 0.5), b, t, TOP, TOP, ch=0.9, chz=0.06, bevel=LIP)
    # Three hinge blocks along the back edge and the hinge barrel through them. The sprite's back edge
    # (rows 6-8) is dark grey (index 2) all along, so the blocks' chamfer stays TOP (a lit index-3
    # bevel drew a row of light bars there) and the barrel is black like the gaps (index 1).
    for c0, c1 in ((5.0, 19.0), (21.0, 28.0), (30.0, 43.0)):
        B.slab(rect(c0, 6.0, c1, 8.4, 0.3), b, t + 0.03, TOP, TOP, ch=0.4, chz=0.03)
    zc = t - LID_T / 2
    B.sweep([(4.6, 6.4, zc, 0.0, 0.0), (4.8, 6.4, zc, 1.1, 1.1 * PX), (43.2, 6.4, zc, 1.1, 1.1 * PX),
             (43.4, 6.4, zc, 0.0, 0.0)], sides=10, mat=PIN)
    # Stepped hump: a wide block (rows 12-18) under a narrow one (rows 9-12).
    hump = [(11.0, 12.0), (16.0, 12.0), (16.0, 9.0), (33.0, 9.0), (33.0, 12.0), (38.0, 12.0), (38.0, 18.2),
            (11.0, 18.2)]
    B.slab(hump, t - 0.01, t + 0.06, TOP, LIP, ch=0.7, chz=0.03)
    B.slab(fillet([(16.8, 9.8), (32.2, 9.8), (32.2, 12.8), (16.8, 12.8)], 0.4, 2), t + 0.05, t + 0.10, TOP, LIP,
           ch=0.6, chz=0.025)
    # Slatted vents on both sides, with studs beside them.
    for c0, c1 in ((5.6, 10.0), (38.8, 42.6)):
        B.box(c0, 12.8, c1, 18.8, t - 0.02, t + 0.004, PIT, PIT, ch=0.1, chz=0.005)
        for r in (13.5, 15.5, 17.5):
            B.sweep([(c0 + 0.1, r, t + 0.012, 0.0, 0.0), (c0 + 0.35, r, t + 0.012, 0.5, 0.022),
                     (c1 - 0.35, r, t + 0.012, 0.5, 0.022), (c1 - 0.1, r, t + 0.012, 0.0, 0.0)], sides=6, mat=LIP,
                    power=0.7)
    for c, r in ((7.0, 10.0), (41.0, 10.0), (7.0, 11.6), (41.0, 11.6)):
        B.ellipsoid(c, r, t, 0.5, 0.5, 0.035, STUD, seg=8, rings=4)
    # Two latches over the front edge.
    for c in (21.0, 29.0):
        B.slab(rect(c - 0.1, 18.6, c + 1.1, 20.8, 0.2), t - 0.14, t + 0.03, STUD, STUD, ch=0.25, chz=0.02)


def build(frame, coll):
    B = L.Builder(24, 14, AX)
    build_coaming(B)
    start = len(B.bm.verts)
    build_lid(B)
    a = math.radians(ANGLES[frame])
    ca, sa = math.cos(a), math.sin(a)
    yh, zh = (14 - 6.4) * PX, LID_TOP - LID_T / 2  # the hinge axis (row 6.4)
    B.bm.verts.ensure_lookup_table()
    for v in B.bm.verts[start:]:
        dy, dz = v.co.y - yh, v.co.z - zh
        v.co.y = yh + dy * ca + dz * sa
        v.co.z = zh - dy * sa + dz * ca
    return B.to_object(f"{NAME}-f{frame + 1}", MAT.list, coll)


def model_name(piece, frame):
    return piece if frame == 0 else f"{piece}-f{frame + 1}"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    lay = L.layout(ROOT, PIECES, CX0, CY0)
    datas = {name: common.load_sprite(ROOT, name) for name in PIECES}
    nframes = len(datas[PIECES[0]]["frames"])
    assert nframes == len(ANGLES)
    for frame in range(nframes):
        coll = common.reset_collection(f"{NAME}-f{frame + 1}")
        obj = build(frame, coll)
        pieces, shells = L.shell_and_split(obj, lay, coll, voxel=0.012, faces=1500, inside=0.004, margin=0.008,
                                           reach=0.04)
        total = sum(L.tris(p) for p in pieces.values())
        print("frame", frame + 1, "pieces tris", total, "shell tris", sum(L.tris(s) for s in shells.values()))
        if "--noexport" not in argv:  # the game contract, as the old script: one model per piece per frame
            for name in PIECES:
                spr = datas[name]["sprites"][0]
                sub = [{**spr, "frames": [spr["frames"][frame]]}]
                common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{model_name(name, frame)}",
                                           sub)
        L.place(pieces, shells, lay)
        obj.hide_render = True
        if "--review" in argv:
            L.review(list(shells.values()), Path(argv[argv.index("--review") + 1]) / f"f{frame + 1}", W, H,
                     quick="--quick" in argv or frame not in (0, 2), dist=7.0, k=10,
                     stats={"tris": total, "pal": sorted({k[0] for k in MAT.slots})})
        for o in list(coll.objects):
            o.hide_render = True


if __name__ == "__main__":
    main()
