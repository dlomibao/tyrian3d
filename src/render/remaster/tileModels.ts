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
  /** This tick's tile ids by draw key, per layer. */
  private readonly drawn = [new Map<number, string>(), new Map<number, string>(), new Map<number, string>()];
  /** This tick's verdicts on (pattern, anchor) pairs: a big pattern is checked once, not per tile. */
  private readonly verdicts = new Map<string, boolean>();

  constructor(entries: readonly TileModelEntry[] = TILE_MODELS) {
    for (const entry of entries) {
      entry.tiles.forEach((row, r) =>
        row.forEach((tile, c) => {
          if (tile < 0) return;
          const id = cellId(`${entry.shapes}:${tile}`, entry.layer);
          let list = this.cells.get(id);
          if (!list) this.cells.set(id, (list = []));
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
    return this.cells.has(cellId(d.tileId, d.layer));
  }

  /** Every model path in the index, or those of one tileset ("shapesz.dat"). */
  models(shapes?: string): string[] {
    const out = new Set<string>();
    for (const list of this.cells.values()) for (const c of list) if (!shapes || c.entry.shapes === shapes) out.add(c.entry.model);
    return [...out];
  }

  /** Record the tiles drawn this tick, for checking patterns. */
  prepare(items: readonly Draw[]): void {
    for (const m of this.drawn) m.clear();
    this.verdicts.clear();
    for (const d of items) if (d.kind === "tile") this.drawn[d.layer].set(d.key, d.tileId);
  }

  /** The structure this tile belongs to, or null if no pattern with it matches. */
  match(d: TileDraw): StructureMatch | null {
    const list = this.cells.get(cellId(d.tileId, d.layer));
    if (!list) return null;
    const width = MAP_WIDTHS[d.layer];
    const index = d.key - d.layer * BG_KEY_LAYER;
    const drawn = this.drawn[d.layer];
    const shapes = d.tileId.slice(0, d.tileId.indexOf(":"));
    for (const { entry, row, col } of list) {
      const rows = entry.tiles.length;
      const cols = entry.tiles[0].length;
      const left = (index % width) - col;
      if (left < 0 || left + cols > width) continue; // the pattern would wrap around the map's edge
      const anchor = index - row * width - col;
      const memo = `${d.layer}|${anchor}|${entry.model}`;
      let ok = this.verdicts.get(memo);
      if (ok === undefined) {
        ok = this.fits(entry, d.layer * BG_KEY_LAYER + anchor, drawn, shapes);
        this.verdicts.set(memo, ok);
      }
      if (!ok) continue;
      return {
        entry,
        anchorKey: d.layer * BG_KEY_LAYER + anchor,
        dx: -col * 24 + (cols * 24) / 2 + (entry.offset?.[0] ?? 0),
        dy: -row * 28 + (rows * 28) / 2 + (entry.offset?.[1] ?? 0),
      };
    }
    return null;
  }

  /** Whether every drawn cell of the pattern at `anchorKey` holds its tile (and, with minRows, enough rows are drawn). */
  private fits(entry: TileModelEntry, anchorKey: number, drawn: Map<number, string>, shapes: string): boolean {
    const rows = entry.tiles.length;
    const cols = entry.tiles[0].length;
    const width = MAP_WIDTHS[entry.layer];
    let rowsSeen = 0;
    for (let r = 0; r < rows; r++) {
      let seen = false;
      for (let c = 0; c < cols; c++) {
        const want = entry.tiles[r][c];
        if (want < 0) continue;
        const got = drawn.get(anchorKey + r * width + c);
        if (got === undefined) continue;
        if (got !== `${shapes}:${want}`) return false;
        seen = true;
      }
      if (seen) rowsSeen++;
    }
    return entry.minRows === undefined || rowsSeen >= Math.min(entry.minRows, rows);
  }
}

const cellId = (tileId: string, layer: number) => `${layer}|${tileId}`;
