"""Green crystal pod (newshv.shp size 2, frames 191/193/195), (D65 hard surface, D122 identity).

IDENTITY: a LAUNCHED projectile/mine, not a ground object. Type 803 moves mv(0,1), animates (ani16)
and fires (launch3); the GEM WAR gunship's centre piece (type 808, the one wearing the green gem)
launches it every 60 ticks, and it has no level spawn events of its own (level 2.7). So it is built
free-flying: a faceted gem with a round, closed underside, nothing standing on the ground.

Reading of the sprite (24x28; the gem fills cols 4-19 x rows 6-21 inside a one-pixel ink ring of 32,
centre at pixel edge (12, 14) = the model origin; every inner pixel centre lies within 8.5 px of it,
every outside one beyond 8.75: a round girdle of radius 8.6 px):
- the pale table in the middle (rows 13-15, cols 10-15: 45-47, the brightest of the gem);
- a diamond of dark notches at the four compass points about 5 px out (N rows 8-10, E/W rows 13-14,
  S rows 17-19: 37-40): the cardinal star facets of a brilliant cut, tipped away from the light;
- bright spots on the four diagonals at the same radius (46/47): the diagonal star facets;
- a mid-green rim (38-43) all round: the upper girdle facets running down to the girdle.
So it is a round brilliant: octagonal table, 8 star facets, 8 kite (bezel) facets, 16 upper girdle
facets, a faceted girdle band, and a pavilion that closes underneath in a round, blunt culet.
Each crown facet takes the sprite's own palette index: the median of the sprite pixels its top view
covers (sampled on a 4x4 subgrid per pixel), with the darkest and brightest sixth of them dropped
(lighting). The girdle band takes the rim's median; the pavilion two steps darker (underside).

Animation: frames 193 and 195 are the same drawing two and four palette steps darker (down to the
ink's 32), a pulse: one model, every material steps down the same way (palette_material frames=).

Material: a gem, so glossy sheen (low roughness, no metal), crisp chamfered facet edges to catch
it; the table glows at its own colour (strength 1, D126: the pale table reads as in the sprite),
the bright crown facets faintly (crystal light), the rest lit. No bake: a convex gem gets nothing
from AO (no textures/newshv-191 folder; nothing to add one for).

  Blender -b -P assets/blender/enemies/newshv-191.py [-- --preview out.png] [--frames frames.png]
Exports public/models/enemies/newshv-191.glb and src/render/spriteModels/newshv-191.json.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
WT = Path(__file__).resolve().parents[3]
import common  # noqa: E402

NAME = "newshv-191"
TAG = "nshv191"
PX = 1 / 12
W, H = 24, 28
FRAMES = (191, 193, 195)
FADE = {193: 2, 195: 4}  # palette steps darker on each later frame (32 is the darkest green)

# Geometry, in sprite px (scaled by PX at the end). Origin = sprite centre, girdle mid-plane z=0.
R = 8.62        # girdle radius (inner mask: centres <= 8.51 in, >= 8.75 out)
ZG = 0.55       # half the girdle band's height (at the rim facets' feet)
CROWN = 3.9     # table height above the girdle top: reads as a raised gem at the 32 deg game tilt
ZT = ZG + CROWN
# The crown is cut like a real stone: a closed blank (girdle cylinder + pavilion) sliced by facet
# planes, so every facet is flat and the crown convex. Plane layout fitted to the sprite's colour
# regions (fit2.py: lowest per-facet spread of sprite indices of the layouts tried):
TC = 4.0        # cardinal notch planes leave the table this far out (the table's cardinal flats)
TD = 2.5        # diagonal frame planes leave the table this far out (the dark diamond frame)
FE = 4.25       # frame -> bright facet break on the diagonals
BE = 6.25       # where the rim (upper girdle) facets begin
AF = 20.0       # frame slope (deg)
ZR = ZT - 0.42 * CROWN  # height of the rim facets' top edge
# pavilion profile (radius, z) below the girdle: a round, blunt bowl closing at the culet
PAV = [(R, -ZG), (R * 0.965, -1.6), (R * 0.87, -2.9), (R * 0.70, -4.2), (R * 0.48, -5.3),
       (R * 0.25, -6.0), (R * 0.08, -6.3)]
ZBOT = -6.35
PAV_G = 62.0    # lower girdle facet slope (deg, downward)
PAV_M = 40.0    # pavilion main slope
NG = 32         # girdle segments
BEVEL = 0.14    # facet-edge chamfer (px)


def crown_planes():
    """(name, azimuth deg, d0, z0, slope deg): the plane leaves height z0 at distance d0 from the
    axis along the azimuth and falls outward at the slope (0 = the flat table)."""
    t = math.tan
    zf = ZT - (FE - TD) * t(math.radians(AF))
    ab = math.degrees(math.atan((zf - ZR) / (BE - FE)))
    an = math.degrees(math.atan((ZT - ZR) / (BE - TC)))
    ar = math.degrees(math.atan((ZR - ZG) / (R - BE)))
    pl = [("table", 0, 0, ZT, 0)]
    for k in range(4):
        pl.append((f"frame{k}", 45 + 90 * k, TD, ZT, AF))
        pl.append((f"bright{k}", 45 + 90 * k, FE, zf, ab))
        pl.append((f"notch{k}", 90 * k, TC, ZT, an))
    for k in range(16):
        pl.append((f"rim{k}", 11.25 + 22.5 * k, R, ZG, ar))
    return pl


def pavilion_planes():
    """The underside's facets (same form, slope measured downward): 16 lower girdle facets under
    the girdle, 8 pavilion mains below them; the blank's round bowl is left as a blunt culet."""
    pl = []
    for k in range(16):
        pl.append((f"pf_g{k}", 11.25 + 22.5 * k, R, -ZG, -PAV_G))
    for k in range(8):
        pl.append((f"pf_m{k}", 45 * k, R, -ZG - 1.3, -PAV_M))
    return pl


