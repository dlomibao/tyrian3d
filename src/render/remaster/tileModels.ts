// Which background tiles are drawn as Blender models in the remastered backgrounds (DECISIONS.md
// D34), and how a multi-tile structure is recognised by its tile pattern.
//
// Each structure model's script (assets/blender/tiles/) writes one JSON file to tileModels/, like
// the enemy models' spriteModels/ (D15): the model and the pattern of tiles it stands for, as
// rows of 0-based tile numbers in the shapes file (-1: any tile). The model's origin is the
// pattern's centre (plus `offset`). A tile can belong to several patterns; the biggest (most
// cells) whose visible cells all match is used, so a structure wins over the per-tile models of
// its tiles (which stay for the tiles it doesn't cover, and while it isn't matched yet), and a
// whole structure over a variant cut by the map's edge. Equal sizes keep the files' order.
//
// In game a pattern is matched from any of its tiles, so a structure stays whole while its first
// row is off screen: a tile at map index `key` in pattern cell (row, col) puts the pattern's
// top-left at key - row * mapWidth - col, and every cell of the pattern that is drawn this tick
// must hold the pattern's tile. Cells not drawn this tick (off screen) aren't checked.
//
// A structure built from tiles that also occur elsewhere as plain terrain (the asteroid platforms of
// shapesz.dat: rims, paving and channels are modular tiles) gives every cell it covers and
// `minRows`: it's placed only once that many of its rows are drawn and match, so the edge of a
// plain platform scrolling in doesn't pass for it. tests/render/remaster.test.ts checks in the
// real maps that `minRows` rows always tell such a structure apart.
//
// A level preloads only the models match() can draw on its maps (modelsOnMaps, D236): it runs the
// same matchAt and fits on every window of map cells the sim can draw (tests/render/structurePreload.test.ts).

import { BG_KEY_LAYER } from "../../sim/backgrnd";
import type { Draw, TileDraw } from "../../sim/draw";

export interface TileModelEntry {
  /** Model path in public/models/, without .glb, e.g. "tiles/shapesz/bunker-ring". */
  model: string;
  /** The tileset, as in TileDraw.tileId: "shapesz.dat". */
  shapes: string;
  /** The background layer the tiles are on: 0 (ground), 1 or 2. */
  layer: 0 | 1 | 2;
  /** Rows of tile numbers (0-based records in the shapes file); -1 matches any tile. */
  tiles: number[][];
  /**
   * Keep drawing the tiles under the model. Ground (layer 0) structures stand on their own tiles,
   * which stay as the remastered ground; structures on layers 1 and 2 replace their tiles.
   */
  keepTiles?: boolean;
  /**
   * Its tiles also occur as other terrain: match only when at least this many of the pattern's
   * rows (or all of them, if fewer) have drawn cells, all matching. Without it any drawn cell of
   * the pattern is enough, and its tiles must occur nowhere else on the layer.
   */
  minRows?: number;
  /**
   * Where the model's origin is, in px from the pattern's centre (x right, y down): a variant of
   * a structure cut by the map's edge reuses the whole structure's model, e.g. [12, 0] for the
   * left two columns of a three-column one.
   */
  offset?: [number, number];
  /**
   * The model already shows the broken sockets its tiles paint under their enemies (D115), so a
   * shot-off enemy there leaves only the fresh break's glow and a light soot, not a full scorch mark.
   */
  brokenSockets?: boolean;
}

/** Map widths in tiles per layer (JE_MapType, JE_MapType2, JE_MapType3). */
const MAP_WIDTHS = [14, 14, 15] as const;

interface Cell {
  entry: TileModelEntry;
  row: number;
  col: number;
}

/** A matched structure: where its model goes this tick. */
export interface StructureMatch {
  entry: TileModelEntry;
  /** The map key of the pattern's top-left cell, which identifies this structure on screen. */
  anchorKey: number;
  /** Offset from the matched tile's top-left to the pattern's centre, in px. */
  dx: number;
  dy: number;
}

