"""Bronze drill spike (newshh.shp 17 over 55, one 24x56 px object).

What it is: the TAIL SPIKE at the top of a swaying column of seven (drill, five newshh-93 bronze
bowls, the newshh-131 pod). Each drill spawns with its pod and five bowls in one column; it flies
(level 2.2, top layer), so it is built free-flying, its long axis level (D163), round in section
with a closed round belly. Nose UP (the column trails below it).

Read as a telescoping drill spike: a long ogive nose spike with a hardened tip insert, then three
telescoping bronze sleeves, each with a V-cut front lip (the sprite's three chevrons, apex forward
on the centre column), the outer sleeve with a V notch over its rear, and in that notch the ball
coupling knuckle that joins the first bowl (the sprite's hot spot at rows 47-49). The crest line
down the centre column and the hot spots are sheen on round polished bronze, not paint.

Design B leads with the silhouette and the read at the small tilted game camera: each tier is a
thick-walled tube whose lip stands a clear step proud of the tier ahead of it, with a chamfered,
lighter-trimmed lip edge, so the three chevrons and the stepped widening read even at 24x56 px.

Geometry in sprite pixels: u = column edge (0..24), v = row edge (0..56) of the composite; the axis
is column 12's centre (u 12.5). Blender: X = (u - 12) / 12, Y = (28 - v) / 12, Z up, 12 px = 1 unit.
Plan half widths sit on the INNER edge of the sprite's ink border (D74).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshh-55.py
(exports public/models/enemies/newshh-17.glb and newshh-55.glb, cut at the row-28 seam)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = ROOT = common.repo_root(__file__)

NAME = "assembly-newshh-55"
TAG = "nshh55B"
PIECES = ["newshh-17", "newshh-55"]
CX0, CY0 = 143, -4  # screen centre of the 24x56 assembly
AXIS_U = 12.5
N = 36  # sides round the axis; vertex 9 sits on the crest (theta 90)
pchip = T.pchip


def X(u):
    return (u - 12.0) / 12.0


def Y(v):
    return (28.0 - v) / 12.0


# --- section ---------------------------------------------------------------------------------------
# Round, a touch taller over the top with a soft crest ridge on the centre column (the sprite's
# bright centre line); the belly a little flatter. Theta 0 = east flank, 90 = crest, 270 = keel.
HU, KR, HL = 0.92, 0.28, 0.80
KR_SPIKE, KR_BALL = 0.4, 0.1  # a sharper crest down the nose spike (its sheen line); the ball round


def sec(theta, r, kr=KR):
    c, s = math.cos(theta), math.sin(theta)
    x = r * c
    if s >= 0:
        z = HU * r * ((1 - kr) * s + kr * (1 - abs(c)))
    else:
        z = HL * r * s
    return x, z


THETAS = [2 * math.pi * k / N for k in range(N)]


# --- parts as rings ------------------------------------------------------------------------------
# A part is a list of rings; a ring is (vfun(theta) -> v, r_px). Consecutive rings are joined, with
# the band's material and shading given per band.

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.play = self.bm.faces.layers.int.new("part")

    kr = KR

    def ring(self, vfun, r):
        out = []
        for th in THETAS:
            x, z = sec(th, r, self.kr)
            out.append(self.bm.verts.new((X(AXIS_U) + x / 12.0, Y(vfun(th)), z / 12.0)))
        return out

    def point(self, v, z=0.0):
        return self.bm.verts.new((X(AXIS_U), Y(v), z / 12.0))

    def band(self, a, b, mat, part, smooth=True):
        for i in range(N):
            j = (i + 1) % N
            f = self.bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mat
            f.smooth = smooth
            f[self.play] = part

    def fan(self, ring, p, mat, part, smooth=True, rev=False):
        for i in range(N):
            j = (i + 1) % N
            f = self.bm.faces.new((ring[i], ring[j], p) if not rev else (ring[j], ring[i], p))
            f.material_index = mat
            f.smooth = smooth
            f[self.play] = part


def const(v):
    return lambda th: v


# Palette: the sprite's index per region, the median of its pixels without the dark shading ramp
# (16-18, the side away from the light) and the sheen (28-31): nose 22, sleeves 22; knuckle 21 (its pixels' median is 20-21). Hardened tip insert
# 23, lip chamfers 24 (a machined bevel trim, as newshh-93's rim trim 24), the seam grooves 19.
NOSE, TIP, S1, S2, S3, KNU, TRIM, GROOVE = range(8)
KNU_PROPS = (0.36, 0.32)  # the ball is polished: its sheen is the sprite's hot spot
PAL = {NOSE: 22, TIP: 23, S1: 22, S2: 22, S3: 22, KNU: 21, TRIM: 24, GROOVE: 19}
PROPS = {19: (0.25, 0.6), 21: (0.32, 0.45), 22: (0.32, 0.4), 23: (0.34, 0.36), 24: (0.36, 0.34)}
PART_NAMES = ["spike", "sleeve1", "sleeve2", "sleeve3", "knuckle"]

# Nose spike half width (px) down the rows: a smooth ogive whose pixel steps are the sprite's
# staircase (rows 15-16 0.5, 17-18 1.5, 19-21 2.5, 22-25 3.5, 26-34 4.5 on the inner mask).
SPIKE = pchip([14.5, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 40.0],
              [0.0, 0.3, 0.72, 1.18, 1.62, 2.02, 2.36, 2.64, 2.96, 3.25, 3.5, 3.72, 3.96, 4.2, 4.4, 4.52, 4.58, 4.62])
TIP_SEAM = 21.0
SPIKE_END = 37.5

# Sleeves: (outer radius, inner radius, lip apex row, lip sweep, rear(theta) -> v). Each bore is a
# hair smaller than the part inside it (a bearing fit), so the parts meet and the outline shell's
# voxel remesh makes one closed body of them.
# Sweep: the lip's row at the flank is apex + sweep (a straight V in plan, |x| = (v - apex) R / sweep).
S1R, S1I, S1A, S1W = 6.5, 4.4, 30.85, 5.55
S2R, S2I, S2A, S2W = 8.3, 6.25, 36.8, 6.4
S3R, S3I, S3A, S3W = 8.62, 6.85, 39.0, 8.62
S3END, NOTCH = 51.0, 43.5  # outer sleeve's rear row; its top V notch apex (|x| = v - NOTCH)


def s1_rear(th):
    return 37.7 + 7.2 * abs(math.cos(th))


def s2_rear(th):
    return 42.4 + 7.0 * abs(math.cos(th))


def s3_rear(th):
    if math.sin(th) <= 0:
        return S3END
    return min(S3END, NOTCH + S3R * abs(math.cos(th)))


def lipf(apex, sweep, off=0.0):
    return lambda th: apex + sweep * abs(math.cos(th)) + off


def mixf(f0, f1, t):
    return lambda th: f0(th) * (1 - t) + f1(th) * t


# Knuckle (ball coupling) half width: inside the outer sleeve, out past its rear as a squat dome
# (rows 51 6.5, 52 5.5, 53 4.5 on the inner mask; ends at row 54).
KNUCKLE = pchip([42.6, 43.6, 45.0, 47.0, 49.0, 50.4, 51.0, 51.6, 52.2, 52.7, 53.2, 53.7, 54.05, 54.3, 54.42],
                [3.8, 5.2, 6.35, 6.9, 7.0, 6.9, 6.75, 6.4, 5.95, 5.45, 4.85, 4.05, 3.0, 1.7, 0.0])
COLLAR = 52.45  # the knuckle's collar groove


def build_spike(M):
    # tip point, insert to the seam, seam groove, nose to the rear cap (hidden in sleeve 1)
    tipv = 14.5
    p = M.point(tipv)
    rows = [14.75, 15.2, 16.0, 16.8, 17.7, 18.6, 19.5, 20.4]
    rings = [M.ring(const(v), SPIKE(v)) for v in rows]
    M.fan(rings[0], p, TIP, 0, rev=True)
    for a, b in zip(rings, rings[1:]):
        M.band(a, b, TIP, 0)
    # seam: the insert's back edge, a shallow V groove, the nose shell
    g0 = M.ring(const(TIP_SEAM - 0.1), SPIKE(TIP_SEAM - 0.1) - 0.05)
    g1 = M.ring(const(TIP_SEAM + 0.1), SPIKE(TIP_SEAM) - 0.32)
    g2 = M.ring(const(TIP_SEAM + 0.3), SPIKE(TIP_SEAM + 0.3))
    M.band(rings[-1], g0, TIP, 0)
    M.band(g0, g1, GROOVE, 0, smooth=False)
    M.band(g1, g2, GROOVE, 0, smooth=False)
    prev = g2
    for v in [22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.5, 33.0, SPIKE_END]:
        r = M.ring(const(v), SPIKE(v))
        M.band(prev, r, NOSE, 0)
        prev = r
    M.fan(prev, M.point(SPIKE_END), NOSE, 0, smooth=False)


def build_sleeve(M, part, mat, R, Ri, apex, sweep, rear, body_rings=5, taper=0.0):
    """A thick-walled telescoping tube: V-cut front lip with a chamfered trim edge, outer skin to the
    rear cut, a small rear chamfer, the inner skin back to the lip. Closed (a torus of quads)."""
    lip = lipf(apex, sweep)
    profile = [  # (vfun, r, band material to the next profile ring, smooth)
        (lipf(apex, sweep, 0.0), Ri, mat, False),            # front face (lip end), inner corner
        (lipf(apex, sweep, 0.0), R - 0.45, TRIM, False),      # chamfer (the lit chevron edge)
        (lipf(apex, sweep, 0.42), R, TRIM, False),
        (lipf(apex, sweep, 0.8), R + taper * 0.1, mat, True),
    ]
    body0 = lipf(apex, sweep, 0.8)
    rear_o = lambda th: rear(th) - 0.25  # noqa: E731
    for k in range(1, body_rings + 1):
        t = k / (body_rings + 1)
        profile.append((mixf(body0, rear_o, t), R + taper * t, mat, True))
    profile.append((rear_o, R + taper, mat, False))
    profile.append((rear, R - 0.3, mat, False))          # rear chamfer
    profile.append((rear, Ri, mat, False))               # rear face to the inner skin
    for t in (0.66, 0.33):  # the hidden inner skin
        profile.append((mixf(lip, rear, t), Ri, mat, True))
    rings = [M.ring(f, r) for f, r, _m, _s in profile]
    for i in range(len(rings)):
        j = (i + 1) % len(rings)
        _f, _r, m, s = profile[i]
        M.band(rings[i], rings[j], m, part, smooth=s)


def build_knuckle(M):
    v0 = 42.6
    p = M.point(v0 - 0.4)
    rows = [v0, 43.8, 45.5, 47.3, 49.0, 50.4, 51.2, 51.8, 52.2]
    rings = [M.ring(const(v), KNUCKLE(v)) for v in rows]
    M.fan(rings[0], p, KNU, 4, rev=True)
    for a, b in zip(rings, rings[1:]):
        M.band(a, b, KNU, 4)
    # collar groove round the dome's shoulder
    g0 = M.ring(const(COLLAR - 0.12), KNUCKLE(COLLAR - 0.12) - 0.35)
    g1 = M.ring(const(COLLAR + 0.12), KNUCKLE(COLLAR + 0.12) - 0.35)
    M.band(rings[-1], g0, GROOVE, 4, smooth=False)
    M.band(g0, g1, GROOVE, 4, smooth=False)
    prev = g1
    for v in [52.75, 53.2, 53.65, 54.0, 54.22]:
        r = M.ring(const(v), KNUCKLE(v))
        M.band(prev, r, KNU, 4)
        prev = r
    # coupling boss: a short stub on the rear face where the first bowl's link pins on
    b0 = M.ring(const(54.3), 1.5)
    M.band(prev, b0, KNU, 4)
    b1 = M.ring(const(54.42), 1.5)
    M.band(b0, b1, GROOVE, 4, smooth=False)
    b2 = M.ring(const(54.42), 0.7)
    M.band(b1, b2, GROOVE, 4, smooth=False)
    M.fan(b2, M.point(54.3), GROOVE, 4, smooth=False)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = []
    for slot in range(8):
        idx = PAL[slot]
        met, rough = KNU_PROPS if slot == KNU else PROPS[idx]
        mats.append(common.palette_material(sprite, idx, f"{TAG}_{slot}", metallic=met, roughness=rough))
    M = Mesh()
    M.kr = KR_SPIKE
    build_spike(M)
    M.kr = KR
    build_sleeve(M, 1, S1, S1R, S1I, S1A, S1W, s1_rear, body_rings=3)
    build_sleeve(M, 2, S2, S2R, S2I, S2A, S2W, s2_rear, body_rings=4)
    build_sleeve(M, 3, S3, S3R, S3I, S3A, S3W, s3_rear, body_rings=5)
    M.kr = KR_BALL
    build_knuckle(M)
    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, coll


# --- pieces (as batch 2's assembly-newshh-45: open cut, the uncut model's normals) ------------------

def split_open(obj, layout):
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:  # close the cut, as common.split_assembly does
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mt in obj.data.materials:
            mesh.materials.append(mt)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def keep_normals(piece, source, cx, cy):
    piece.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    mod = piece.modifiers.new("keep_normals", "DATA_TRANSFER")
    mod.object = source
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "POLYINTERP_NEAREST"
    mod.use_object_transform = True
    bpy.ops.object.select_all(action="DESELECT")
    piece.select_set(True)
    bpy.context.view_layer.objects.active = piece
    bpy.ops.object.modifier_apply(modifier=mod.name)
    piece.location = (0, 0, 0)
    bpy.context.view_layer.update()


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, "newshh-55")
    sprite["colors"].update(common.load_sprite(ROOT, "newshh-17")["colors"])
    obj, coll = build(sprite)
    # the outline shell from the sealed whole model, before any cut (D51, D90, D118)
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=3000, smooth=6, inside=0.006)
    if "--views" in sys.argv:  # review renders (design-stage helper module given by --viewsmod)
        import importlib.util
        spec = importlib.util.spec_from_file_location("views_B", sys.argv[sys.argv.index("--viewsmod") + 1])
        vb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vb)
        vb.run(obj, shell, Path(sys.argv[sys.argv.index("--views") + 1]), PART_NAMES)
    if "--glb" in sys.argv:  # whole-object glb for design review
        common.export_glb([obj, shell], Path(sys.argv[sys.argv.index("--glb") + 1]))
    # assembly layout: the sprite's own, centred on the middle of the 24x56 object
    lay = {e["model"]: (e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES}
    layout = [(n, *lay[n]) for n in PIECES]
    model = obj.copy()
    model.data = obj.data.copy()
    coll.objects.link(model)
    pieces = split_open(model, layout)
    spieces = split_open(shell, [(n + "_o", cx, cy) for n, cx, cy in layout])
    for n, cx, cy in layout:
        keep_normals(pieces[n], obj, cx, cy)
        sp = spieces[n + "_o"]
        sp["tyrian_outline"] = True
        sp.data.materials.clear()
        sp.data.materials.append(bpy.data.materials["outline_shell"])
        sp.data.shade_smooth()
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [pieces[n], sp], f"enemies/{n}", data["sprites"])


if __name__ == "__main__":
    main()
