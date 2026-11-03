"""Tall buildings and structures (DECISIONS.md D68, docs/agents/TALL-BUILDINGS.md): a structure whose
tiles draw a roof with a wall painted below it, built as a real 3D building and drawn the way its
tiles draw it.

Tyrian's art draws tall buildings in a fixed oblique view: the roof, and under it the south wall,
as if seen from above and in front. The game camera can't see that much wall: at 15° a vertical wall
shows 0.31 px per px of height at mid-screen, and from 0.72 at the screen's top to -0.09 at its
bottom, and the pass stack leaves a ground structure 0.8 units (D5). A model fitted to the whole
sprite from straight above stretches the roof over the wall or turns the wall into a ramp; a model
of the real height drifts tens of px off its tiles as it scrolls. So (`TallBuilding`):

- `tools/tall_buildings.py` splits the tiles: the building's pixels, the roof/wall edge, the painted
  wall band (`shift`, px) and each column's foot, and says whether the structure counts as tall;
- the building stands on its **footprint**: the roof outline moved down to the foot of the painted
  wall (where the wall meets the ground);
- its walls are vertical and it is as tall as the painted wall band, one px of height per px of
  wall; the south wall wears the painted wall's pixels row for row and the roof the roof's, each as
  a low relief by brightness, in palette materials (`block`);
- `export` marks it `tyrian_oblique` (px up the screen per px of height: 1) and `tyrian_depth_band`
  (DEPTH_BAND): the renderer (src/render/remaster/structureInstances.ts) puts every vertex on the
  camera ray through the point the art draws it at, with the depth of a copy squeezed into the band.
  The roof and the wall land exactly where the tiles paint them at every tilt and scroll position,
  everything the original drew over the tiles still draws over the building, and normals, light and
  shadows are the real building's;
- on the ground the tiles stay drawn under it (keepTiles, as for every layer-0 structure): the model
  covers the painted building exactly, so they only show round it.

`lean` (Y per unit of height) tips the walls back; only the experiment's variants used it (B: fit the
15° camera within the pass budget; C0: fit it at full height). Not done here: a building on layer
2 (it replaces its tiles, so it must carry the island rock, D63, which must not take the oblique
view); buildings whose roof edge steps (the split takes one wall band for the whole pattern).

Units and frame as lib_tiles: 1 unit = 12 px, origin at the pattern's centre, X right, Y up the
screen, Z up, z = 0 the layer's plane.
"""

import sys
from pathlib import Path

import bmesh
import numpy as np

import common
import lib_tiles as lt

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import tall_buildings as tbm  # noqa: E402

PX = lt.PX
#: The depth band (model units above its base) a tall building's depth is squeezed into, per layer:
#: under the next pass the original draws over that layer (D5). On the ground, background 2's
#: under pass at 0.05 (SAVARA's clouds: higher, a building hides them); on background 3 (at 2.1),
#: the top enemies at 2.5 (whose models start about 0.4 above it, as lib_tyrbld's L2_OVER_MAX).
DEPTH_BAND = {0: (0.0, 0.04), 1: (0.0, 0.3), 2: (0.0, 0.38)}
#: How far the brightest roof pixel stands over the darkest (units).
ROOF_RELIEF = 0.05
#: How far the brightest wall pixel stands out of the wall over the darkest (units).
WALL_RELIEF = 0.06
#: The game camera's wall per height at mid-screen, 15° (tools/tall_buildings.py CAMERAS).
S_TILTED = 0.314