const files = import.meta.glob<TileModelEntry>("../tileModels/*.json", { eager: true, import: "default" });

/** Every entry in src/render/tileModels/. */
export const TILE_MODELS: readonly TileModelEntry[] = Object.values(files);

export class TileModelIndex {
  private readonly cells = new Map<string, Cell[]>();
  /** The same cells per layer by tile id, for the per-draw lookups (D91: no key string per draw). */
  private readonly byLayer = [new Map<string, Cell[]>(), new Map<string, Cell[]>(), new Map<string, Cell[]>()];
  /** A number per entry, for the verdicts' keys. */
  private readonly entryIds = new Map<TileModelEntry, number>();
  /** Each entry's pattern as tile ids (TileDraw.tileId; null: any tile). */
  private readonly tileIds = new Map<TileModelEntry, (string | null)[][]>();
  /** This tick's tile ids by draw key, per layer. */
  private readonly drawn = [new Map<number, string>(), new Map<number, string>(), new Map<number, string>()];
  /** This tick's verdicts on (pattern, anchor) pairs: a big pattern is checked once, not per tile. */
  private readonly verdicts = new Map<number, boolean>();

  constructor(entries: readonly TileModelEntry[] = TILE_MODELS) {
    for (const entry of entries) {
      this.entryIds.set(entry, this.entryIds.size);
      this.tileIds.set(entry, entry.tiles.map((row) => row.map((t) => (t < 0 ? null : `${entry.shapes}:${t}`))));
      entry.tiles.forEach((row, r) =>
        row.forEach((tile, c) => {
          if (tile < 0) return;
          const id = cellId(`${entry.shapes}:${tile}`, entry.layer);
          let list = this.cells.get(id);
          if (!list) {
            this.cells.set(id, (list = []));
            this.byLayer[entry.layer].set(`${entry.shapes}:${tile}`, list);
          }
          list.push({ entry, row: r, col: c });
        }),
      );
    }
    // Biggest pattern first (a stable sort keeps the files' order between equals).
    const size = (e: TileModelEntry) => e.tiles.reduce((n, row) => n + row.filter((t) => t >= 0).length, 0);
    for (const list of this.cells.values()) list.sort((a, b) => size(b.entry) - size(a.entry));
  }

  get size(): number {
    return this.cells.size;
  }

  /** Whether any model stands for this tile (cheap check before match()). */
  has(d: TileDraw): boolean {
    return this.byLayer[d.layer].has(d.tileId);
  }

  /** Every model path in the index, or those of one tileset ("shapesz.dat"). */
  models(shapes?: string): string[] {
    const out = new Set<string>();
    for (const list of this.cells.values()) for (const c of list) if (!shapes || c.entry.shapes === shapes) out.add(c.entry.model);
    return [...out];
  }

  /**
   * The models of tileset `shapes` that a level with these tiles (layer, 0-based tile number, and
   * when it first shows) can draw, each with the earliest time any of its tiles shows.
   */
  modelsOfTiles(shapes: string, tiles: Iterable<{ layer: number; tile: number; time: number }>): Map<string, number> {
    const out = new Map<string, number>();
    for (const t of tiles) {
      for (const c of this.cells.get(cellId(`${shapes}:${t.tile}`, t.layer as 0 | 1 | 2)) ?? []) {
        if (c.entry.shapes !== shapes) continue;
        out.set(c.entry.model, Math.min(out.get(c.entry.model) ?? Infinity, t.time));
      }
    }
    return out;
  }

  /** Record the tiles drawn this tick, for checking patterns. */
  prepare(items: readonly Draw[]): void {
    for (const m of this.drawn) m.clear();
    this.verdicts.clear();
    for (const d of items) if (d.kind === "tile") this.drawn[d.layer].set(d.key, d.tileId);
  }

