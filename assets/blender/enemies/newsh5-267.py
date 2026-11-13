"""Cannon bolt (newsh5.shp size 1, frame 267 pointing left and frame 286 pointing right): DREAD-NOT
and TIME WAR cannon shots (enemy types 452/453, launched by 450/451 and 674/675). 

What it is: a hard steel dart fired sideways across the screen. The sprite (12x14, one frame) is a
round grey shaft three px thick running the sprite's width, its nose at the open end (no ink: the
shot is drawn to the sprite's edge), a red-hot band one px behind the nose, and two pairs of white
swept fins standing out flat to either side, a forward pair and a tail pair flush with the blunt
rear end. 286 is 267 mirrored left-right, pixel for pixel, so one geometry serves both.

- Shaft: a solid of revolution on pchip-free explicit stations (it is turned metal: straight runs
  with cut grooves), radius at the sprite's inner mask (D74: 1.45 px against the 1.5 px row band),
  an elliptical bullet nose with a small machined flat, the glowing driving band (pal 116, D126
  glow on metallic 1 / rough 0.85, D173) between two cut grooves, a panel groove between the fin
  pairs, a chamfered tail and a recessed nozzle (pal 8) in the rear face.
- Fins: lofted plan grids traced from the sprite's inner fin rows (front edge, back edge, a round
  tip), a tapered lens section with machined chamfer flats fore and aft, roots buried in the shaft.
- Colours: the trimmed median of each region's sprite pixels (shaft 10, fins 14, band 116; the
  13/120 centre rows are sheen, the 8/11 edge pixels shading).
- Outline shell from a sealed copy (common.outline_shell, D51; islands="outer", D189).

Run:  tools/build-models.sh -j 2 assets/blender/enemies/newsh5-267.py
Exports only enemies/newsh5-267 (newsh5-286.py loads this builder and exports only 286).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy


def find_repo():
    here = Path(__file__).resolve()
    for base in [here, Path.cwd().resolve()]:
        for p in [base] + list(base.parents):
            if (p / "assets" / "blender" / "common.py").exists() and (p / "package.json").exists():
                return p
    raise SystemExit("newsh5-267: can't find the repository (run from inside it)")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_data  # noqa: E402

NAMES = {267: "newsh5-267", 286: "newsh5-286"}
PX = 1 / 12
W, H = 12, 14

# --- Shape (sprite px, the 267 drawing: nose at x = 0, tail at x = 11, y down the sprite) --------
YC, ZC = 5.5, 1.5          # shaft axis: the middle of rows 4-6, resting on the ground plane
R = 1.45                   # shaft radius (the inner band is 1.5 px half-width)
SEG = 32                   # segments round the shaft
G = 1.30                   # groove floor radius
FIN_T0, FIN_T1 = 0.40, 0.20   # fin half-thickness at root and tip
CH_F, CH_B = 0.30, 0.25    # chamfer flats: share of the chord fore and aft
TIP_R = 0.40               # round tip corner radius
# fins: (front edge root/tip x, back edge root/tip x) at y = 4 and y = 2 (their inner rows)
FINS = [((3.0, 4.0), (7.0, 6.0)), ((8.0, 9.0), (10.98, 10.98))]
Y_ROOT, Y_TIP = 4.45, 1.95

GLOW = 2.4                 # band glow strength (palette colour x GLOW, D126)


def stations():
    """(x, r, material key of the segment that starts here, hard edge?) along the shaft."""
    st = []
    n = 9
    for i in range(n):           # elliptical bullet nose with a small flat
        t = i / (n - 1)
        x = 0.02 + 0.98 * (1 - math.cos(0.5 * math.pi * t))
        r = 0.30 + (R - 0.30) * math.sin(0.5 * math.pi * t) ** 0.85
        st.append((x, r, "shaft", i == 0))
    st[0] = (0.0, 0.30, "shaft", True)
    st += [(1.00, R, "shaft", True), (1.03, G, "shaft", True), (1.10, G, "band", True),
           (1.13, R + 0.04, "band", True), (1.87, R + 0.04, "shaft", True), (1.90, G, "shaft", True),
           (1.97, G, "shaft", True), (2.00, R, "shaft", True)]
    for x in (3.0, 4.5, 6.0):
        st.append((x, R, "shaft", False))
    st += [(7.40, R, "shaft", True), (7.44, 1.36, "shaft", True), (7.56, 1.36, "shaft", True),
           (7.60, R, "shaft", True)]
    for x in (8.6, 9.6):
        st.append((x, R, "shaft", False))
    st += [(10.30, R, "shaft", True), (10.92, 1.20, "shaft", True), (11.0, 1.12, "shaft", True),
           (11.0, 0.78, "nozzle", True), (10.72, 0.70, "nozzle", True), (10.72, 0.0, "nozzle", True)]
    return st


def build_shaft(bm, mats):
    st = stations()
    rings = []
    for x, r, key, hard in st:
        if r < 1e-6:
            rings.append([bm.verts.new((x, YC, ZC))])
            continue
        ring = []
        for k in range(SEG):
            a = 2 * math.pi * k / SEG
            ring.append(bm.verts.new((x, YC + r * math.cos(a), ZC + r * math.sin(a))))
        rings.append(ring)
    # flat nose cap
    cap = bm.faces.new(list(reversed(rings[0])))
    cap.material_index = mats["shaft"]
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        key = st[i][2]
        if len(b) == 1:
            for k in range(SEG):
                f = bm.faces.new((a[k], a[(k + 1) % SEG], b[0]))
                f.material_index = mats[key]
            continue
        for k in range(SEG):
            f = bm.faces.new((a[k], a[(k + 1) % SEG], b[(k + 1) % SEG], b[k]))
            f.material_index = mats[key]
    return rings, st


def fin_plan(fin, u, v, flip):
    (f0, f1), (b0, b1) = fin
    y = Y_ROOT + (Y_TIP - Y_ROOT) * u
    s = (4.0 - y) / 2.0                      # 0 at the y = 4 row edge, 1 at y = 2
    xf = f0 + (f1 - f0) * s
    xb = b0 + (b1 - b0) * s
    d = y - Y_TIP
    if d < TIP_R:                            # round the tip corners
        inset = TIP_R - math.sqrt(max(0.0, TIP_R ** 2 - (TIP_R - d) ** 2))
        xf += inset
        xb -= inset if b1 < 10.9 else 0.35 * inset   # the tail fin keeps its square trailing edge
    x = xf + (xb - xf) * v
    return x, (2 * YC - y) if flip else y


def fin_half(u, v):
    t = FIN_T0 + (FIN_T1 - FIN_T0) * u
    bev = min(1.0, v / CH_F, (1 - v) / CH_B)
    tip = min(1.0, (1 - u) / 0.12) if u > 0 else 1.0
    return t * max(0.0, bev) * (0.25 + 0.75 * tip) if u < 1 else 0.0


def build_fin(bm, mats, fin, flip):
    us = [0.0, 0.2, 0.4, 0.6, 0.75, 0.86, 0.93, 0.97, 1.0]
    vs = [0.0, 0.04, 0.12, CH_F, 0.5, 1 - CH_B, 0.9, 0.97, 1.0]
    top, bot = [], []
    for u in us:
        rt, rb = [], []
        for v in vs:
            x, y = fin_plan(fin, u, v, flip)
            h = fin_half(u, v)
            vt = bm.verts.new((x, y, ZC + h))
            vb = vt if h < 1e-7 else bm.verts.new((x, y, ZC - h))
            rt.append(vt)
            rb.append(vb)
        top.append(rt)
        bot.append(rb)
    faces = []
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            q = [top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]]
            p = [bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]]
            for quad in (q, p):
                uq = list(dict.fromkeys(quad))
                if len(uq) >= 3:
                    try:
                        faces.append(bm.faces.new(uq))
                    except ValueError:
                        pass
    # root cap (buried in the shaft)
    ring = top[0] + [v for v in reversed(bot[0]) if v not in top[0]]
    faces.append(bm.faces.new(list(dict.fromkeys(ring))))
    for f in faces:
        f.material_index = mats["fin"]


def build_geometry(mats):
    bm = bmesh.new()
    build_shaft(bm, mats)
    for fin in FINS:
        for flip in (False, True):
            build_fin(bm, mats, fin, flip)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return bm


def to_model(bm, mirror):
    """Sprite px (267 drawing) -> model units; mirror: the 286 drawing (x -> 12 - x)."""
    for v in bm.verts:
        x, y, z = v.co
        if mirror:
            x = W - x
        v.co = ((x - W / 2) * PX, (H / 2 - y) * PX, z * PX)
    if mirror:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    seal_and_orient(bm)


def face_islands(bm):
    """Groups of faces connected through shared edges."""
    seen, out = set(), []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        out.append(isl)
    return out


def seal_and_orient(bm):
    """Fill the slit holes left where zero-thickness fin tip rows meet, make normals consistent per
    island, then reverse any island whose signed volume is negative (inside out)."""
    open_edges = [e for e in bm.edges if e.is_boundary]
    if open_edges:
        bmesh.ops.holes_fill(bm, edges=open_edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.index_update()
    for isl in face_islands(bm):
        vol = 0.0
        for f in isl:
            vs = [v.co for v in f.verts]
            for k in range(1, len(vs) - 1):
                vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6.0
        if vol < 0:
            bmesh.ops.reverse_faces(bm, faces=isl)


def mark_sharp(mesh, angle=35.0):
    try:
        mesh.set_sharp_from_angle(angle=math.radians(angle))
    except AttributeError:
        pass


# --- Sprite -------------------------------------------------------------------------------------

def load(name):
    """The frame read straight from the game data with tools/sprite_data.py (newsh5.shp size 1,
    palette 5): the catalogue has no reference/models folder for this unit."""
    return sprite_data.load(ROOT, name, "newsh5.shp", [int(name.split("-")[1])], size=1)


# --- Build ----------------------------------------------------------------------------------------

def build(frame):
    name = NAMES[frame]
    sprite = load(name)
    coll = common.reset_collection(name)
    pm = common.palette_material
    m_shaft = pm(sprite, 10, name, metallic=0.55, roughness=0.36)
    m_fin = pm(sprite, 14, name, metallic=0.35, roughness=0.40)
    m_band = pm(sprite, 116, name, metallic=1.0, roughness=0.85, emission_strength=GLOW)
    m_noz = pm(sprite, 8, name, metallic=0.5, roughness=0.6)
    for m in (m_shaft, m_fin):
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.7   # satin steel F0 (D176)
    slots = {"shaft": 0, "fin": 1, "band": 2, "nozzle": 3}
    bm = build_geometry(slots)
    to_model(bm, mirror=frame == 286)
    for f in bm.faces:
        f.smooth = True
    obj = common.mesh_object(name, bm, [m_shaft, m_fin, m_band, m_noz], coll, smooth=None)
    mark_sharp(obj.data)
    shell = common.outline_shell(obj, coll, voxel=0.005, faces=1600, smooth=3, islands="outer")
    shell.name = shell.data.name = f"{name}_outline"
    obj.name = obj.data.name = name
    common.frame_part(obj, [frame])
    common.frame_part(shell, [frame])
    return sprite, [obj, shell]


def export(frame):
    """Build one frame's model and export it (public/models/enemies/<name>.glb + its spriteModels JSON)."""
    sprite, objs = build(frame)
    name = NAMES[frame]
    common.export_sprite_model(ROOT, objs, f"enemies/{name}", sprite["sprites"])
    return sprite, objs


def main():
    export(267)


if __name__ == "__main__":
    main()
