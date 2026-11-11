"""tools/terrain_hd.py across several levels of one tileset (DECISIONS.md D83): the merge keeps the
atlas's tiles byte for byte and the seams of the new tiles hold.

Needs the game data (TYRIAN_DATA, default data/) and numpy, scipy and PIL; run through
tests/tools/terrainHd.test.ts, or directly:
    TYRIAN_DATA=... python -m unittest tests/tools/terrain_hd_test.py

No Gemini and no registration: the cut reads a candidates cache made here (each tile's original
upscaled smoothly, with its own brightness offset and noise, so there are seams to solve), and the
base atlas is a copy of the committed public/art/terrain/shapesz (TYRIAN, D59/D60).
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import terrain_hd as th  # noqa: E402

DATA = Path(os.environ.get("TYRIAN_DATA", ROOT / "data"))
ART = ROOT / "public/art/terrain/shapesz"
LEVELS = ["1-9", "1-11", "1-16"]  # TYRIAN (all kept), HOLES and ASSASSIN (new ground and layer-2 rock)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def level1_atlas(d: Path) -> None:
    """Trim the atlas folder `d` to the tiles TYRIAN's map (1-9) draws, removing images no rect uses."""
    L = th.TilesetData(DATA, ["1-9"]).level("1-9")
    models = th.load_models("shapesz.dat")
    man = json.loads((d / "manifest.json").read_text())
    for layer_s in list(man["layers"]):
        g, drawn, _ = th.layer_masks(L, int(layer_s), models)
        used = {str(int(n)) for n in np.unique(g[drawn])}
        lay = man["layers"][layer_s]
        lay["tiles"] = {k: r for k, r in lay["tiles"].items() if k in used}
        if not lay["tiles"]:
            del man["layers"][layer_s]
    refs = {lay["image"] for lay in man["layers"].values()}
    refs |= {r["image"] for lay in man["layers"].values() for r in lay["tiles"].values() if "image" in r}
    for f in d.glob("*.webp"):
        if f.name not in refs:
            f.unlink()
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")


def fake_candidates(T: th.TilesetData, inv: dict, seed: int = 3) -> dict:
    """One stand-in painting per tile that needs art: the original upscaled bicubic to 8 texels per
    pixel, a per-tile brightness offset of up to +-14 levels, and noise."""
    rng = np.random.default_rng(seed)
    out = {}
    for layer_s, d in inv["layers"].items():
        layer = int(layer_s)
        for t in d["tiles"].values():
            if not th.needs_paint(t, layer, reuse=False):
                continue
            n = t["tile"]
            rgb = T.rgb[T.tile(n)]
            hd = np.asarray(Image.fromarray(rgb).resize((th.TILE_W * th.SCALE, th.TILE_H * th.SCALE), Image.BICUBIC)).astype(np.float32)
            hd = (hd + rng.uniform(-14, 14) + rng.normal(0, 3, hd.shape)).clip(0, 255)
            out[(layer, n)] = [{"hd": hd, "ncc": 0.9, "cellScore": 0.9, "err": 0.02, "interior": 2, "sheet": "region-fake", "cell": 0,
                                "blocky": 1.2, "novel": 0.0, "score": 0.9, "fit": {}}]
    return out


@unittest.skipUnless((DATA / "tyrian1.lvl").exists() and (DATA / "shapesz.dat").exists() and (ART / "manifest.json").exists(),
                     "needs the game data and the committed shapesz atlas")
class MergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="terrain-hd-test-"))
        cls.out = cls.tmp / "out"
        shutil.copytree(ART, cls.out / "shapesz")
        # The committed atlas covers every level of the tileset (D86); the merge is tested from
        # level 1's part of it, so HOLES and ASSASSIN have new tiles to cut.
        level1_atlas(cls.out / "shapesz")
        cls.before = {f.name: sha(f) for f in (cls.out / "shapesz").iterdir()}
        cls.old_manifest = json.loads((cls.out / "shapesz/manifest.json").read_text())
        cls.work = cls.tmp / "work"
        args = ["--data", str(DATA), "--level", ",".join(LEVELS), "--work", str(cls.work)]
        th.main(args + ["inventory", "--out", str(cls.out)])
        cls.inv = json.loads((cls.work / "inventory.json").read_text())
        cls.T = th.TilesetData(DATA, LEVELS)
        (cls.work / "sheets").mkdir(parents=True, exist_ok=True)
        (cls.work / "sheets/manifest.json").write_text(json.dumps({"sheets": []}))
        cache = cls.work / "cands.pkl"
        cache.write_bytes(pickle.dumps(fake_candidates(cls.T, cls.inv)))
        cls.cut = args + ["cut", "--cache", str(cache), "--out", str(cls.out), "--lossless"]
        th.main(cls.cut)
        cls.manifest = json.loads((cls.out / "shapesz/manifest.json").read_text())
        cls.report = json.loads((cls.work / "cut-report.json").read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_inventory_spans_the_levels(self):
        self.assertEqual(self.inv["levels"], LEVELS)
        l0 = self.inv["layers"]["0"]
        # TYRIAN's 66 ground tiles have art; HOLES and ASSASSIN add more.
        self.assertEqual(l0["tilesWithArt"], 66)
        self.assertGreater(l0["tilesLeft"], 10)
        t46 = l0["tiles"]["46"]
        self.assertTrue(t46["hasArt"])
        self.assertIn("1-9", t46["levels"])
        # Layer 2: HOLES' and ASSASSIN's rock is terrain drawn as tiles; TYRIAN's islands stay under models.
        l2 = self.inv["layers"]["2"]["tiles"]
        self.assertEqual(l2["92"]["kind"], "terrain")
        self.assertFalse(l2["120"]["drawnAsTile"])

    def test_tileset_levels(self):
        ids = th.tileset_levels(DATA, "shapesz")
        self.assertEqual(len(ids), 32)
        self.assertIn("1-9", ids)
        self.assertIn("4-16", ids)
        self.assertNotIn("1-8", ids)  # SAVARA is shapesy

    def test_kept_tiles_are_byte_for_byte(self):
        d = self.out / "shapesz"
        for name, h in self.before.items():
            if name == "manifest.json":
                continue
            self.assertEqual(sha(d / name), h, f"{name} changed")
        for layer_s, lay in self.old_manifest["layers"].items():
            new = self.manifest["layers"][layer_s]
            self.assertEqual(new["image"], lay["image"])
            for k, r in lay["tiles"].items():
                self.assertEqual(new["tiles"][k], r, f"rect of {layer_s}:{k}")
                self.assertTrue(self.report[f"{layer_s}:{k}"].get("kept"))
        # And the texels the game reads for them.
        _, old = th.load_tileset_art(ART)
        _, now = th.load_tileset_art(d)
        for layer, tiles in old.items():
            for n, img in tiles.items():
                if str(n) not in self.old_manifest["layers"].get(str(layer), {}).get("tiles", {}):
                    continue  # not in level 1's part of the atlas, which the test merges into
                self.assertTrue(np.array_equal(now[layer][n], img), f"texels of {layer}:{n}")

    def test_new_tiles_follow_the_format(self):
        new = [k for k, r in self.report.items() if "from" in r]
        self.assertGreater(len(new), 20)
        for layer_s, lay in self.manifest["layers"].items():
            sizes = {}
            for k, r in lay["tiles"].items():
                name = r.get("image", lay["image"])
                if name not in sizes:
                    with Image.open(self.out / "shapesz" / name) as im:
                        sizes[name] = im.size
                W, H = sizes[name]
                self.assertEqual((r["w"], r["h"]), (th.TILE_W * th.SCALE, th.TILE_H * th.SCALE))
                self.assertEqual((r["x"] % 16, r["y"] % 16), (0, 0))
                self.assertTrue(16 <= r["x"] and r["x"] + r["w"] + 16 <= W and 16 <= r["y"] and r["y"] + r["h"] + 16 <= H)
                self.assertTrue(W <= th.ATLAS_MAX and H <= th.ATLAS_MAX)
            # New tiles sit in images of their own, never in the kept ones.
            if layer_s in self.old_manifest["layers"]:
                for k, r in lay["tiles"].items():
                    if k not in self.old_manifest["layers"][layer_s]["tiles"]:
                        self.assertNotIn(r.get("image", lay["image"]), self.before)
        self.assertIn("2", self.manifest["layers"])  # layer 2's rock, new to this tileset's atlas

    def test_seams_hold(self):
        tiles = th.load_atlas(self.out, "shapesz")
        models = th.load_models("shapesz.dat")
        _, base = th.load_tileset_art(ART)
        fresh = {int(k.split(":")[1]) for k, r in self.report.items() if k.startswith("0:") and "from" in r}
        maps = [th.layer_masks(L, 0, models)[:2] for L in self.T.levels]
        new = th.seam_stats(tiles[0], maps, pair_filter=lambda a, b: a in fresh or b in fresh)
        self.assertGreater(new["edges"], 1000)
        # The ground's measure of D58-D60 (TYRIAN 0.57): edges with a new tile no worse than ~0.6.
        self.assertLess(new["texelRatio"], 0.65, new)
        # Level 1's own edges are exactly what they were.
        L19 = self.T.level("1-9")
        g, dr = th.layer_masks(L19, 0, models)[:2]
        self.assertEqual(th.seam_stats(tiles[0], g, dr)["texelRatio"], th.seam_stats(base[0], g, dr)["texelRatio"])
        # Without the seam pass the same paintings meet much worse.
        raw = {}
        for layer, d in self.inv["layers"].items():
            for t in d["tiles"].values():
                if int(layer) == 0 and t["tile"] in fresh:
                    raw[t["tile"]] = None
        cands = pickle.loads((self.work / "cands.pkl").read_bytes())
        plain = dict(tiles[0])
        for n in raw:
            hd = cands[(0, n)][0]["hd"]
            plain[n] = np.concatenate([hd, np.full(hd.shape[:2] + (1,), 255, np.float32)], -1)
        before = th.seam_stats(plain, maps, pair_filter=lambda a, b: a in fresh or b in fresh)
        self.assertGreater(before["texelRatio"], 1.5 * new["texelRatio"], (before["texelRatio"], new["texelRatio"]))

    def test_cut_again_changes_nothing(self):
        d = self.out / "shapesz"
        files = {f.name: sha(f) for f in d.iterdir()}
        th.main(self.cut)
        self.assertEqual({f.name: sha(f) for f in d.iterdir()}, files)


class StripTest(unittest.TestCase):
    def test_held_strips_stay_and_free_ones_meet_them(self):
        rng = np.random.default_rng(1)
        a = rng.uniform(0, 255, (224, 192, 3)).astype(np.float32)
        b = rng.uniform(0, 255, (224, 192, 3)).astype(np.float32)
        pairs = Counter({("h", 1, 2): 50, ("v", 2, 1): 5})
        s = th.solve_strips({2: b}, pairs, fixed={1: a})
        np.testing.assert_allclose(s[(1, "right")], th.edge_strip(a, "right"), atol=1e-6)
        # Tile 2's left strip is pulled almost onto tile 1's right one (50 pairs against a 0.15 pull).
        gap = np.abs(s[(2, "left")] - s[(1, "right")]).mean()
        self.assertLess(gap, 0.2 * np.abs(th.edge_strip(b, "left") - th.edge_strip(a, "right")).mean())

    def test_no_fixed_is_the_old_solve(self):
        rng = np.random.default_rng(2)
        tiles = {n: rng.uniform(0, 255, (224, 192, 3)).astype(np.float32) for n in (1, 2, 3)}
        pairs = Counter({("h", 1, 2): 10, ("h", 2, 3): 4, ("v", 1, 3): 7})
        s1 = th.solve_strips(tiles, pairs)
        s2 = th.solve_strips(tiles, pairs, fixed={})
        for k in s1:
            np.testing.assert_array_equal(s1[k], s2[k])


class FieldTest(unittest.TestCase):
    """A repeated tile painted as one patch (D137)."""

    def test_patch_is_seamless_when_repeated(self):
        rng = np.random.default_rng(3)
        a = np.cumsum(np.cumsum(rng.normal(size=(60, 70, 3)), 0), 1).astype(np.float32)  # a drifting texture: its edges differ
        p = th.make_periodic(a, 0.3)
        wrap = np.abs(p[:, 0] - p[:, -1]).mean(), np.abs(p[0] - p[-1]).mean()
        inside = np.abs(np.diff(p, axis=1)).mean()
        self.assertLess(max(wrap), 1.5 * inside)  # the wrap is a step like any other, not a seam
        self.assertGreater(np.abs(a[:, 0] - a[:, -1]).mean(), 3 * inside)  # (and the raw patch was)

    def test_virtual_tiles_follow_the_map_column_and_row(self):
        g = np.full((13, 15), 16)
        g[0, 0] = 5
        v = th.field_grid(g, {16: 0})
        self.assertEqual(v[0, 0], 5)
        self.assertEqual(v[1, 2], th.FIELD_BASE + 1 * th.FIELD_COLS + 2)
        self.assertEqual(v[1 + th.FIELD_ROWS, 2 + th.FIELD_COLS], v[1, 2])  # the patch repeats
        self.assertEqual(th.field_real(int(v[1, 2]), {16: 0}), 16)

    def test_histogram_match_takes_the_reference_colours(self):
        a = np.random.default_rng(1).uniform(0, 255, (40, 40, 3)).astype(np.float32)
        ref = np.random.default_rng(2).normal([10, 30, 50], [3, 8, 12], (50, 50, 3)).astype(np.float32)
        out = th.match_histogram(a, ref)
        self.assertLess(np.abs(out.mean((0, 1)) - ref.mean((0, 1))).max(), 1.0)
        self.assertLess(np.abs(out.std((0, 1)) - ref.std((0, 1))).max(), 1.0)


    def test_tint_round_trip(self):
        """D138: an offset image survives the atlas's bytes and the shader's bilinear read (smooth offsets, to a level or two)."""
        yy, xx = np.mgrid[0:56, 0:48]
        d = np.stack([20 * np.sin(xx / 9) + 5, -30 * np.cos(yy / 11), 0 * xx + 40], -1).astype(np.float32)  # sRGB levels, smooth
        ratio = 4  # 8 texels per pixel down to 2: the offsets come back at the atlas's resolution
        t = th.tint_down(np.kron(d, np.ones((ratio, ratio, 1), np.float32)), ratio)
        np.testing.assert_allclose(t, d, atol=1e-4)
        back = th.tint_decode(th.tint_encode(t))
        self.assertLess(np.abs(back - t).max(), 2.0)  # one byte step of the sRGB-coded linear value, at worst
        up = th.tint_up(back, 2)
        self.assertEqual(up.shape, (112, 96, 3))
        self.assertLess(np.abs(up[8:-8, 8:-8] - np.kron(d, np.ones((2, 2, 1)))[8:-8, 8:-8]).mean(), 1.5)
        self.assertAlmostEqual(float(th.tint_decode(th.tint_encode(np.zeros(1, np.float32)))[0]), 0.0, delta=1.0)


class RimFix(unittest.TestCase):
    """fix_rim (D113): the teal ring the seam strips left on blue-grey plating."""

    @staticmethod
    def tile(inner, rim, w=192, h=224, rim_w=8):
        a = np.zeros((h, w, 4), np.float32)
        a[..., :3] = inner
        a[..., 3] = 255
        a[:rim_w] = a[-rim_w:] = a[:, :rim_w] = a[:, -rim_w:] = [*rim, 255]
        return a

    def test_teal_rim_goes_plating_blue(self):
        t = self.tile([40, 54, 65], [41, 66, 73])
        out, change = th.fix_rim(t)
        self.assertGreater(change, 5)
        r = out[0, 0, :3]
        self.assertAlmostEqual(r[1], 41 + th.RIM_RHO * (73 - 41), delta=0.5)  # green at the plating's ratio
        self.assertEqual((r[0], r[2]), (41, 73))  # red and blue stay
        np.testing.assert_array_equal(out[24:-24, 24:-24], t[24:-24, 24:-24])  # the interior is untouched
        again, change2 = th.fix_rim(out)
        self.assertLess(change2, 0.5)  # and it settles

    def test_other_materials_are_left_alone(self):
        for inner, rim in (([30, 70, 25], [20, 90, 20]), ([90, 70, 50], [100, 90, 60])):  # jungle, rock
            t = self.tile(inner, rim)
            out, change = th.fix_rim(t)
            self.assertEqual(change, 0.0)
            np.testing.assert_array_equal(out, t)

    def test_plating_with_a_plating_rim_is_unchanged(self):
        t = self.tile([40, 54, 65], [44, 58, 70])
        out, change = th.fix_rim(t)
        self.assertLess(change, 0.5)


if __name__ == "__main__":
    unittest.main()