  /** The structure this tile belongs to, or null if no pattern with it matches. */
  match(d: TileDraw): StructureMatch | null {
    return this.matchAt(d.layer, d.key - d.layer * BG_KEY_LAYER, d.tileId, this.tickFits);
  }

  /** This tick's verdict on a pattern at an anchor, checked once per tick (a big pattern isn't checked per tile). */
  private readonly tickFits = (entry: TileModelEntry, anchorKey: number): boolean => {
    const memo = anchorKey * 4096 + this.entryIds.get(entry)!;
    let ok = this.verdicts.get(memo);
    if (ok === undefined) {
      ok = this.fits(entry, anchorKey, this.drawn[entry.layer]);
      this.verdicts.set(memo, ok);
    }
    return ok;
  };

  /**
   * The structure tile `tileId` at map index `index` of `layer` belongs to: the first pattern holding
   * the tile (biggest first) that stays inside the map's width and `fits(entry, anchorKey)`. Shared by
   * match() and modelsOnMaps, so what a level preloads and what it draws can't disagree (D236).
   */
  private matchAt(layer: 0 | 1 | 2, index: number, tileId: string, fits: (entry: TileModelEntry, anchorKey: number) => boolean): StructureMatch | null {
    const list = this.byLayer[layer].get(tileId);
    if (!list) return null;
    const width = MAP_WIDTHS[layer];
    for (const { entry, row, col } of list) {
      const rows = entry.tiles.length;
      const cols = entry.tiles[0].length;
      const left = (index % width) - col;
      if (left < 0 || left + cols > width) continue; // the pattern would wrap around the map's edge
      const anchor = index - row * width - col;
      if (!fits(entry, layer * BG_KEY_LAYER + anchor)) continue;
      return {
        entry,
        anchorKey: layer * BG_KEY_LAYER + anchor,
        dx: -col * 24 + (cols * 24) / 2 + (entry.offset?.[0] ?? 0),
        dy: -row * 28 + (rows * 28) / 2 + (entry.offset?.[1] ?? 0),
      };
    }
    return null;
  }

  /**
   * The models of tileset `shapes` that match() can draw on a level whose maps are `maps` (per layer,
   * row-major MAP_WIDTHS wide: the tile number each cell draws, -1 where the sim draws none). A
   * level preloads only these (D236): a structure whose pattern (as much of it as a screen shows)
   * occurs nowhere, or where a bigger pattern always takes its tiles, is never drawn.
   *
   * It runs matchAt and fits, as match() does, on every screen the sim can draw. backgrnd.ts draws
   * a layer as 7 or 8 screen rows (SCREEN_ROWS) of 12 consecutive map cells (SCREEN_COLS), each
   * one map width on from the last, starting wherever the scroll puts the first: so around every
   * cell holding a pattern's tile, it tries every such window with that cell in it, at every offset
   * (also those whose rows wrap round the map's columns, which a scroll can give). A model is kept if
   * any of them draws it. columnFits and rowsFit skip the cells where no window can match a pattern.
   */
  modelsOnMaps(shapes: string, maps: readonly ArrayLike<number>[]): Set<string> {
    // A level started again (a retry, the next game) asks again: its answer, kept (~0.1 s for an asteroid field).
    let h1 = 0x811c9dc5, h2 = 0x9e3779b9;
    for (const map of maps) {
      const n = map?.length ?? -1;
      h1 = Math.imul(h1 ^ n, 0x01000193);
      h2 = Math.imul(h2 ^ n, 0x85ebca6b);
      for (let i = 0; i < n; i++) {
        h1 = Math.imul(h1 ^ (map[i] & 0xffff), 0x01000193);
        h2 = Math.imul((h2 ^ (map[i] & 0xffff)) + i, 0x85ebca6b);
      }
    }
    const key = `${shapes}|${h1 >>> 0}|${h2 >>> 0}`;
    const known = this.onMaps.get(key);
    if (known) return new Set(known);
    const out = this.mapModels(shapes, maps);
    this.onMaps.set(key, out);
    if (this.onMaps.size > 8) this.onMaps.delete(this.onMaps.keys().next().value!);
    return new Set(out);
  }