class TallBuilding:
    """One building pattern. `ground`: the ground's palette ramps (default: the pattern's border's)."""

    def __init__(self, shapes, pattern, layer=0, ground=None, tag="tall"):
        self.ts = lt.Tileset(ROOT, shapes, layer)
        self.pattern = pattern
        self.layer = layer
        self.height_px = None
        self.grid = self.ts.grid(pattern)
        self.frame = lt.Frame(pattern)
        self.s = tbm.split(self.grid, self.ts.colors, ground)
        self.shift = int(round(self.s["wall_px"]))
        self.pal = lt.Palette(self.ts, tag, roughness=0.75, metallic=0.05)
        b = self.s["building"]
        h, w = b.shape
        self.cols = [x for x in range(w) if self.s["foot"][x] >= 0]
        # One edge for the whole building, `shift` px above each column's foot (columns the split
        # left without an edge, such as a lit side face, take the same).
        self.edge = {x: self.s["foot"][x] - self.shift for x in self.cols}
        self.roof = np.zeros_like(b)
        for x in self.cols:
            self.roof[self.s["top"][x]:max(self.s["top"][x], self.edge[x]), x] = True
        self.roof &= b
        self.plan = np.zeros_like(b)
        ys, xs = np.nonzero(self.roof)
        keep = ys + self.shift < h
        self.plan[ys[keep] + self.shift, xs[keep]] = True
        lum = self.ts.lum[np.clip(self.grid, 0, 255)]
        self.lum = np.where(self.grid >= 0, lum, 0)
        self.wall_index = int(np.median(self.grid[self.s["wall"]])) if self.s["wall"].any() else 1

    # --- parts ----------------------------------------------------------------------------------

    def block(self, height_px=None, lean=0.0, name="tall_block"):
        """The building: a prism on the footprint, `height_px` tall (default the wall band), its
        roof the roof's pixels and its south wall the wall's, row for row; walls tipped back by
        `lean`. Returns the object."""
        hpx = self.shift if height_px is None else height_px
        self.height_px = hpx
        top = hpx * PX
        pal, grid, plan = self.pal, self.grid, self.plan
        rel = self._relief(self.roof, ROOF_RELIEF)
        heights = np.zeros(plan.shape)
        ys, xs = np.nonzero(plan)
        heights[ys, xs] = rel[ys - self.shift, xs]
        wall_mat = pal(self.wall_index)
        bm = bmesh.new()
        lt.mask_slab(bm, plan, self.frame, 0.0, top,
                     lambda x, y: pal(grid[y - self.shift, x]), wall_mat, top_height=heights, smooth_top=False)
        # The facade replaces the plain south wall (two surfaces so close would fight for depth in
        # a squeezed depth band).
        bm.normal_update()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y < -0.9], context="FACES")
        self._facade(bm, top)
        for v in bm.verts:
            v.co.y += lean * v.co.z
        lt.dissolve_coplanar(bm)
        return mesh_object(name, bm, pal)

    def _relief(self, mask, amp):
        """Each pixel's relief by its brightness within `mask` (0 darkest .. amp brightest)."""
        vals = self.lum[mask]
        if len(vals) == 0:
            return np.zeros(mask.shape)
        lo, hi = np.percentile(vals, 5), np.percentile(vals, 95)
        return np.clip((self.lum - lo) / max(1e-6, hi - lo), 0, 1) * amp

    def _facade(self, bm, top):
        """The painted wall on the footprint's south side, one row of quads per painted wall row,
        standing out by its brightness a little in front of the plain wall mask_slab made."""
        grid, frame, pal = self.grid, self.frame, self.pal
        rel = self._relief(self.s["wall"], WALL_RELIEF)
        n = self.shift
        h, w = grid.shape
        cols = [x for x in self.cols if self.plan[:, x].any()]
        if not cols or n <= 0:
            return
        # The facade of each column sits at that column's foot (the plan's south edge).
        south = {x: int(np.nonzero(self.plan[:, x])[0].max()) + 1 for x in cols}
        verts = {}

        def px_rel(x, j):
            y = self.edge[x] + j
            return rel[y, x] if 0 <= y < h and self.s["building"][y, x] else 0.0

        def vert(cx, j):
            # Corner between columns cx-1 and cx, rows j-1 and j: the mean relief of its pixels, at
            # the south edge of the column it belongs to (the left one at a step).
            key = (cx, j)
            if key in verts:
                return verts[key]
            owners = [x for x in (cx - 1, cx) if x in south]
            vals = [px_rel(x, jj) for x in owners for jj in (j - 1, j) if 0 <= jj < n]
            out = 0.004 + (sum(vals) / len(vals) if vals else 0.0)
            sy = min(south[x] for x in owners)
            z = top - j * top / n
            v = bm.verts.new((frame.x(cx), frame.y(sy) - out, z))
            verts[key] = v
            return v

        for x in cols:
            for j in range(n):
                y = self.edge[x] + j
                index = grid[y, x] if 0 <= y < h and self.s["building"][y, x] else self.wall_index
                f = bm.faces.new((vert(x, j + 1), vert(x + 1, j + 1), vert(x + 1, j), vert(x, j)))
                f.material_index = pal(index)

    def export(self, objects, name, min_rows=None):
        """Mark the objects for the renderer (the oblique view, k = wall band / height, and the layer's
        depth band) and export them with their tileModels entry (keepTiles on the ground; `min_rows`
        when the tiles also make other walls and buildings)."""
        import json
        oblique(objects, self.shift / (self.height_px or self.shift))
        depth_band(objects, self.layer)
        out = lt.export_tile_model(self.ts, objects, name, self.layer, self.pattern, keep_tiles=True if self.layer == 0 else False)
        if min_rows is not None:
            path = ROOT / "src" / "render" / "tileModels" / f"{self.ts.name}-{name}.json"
            entry = json.loads(path.read_text())
            entry["minRows"] = int(min_rows)
            path.write_text(json.dumps(entry, indent=1) + "\n")
        return out


def mesh_object(name, bm, pal):
    """common.mesh_object without its normal recalculation: the facade is an open sheet whose
    winding is set where it is built (recalc_face_normals may flip such a sheet)."""
    import bpy
    coll = common.reset_collection(name)
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    for mat in pal.materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def depth_band(objects, layer, band=None):
    """Mark the objects so the renderer squeezes their depth into `band` (default the layer's
    DEPTH_BAND; module docstring)."""
    for o in objects:
        o["tyrian_depth_band"] = list(band or DEPTH_BAND[layer])


def oblique(objects, k=1.0):
    """Mark the objects so the renderer draws them in the art's oblique view: `k` px up the screen
    per px of height (module docstring)."""
    for o in objects:
        o["tyrian_oblique"] = float(k)