# palette index -> (metallic, roughness, emission strength)
def look(i, part):
    if part == "table":
        return 0.0, 0.12, 0.5
    if part == "crown":
        return 0.05, 0.16, 0.22 if i >= 45 else 0.1
    if part == "band":
        return 0.05, 0.22, 0.08
    return 0.05, 0.3, 0.05  # pavilion


def ang(deg):
    return math.radians(deg)


def ring_pt(r, deg, z):
    a = ang(deg)
    return Vector((r * math.cos(a), r * math.sin(a), z))


def build_mesh():
    """The gem as a bmesh in px units; faces carry a 'facet' int layer (name in the returned list)."""
    bm = bmesh.new()
    lay = bm.faces.layers.int.new("facet")
    names = ["band", "pav_hi", "pav_lo"]

    def tag(f, name):
        if name not in names:
            names.append(name)
        f[lay] = names.index(name)

    top = ZT + 2.0
    Gt = [bm.verts.new(ring_pt(R, 360 / NG * j, top)) for j in range(NG)]
    # pavilion: rings offset half a segment per tier (lower girdle / pavilion main look), smooth
    rings = [Gt]
    for t, (r, z) in enumerate(PAV):
        off = (t % 2) * 360 / NG / 2 if t else 0
        rings.append([bm.verts.new(ring_pt(r, 360 / NG * j + off, z)) for j in range(NG)])
    for t in range(len(rings) - 1):
        a, b = rings[t], rings[t + 1]
        nm = "band" if t == 0 else ("pav_hi" if t < 3 else "pav_lo")
        if t == 0:
            for j in range(NG):
                tag(bm.faces.new([a[j], b[j], b[(j + 1) % NG], a[(j + 1) % NG]]), nm)
            continue
        shifted = t % 2 == 1  # ring t+1 sits half a segment ahead of ring t
        for j in range(NG):
            j1 = (j + 1) % NG
            if shifted:
                tag(bm.faces.new([a[j], b[j], a[j1]]), nm)
                tag(bm.faces.new([a[j1], b[j], b[j1]]), nm)
            else:
                tag(bm.faces.new([a[j], b[j], b[j1]]), nm)
                tag(bm.faces.new([a[j], b[j1], a[j1]]), nm)
    culet = bm.verts.new((0, 0, ZBOT))
    last = rings[-1]
    for j in range(NG):
        tag(bm.faces.new([last[j], culet, last[(j + 1) % NG]]), "pav_lo")
    tag(bm.faces.new(list(reversed(Gt))), "blank")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # cut the crown, facet by facet
    for name, phi, d0, z0, slope in crown_planes() + pavilion_planes():
        a = math.radians(abs(slope))
        up = 1 if slope >= 0 else -1
        u = Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi)), 0))
        no = Vector((u.x * math.sin(a), u.y * math.sin(a), up * math.cos(a)))
        co = u * d0 + Vector((0, 0, z0))
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and len(e.link_faces) == 1]
        if not cut:
            continue
        made = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
        for f in made:
            tag(f, name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    left = [f for f in bm.faces if names[f[lay]] == "blank"]
    if left:
        raise RuntimeError(f"{len(left)} blank faces left above the crown")
    return bm, lay, names


def sample_facets(bm, lay, names, sprite_px):
    """Sprite palette indices under each facet's top view (4x4 subsamples per pixel)."""
    tree = BVHTree.FromBMesh(bm)
    bm.faces.ensure_lookup_table()
    got = {n: [] for n in names}
    for r in range(H):
        for c in range(W):
            v = sprite_px[r][c]
            if v < 0:
                continue
            for sj in range(4):
                for si in range(4):
                    x = c + (si + 0.5) / 4 - W / 2
                    y = H / 2 - (r + (sj + 0.5) / 4)
                    hit = tree.ray_cast(Vector((x, y, 50)), Vector((0, 0, -1)))
                    if hit[0] is None:
                        continue
                    got[names[bm.faces[hit[2]][lay]]].append(v)
    return got


def trimmed_median(vals):
    v = sorted(vals)
    k = len(v) // 6
    core = v[k:len(v) - k] or v
    return core[len(core) // 2]


def part_of(name):
    if name == "table":
        return "table"
    if name == "band":
        return "band"
    if name.startswith("pav") or name.startswith("pf_"):
        return "pav"
    return "crown"


def build(sprite, coll):
    bm, lay, names = build_mesh()
    names_used = [names[i] for i in sorted({f[lay] for f in bm.faces})]
    f191 = sprite["frames"][0]["pixels"]
    got = sample_facets(bm, lay, names, f191)
    ink = 32
    index = {}
    for n in names_used:
        vals = [v for v in got[n] if v > ink]
        if vals:
            index[n] = trimmed_median(vals)
    # band: the rim's median (inner pixels beyond 7 px from the centre)
    rim = []
    for r in range(H):
        for c in range(W):
            v = f191[r][c]
            if v > ink and math.hypot(c + 0.5 - W / 2, H / 2 - r - 0.5) > 7.0:
                rim.append(v)
    index["band"] = trimmed_median(rim)
    for n in names_used:
        if n in ("pav_hi", "pav_lo") or n.startswith("pf_m"):
            index[n] = index["band"] - 2
        elif n.startswith("pf_g"):
            index[n] = index["band"] - 1
    # materials: one per (index, part)
    mats, slot = [], {}
    for n in names_used:
        key = (index[n], part_of(n))
        if key in slot:
            continue
        i, part = key
        met, rough, em = look(i, part)
        m = common.palette_material(sprite, i, f"{TAG}-{part}", metallic=met, roughness=rough,
                                    emission_strength=em,
                                    frames={f: max(i - d, 32) for f, d in FADE.items()})
        slot[key] = len(mats)
        mats.append(m)
    for f in bm.faces:
        n = names[f[lay]]
        f.material_index = slot[(index[n], part_of(n))]
        f.smooth = n in ("pav_hi", "pav_lo")
    # chamfer the crown's facet edges and the girdle's two edges (hard, crisp sheen lines)
    hard = [e for e in bm.edges if len({f[lay] for f in e.link_faces}) > 1
            and not all(names[f[lay]] in ("pav_hi", "pav_lo") for f in e.link_faces)]
    bmesh.ops.bevel(bm, geom=hard, offset=BEVEL, offset_type="OFFSET", segments=1, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    for v in bm.verts:
        v.co *= PX
    me = bpy.data.meshes.new(TAG)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # sharp crown/girdle edges, smooth pavilion
    me.set_sharp_from_angle(angle=math.radians(25))
    report = {n: {"index": index[n], "px": len(got[n])} for n in names_used}
    return obj, report


# --- measurement and views (scratch) ---------------------------------------------------------------


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj, _report = build(sprite, coll)
    # the outline shell from a sealed copy (the gem is one closed solid; D51, D90/D118)
    sealed = bpy.data.objects.new(f"{NAME}_sealed", obj.data.copy())
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(sealed, coll, voxel=0.012, faces=1200, smooth=6, inside=0.003)
    sh.name = f"{NAME}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    bpy.context.view_layer.update()
    objs = [obj, sh]
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = WT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])
    if "--frames" in sys.argv:
        common.render_frame_previews(objs, sys.argv[sys.argv.index("--frames") + 1], sprite, WT)


if __name__ == "__main__":
    main()