  /** Answers of modelsOnMaps, by tileset and maps (a hash of them). */
  private readonly onMaps = new Map<string, Set<string>>();

  private mapModels(shapes: string, maps: readonly ArrayLike<number>[]): Set<string> {
    const out = new Set<string>();
    const ids = new Map<number, string>();
    const idOf = (t: number) => {
      let id = ids.get(t);
      if (id === undefined) ids.set(t, (id = `${shapes}:${t}`));
      return id;
    };
    for (const layer of [0, 1, 2] as const) {
      const map = maps[layer];
      if (!map) continue;
      const width = MAP_WIDTHS[layer];
      const base = layer * BG_KEY_LAYER;
      // The window: its first row starts at map index m, and it has n rows.
      let m = 0, n = 0;
      const drawn: DrawnTiles = {
        get: (key) => {
          const index = key - base;
          const d = index - m;
          if (d < 0 || d >= n * width || d % width >= SCREEN_COLS || index < 0 || index >= map.length) return undefined;
          const t = map[index];
          return t < 0 ? undefined : idOf(t);
        },
      };
      // Per pattern at an anchor (entry and anchor), its verdict per window that draws different cells of it.
      const verdicts = new Map<number, Map<number, boolean>>();
      // The patterns that can fit in some window over the cell tried (columnFits, rowsFit), and theirs.
      const possible: { entry: TileModelEntry; anchorKey: number; anchorRow: number; phases: number[]; byWindow: Map<number, boolean> }[] = [];
      // This window's verdict on a possible pattern: whether it fits in the cells the window draws of
      // it, which are its first row's (`top`, relative to the pattern), the rows after it, and the next
      // row's first cells, at a scroll offset whose columns are one of a few classes over the pattern.
      const verdict = (q: (typeof possible)[number]): boolean => {
        const rows = q.entry.tiles.length;
        const top = Math.floor(m / width) - q.anchorRow;
        const at = (r: number) => (r >= 0 && r < rows ? r + 1 : 0);
        const lo = Math.max(top + 1, 0), hi = Math.min(top + n - 1, rows - 1);
        const seen = ((at(top) * 64 + (lo <= hi ? lo + 1 : 0)) * 64 + (lo <= hi ? hi + 1 : 0)) * 64 + at(top + n);
        const memo = q.phases[m - Math.floor(m / width) * width] * 2 ** 24 + seen;
        let ok = q.byWindow.get(memo);
        if (ok === undefined) q.byWindow.set(memo, (ok = this.fits(q.entry, q.anchorKey, drawn, top, top + n)));
        return ok;
      };
      // matchAt's test in this window: only possible patterns can fit (`fitting`: theirs that do, as
      // bits, up to 30 of them; with more, each is tested as asked).
      let fitting = 0;
      const fits = (entry: TileModelEntry, anchorKey: number): boolean => {
        const i = possible.findIndex((x) => x.entry === entry && x.anchorKey === anchorKey);
        return i >= 0 && (possible.length > 30 ? verdict(possible[i]) : (fitting & (1 << i)) !== 0);
      };
      for (let p = 0; p < map.length; p++) {
        if (map[p] < 0) continue;
        const tileId = idOf(map[p]);
        const list = this.byLayer[layer].get(tileId);
        if (!list || list.every((c) => out.has(c.entry.model))) continue;
        possible.length = 0;
        const wanted: string[] = [];
        for (const c of list) {
          if (!columnFits(c, p, map) || !rowsFit(c, p, map)) continue;
          const anchor = p - c.row * width - c.col;
          const anchorRow = Math.floor(anchor / width);
          const pair = this.entryIds.get(c.entry)! * 65536 + anchor + 32768;
          let byWindow = verdicts.get(pair);
          if (!byWindow) verdicts.set(pair, (byWindow = new Map()));
          possible.push({ entry: c.entry, anchorKey: base + anchor, anchorRow, phases: phaseClasses(width, anchor - anchorRow * width, c.entry.tiles[0].length), byWindow });
          if (!out.has(c.entry.model)) wanted.push(c.entry.model);
        }
        // Every window with this cell in its row j, at column t of the row, until nothing new can come;
        // matchAt once per set of possible patterns that fit (it decides by those alone).
        let left = wanted.length;
        const tried = new Set<number>();
        for (const rows of SCREEN_ROWS) {
          for (let j = 0; j < rows && left > 0; j++) {
            for (let t = 0; t < SCREEN_COLS && left > 0; t++) {
              m = p - j * width - t;
              n = rows;
              if (possible.length <= 30) {
                fitting = 0;
                possible.forEach((q, i) => (fitting |= verdict(q) ? 1 << i : 0));
                if (tried.has(fitting)) continue;
                tried.add(fitting);
              }
              const hit = this.matchAt(layer, p, tileId, fits);
              if (hit && !out.has(hit.entry.model)) {
                out.add(hit.entry.model);
                left = wanted.filter((w) => !out.has(w)).length;
              }
            }
          }
        }
      }
    }
    return out;
  }

