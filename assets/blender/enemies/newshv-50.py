"""Pale violet crystal shard (newshv.shp frame 50) (merged with newshv-12, its mirror): a pale violet crystal shard flying
point first, up and to the left (newshv-12: up and to the right).

What it is: a free-flying faceted crystal (the same crystal as newshv-10, turned 45 degrees): a
twelve-sided prism with a crisp crest along its top (three facets a flank, kinked along the
length), a long pyramidal point, a recessed growth seam and a short faceted base cap. Closed all round (it flies free; the underside is the same faceted
crystal mirrored, no detail).

Plan: lofted along the sprite's 45-degree symmetry line (the inner mask is exactly symmetric about
it). Stations s (px along the axis from the inner mask's corner at column edge 2, row edge 6) and
half widths w (px across) were fitted to the inner mask (fit/opt3.py, fit/hand.py: grid IoU 1.0 on
the profile alone). The seam sits where the sprite draws its dark line (s ~ 17.7: pixels 86-89 at
rows 16-21), and its 0.35 px notch is the notch in the sprite's outline there.

Colours (median of each region's sprite pixels, fit/col.py): body 92 (lit facet 93 / shaded 89 is
lighting), seam 89, base cap 91.

newshv-12.py is this script mirrored (MIRROR = True): change both together.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshv-50.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshv-50"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
R2 = math.sqrt(2)
SW, SH = 24, 28  # sprite block, px

# (s, w) stations along the axis. k = half height / half width of the section there.
TIP = [(-0.9, 0.0), (0.4, 0.62), (9.5, 5.3)]          # pyramidal point (termination)
PRISM = [(9.5, 5.3), (12.6, 5.95), (15.4, 6.2), (17.4, 5.1)]  # body: prism and its shoulder
GROOVE = [(17.4, 5.1), (17.48, 4.75), (18.12, 4.75), (18.2, 5.45)]  # recessed growth seam
CAP = [(18.2, 5.45), (19.4, 5.3), (21.6, 3.6), (22.9, 1.0), (23.25, 0.0)]  # base cap
K_BODY = 0.78    # crest half height / half width (prism)
K_CAP = 0.66
# Section, one quarter (x across / w, z up / (k w)), side vertex to crest: a steep flank facet, a
# mid facet and the crest facet (convex: the slopes fall toward the crest), so the crest is a
# crisp ridge and each flank breaks into three lit planes. Mirrored to the other side and below.
QUARTER = [(1.0, 0.0), (0.86, 0.30), (0.56, 0.62), (0.0, 1.0)]
# Facet breaks along the prism: the crest rises and falls a touch between stations (the plan's
# edge, the side vertices, does not move), so the long facets kink like a grown crystal's.
CREST = {9.5: 1.07, 12.6: 0.96, 15.4: 1.05, 17.4: 0.94}
CHAMFER = 0.018  # units: small chamfer on the facet edges (sheen lines, not paint)
GROW = 0.12      # px: puts back what the chamfer takes off the plan's side vertices
MIRROR = False   # newshv-12 is this crystal mirrored in x (pointing up-right)


def to_world(s, w, z):
    """Axis frame (px) -> Blender units. Column c = 2 + (s + w)/sqrt2, row r = 6 + (s - w)/sqrt2."""
    c = 2 + (s + w) / R2
    r = 6 + (s - w) / R2
    if MIRROR:
        c = SW - c
    return ((c - SW / 2) * PX, (SH / 2 - r) * PX, z * PX)


def section():
    """The closed 12-vertex section, counter-clockwise from the +w side vertex."""
    up = QUARTER + [(-x, z) for x, z in reversed(QUARTER[:-1])]  # +w .. crest .. -w
    down = [(x, -z) for x, z in reversed(up[1:-1])]             # under the -w side .. +w
    return up + down


def ring(bm, s, w, h, crest=1.0):
    """One section at station s: half width w, half height h; `crest` lifts the top ridge only."""
    if w <= 1e-6:
        return [bm.verts.new(to_world(s, 0.0, 0.0))]
    out = []
    w = w + GROW if w > 1 else w
    for x, z in section():
        zz = h * z * (crest if z > 0.99 else 1.0 + (crest - 1.0) * 0.5 if z > 0.5 else 1.0)
        out.append(bm.verts.new(to_world(s, w * x, zz)))
    return out


def bridge(bm, r0, r1, mat):
    faces = []
    n = max(len(r0), len(r1))
    for k in range(n):
        j = (k + 1) % n
        if len(r0) == 1:
            f = bm.faces.new((r0[0], r1[k], r1[j]))
        elif len(r1) == 1:
            f = bm.faces.new((r0[k], r1[0], r0[j]))
        else:
            f = bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
        f.material_index = mat
        faces.append(f)
    return faces


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(92, metallic=0.15, roughness=0.36),  # 0 crystal body
        pal(89, metallic=0.1, roughness=0.55),   # 1 growth seam (recessed)
        pal(91, metallic=0.15, roughness=0.4),  # 2 base cap
    ]
    BODY, SEAM, CAPM = 0, 1, 2
    bm = bmesh.new()

    stations = []  # (s, w, k, mat of the band that ends here)
    for s, w in TIP:
        stations.append((s, w, K_BODY, BODY))
    for s, w in PRISM[1:]:
        stations.append((s, w, K_BODY, BODY))
    for s, w in GROOVE[1:]:
        k = K_BODY if s < 18.15 else K_CAP
        stations.append((s, w, k, SEAM if s < 18.15 else SEAM))
    for s, w in CAP[1:]:
        stations.append((s, w, K_CAP, CAPM))

    rings = []
    for s, w, k, _ in stations:
        # the seam's floor is a touch flatter than the prism (a cut groove, not a pinch)
        rings.append(ring(bm, s, w, w * k, crest=CREST.get(s, 1.0)))
    for i in range(1, len(rings)):
        bridge(bm, rings[i - 1], rings[i], stations[i][3])

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # Chamfer the long facet edges and the band edges (hard surface: crisp, with a sheen line)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9)]
    bmesh.ops.bevel(bm, geom=edges, offset=CHAMFER, offset_type="OFFSET", segments=1,
                    profile=0.5, affect="EDGES", clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return obj, coll


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj, coll = build(sprite)
    # D90/D118: shell from a sealed copy (the crystal is closed already), held a hair inside.
    shell = common.outline_shell(obj, coll, voxel=0.015, faces=2500, inside=0.004)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"triangles {tris} (model), shell faces {len(shell.data.polygons)}")
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