  /**
   * Whether every drawn cell of the pattern at `anchorKey` holds its tile (and, with minRows, enough
   * rows are drawn). Rows outside `r0`..`r1` aren't looked at: the caller knows none is drawn.
   */
  private fits(entry: TileModelEntry, anchorKey: number, drawn: DrawnTiles, r0 = 0, r1 = entry.tiles.length - 1): boolean {
    const rows = entry.tiles.length;
    const cols = entry.tiles[0].length;
    const width = MAP_WIDTHS[entry.layer];
    const ids = this.tileIds.get(entry)!;
    let rowsSeen = 0;
    for (let r = Math.max(0, r0); r <= Math.min(rows - 1, r1); r++) {
      let seen = false;
      for (let c = 0; c < cols; c++) {
        const want = ids[r][c];
        if (want === null) continue;
        const got = drawn.get(anchorKey + r * width + c);
        if (got === undefined) continue;
        if (got !== want) return false;
        seen = true;
      }
      if (seen) rowsSeen++;
    }
    return entry.minRows === undefined || rowsSeen >= Math.min(entry.minRows, rows);
  }
}

const cellId = (tileId: string, layer: number) => `${layer}|${tileId}`;

/** The tile id drawn at a map key (layer * BG_KEY_LAYER + index), or undefined where none is. */
interface DrawnTiles {
  get(key: number): string | undefined;
}

/** backgrnd.ts blitBackgroundRow: a screen row is 12 consecutive map cells. */
const SCREEN_COLS = 12;
/**
 * The screen rows a layer draws: draw_background_1/2/3 draw 8, at y = -28..168 plus the scroll
 * (0..27), less one wholly off the playfield's top (y <= -28) or bottom (y >= 184).
 */
const SCREEN_ROWS = [7, 8] as const;

/**
 * Whether pattern cell `cell` at map index `p` can fit up and down its column: a window over `p`
 * draws its column for SCREEN_ROWS[0] rows at least (one cell per screen row), so where no run of
 * that many map rows with `p` in it fits, fits() fails in every window over `p`.
 */
function columnFits({ entry, row, col }: Cell, p: number, map: ArrayLike<number>): boolean {
  const width = MAP_WIDTHS[entry.layer];
  const rows = entry.tiles.length;
  const run = SCREEN_ROWS[0];
  const left = (p % width) - col;
  if (left < 0 || left + entry.tiles[0].length > width) return false; // as matchAt
  for (let j = 0; j < run; j++) {
    let ok = true;
    for (let d = -j; d < run - j && ok; d++) {
      const r = row + d;
      if (r < 0 || r >= rows) continue;
      const want = entry.tiles[r][col];
      const i = p + d * width;
      if (want < 0 || i < 0 || i >= map.length || map[i] < 0) continue;
      ok = map[i] === want;
    }
    if (ok) return true;
  }
  return false;
}

/**
 * Whether pattern cell `cell` at map index `p` can fit across the rows of a window over `p`. A
 * window's rows but its first (and the next row's first cells) draw every column but one cyclic run
 * of width - SCREEN_COLS columns (where the scroll starts each screen row), the same in each; there
 * are SCREEN_ROWS[0] - 1 of them at least, and `p` is in them or just above or below them. So in some
 * run of that many map rows next to or round `p`, every wrong tile is in one such run of columns, and
 * `p` outside it if it's among those rows; where none does, fits() fails in every window over `p`.
 */
function rowsFit({ entry, row, col }: Cell, p: number, map: ArrayLike<number>): boolean {
  const width = MAP_WIDTHS[entry.layer];
  const rows = entry.tiles.length;
  const cols = entry.tiles[0].length;
  const run = SCREEN_ROWS[0] - 1;
  const pc = p % width;
  const left = pc - col;
  const k = Math.floor(p / width);
  const anchorRow = k - row;
  // The columns of a map row's wrong tiles (drawn, and not the pattern's), as bits.
  const wrong = (mapRow: number): number => {
    const r = mapRow - anchorRow;
    if (r < 0 || r >= rows) return 0;
    let bits = 0;
    for (let c = 0; c < cols; c++) {
      const want = entry.tiles[r][c];
      const i = mapRow * width + left + c;
      if (want < 0 || i < 0 || i >= map.length || map[i] < 0) continue;
      if (map[i] !== want) bits |= 1 << (left + c);
    }
    return bits;
  };
  const byRow: number[] = [];
  for (let mr = k - run; mr <= k + run; mr++) byRow.push(wrong(mr));
  for (let s = k - run; s <= k + 1; s++) {
    let bad = 0;
    for (let mr = s; mr < s + run; mr++) bad |= byRow[mr - (k - run)];
    const inside = k >= s && k < s + run;
    for (let a = 0; a < width; a++) {
      const g = GAPS[width][a];
      if ((bad & ~g) === 0 && !(inside && g & (1 << pc))) return true;
    }
  }
  return false;
}

/**
 * For a pattern `cols` wide at column `left` of a map `width` wide: per scroll offset (the column a
 * window's screen rows start at), a class number, the same for offsets whose screen rows draw the
 * same of the pattern's columns (in a window's first row, the rows after it, and the next row's).
 */
function phaseClasses(width: number, left: number, cols: number): number[] {
  const key = (width * 64 + left) * 64 + cols;
  let classes = PHASE_CLASSES.get(key);
  if (!classes) {
    const span = ((1 << cols) - 1) << left;
    const seen = new Map<string, number>();
    classes = Array.from({ length: width }, (_, p) => {
      let first = 0, wrap = 0;
      for (let t = 0; t < SCREEN_COLS; t++) {
        if (p + t < width) first |= 1 << (p + t);
        else wrap |= 1 << (p + t - width);
      }
      const k = `${first & span}|${(first | wrap) & span}|${wrap & span}`;
      let c = seen.get(k);
      if (c === undefined) seen.set(k, (c = seen.size));
      return c;
    });
    PHASE_CLASSES.set(key, classes);
  }
  return classes;
}
const PHASE_CLASSES = new Map<number, number[]>();

/** Per map width, the runs of width - SCREEN_COLS columns a screen row can leave out (from each column, wrapping), as bits. */
const GAPS: Record<number, number[]> = Object.fromEntries(
  [...new Set(MAP_WIDTHS)].map((w) => [w, Array.from({ length: w }, (_, a) => Array.from({ length: w - SCREEN_COLS }, (_, x) => 1 << ((a + x) % w)).reduce((g, b) => g | b, 0))]),
);
