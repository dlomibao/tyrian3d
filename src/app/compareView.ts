// `?compare=1` (DECISIONS.md D158): in-level play side by side, the original on the left (the draw
// list rasterised as OpenTyrian draws it, with its HUD: render/classic/) and the remaster on the
// right (the Hud lays its frame and the 3D view out in the right half). One game drives both: each
// tick's draw list goes to both renderers, so a single input plays them in step.

import { decodePicture } from "../data/pictures";
import { paletteToRgba8 } from "../data/palette";
import { requireFile, type TyrianFiles } from "../sim/resources";
import type { DrawList } from "../sim/draw";
import { g } from "../sim/state";
import { ClassicRenderer, SCREEN_H, SCREEN_W, Surface } from "../render/classic/classicRenderer";
import { drawAfterFilter, drawBeforeFilter, drawSidebar } from "../render/classic/classicHud";

/** Whether the URL asks for the comparison. */
export function compareFromUrl(search: string = location.search): boolean {
  const v = new URLSearchParams(search).get("compare");
  return v !== null && v !== "0" && v !== "false";
}

export class CompareView {
  private readonly box = document.createElement("div");
  private readonly canvas = document.createElement("canvas");
  private readonly ctx: CanvasRenderingContext2D;
  private readonly image: ImageData;
  private readonly renderer = new ClassicRenderer();
  private readonly screen = new Surface();
  private readonly frame: Uint8Array | null;
  private rgba: { palette: number; table: Uint8Array } | null = null;

  constructor(files: TyrianFiles) {
    this.canvas.width = SCREEN_W;
    this.canvas.height = SCREEN_H;
    this.ctx = this.canvas.getContext("2d")!;
    this.image = this.ctx.createImageData(SCREEN_W, SCREEN_H);
    Object.assign(this.box.style, {
      position: "fixed", left: "0", top: "0", width: "50vw", height: "100vh", background: "#000", zIndex: "40",
      display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none",
    });
    Object.assign(this.canvas.style, { width: "100%", maxHeight: "100%", aspectRatio: "320 / 200", objectFit: "contain", imageRendering: "pixelated" });
    this.box.append(this.canvas);
    this.box.style.display = "none"; // not `hidden`: the inline flex display would override it
    document.body.append(this.box);
    let pic: Uint8Array | null = null;
    try {
      pic = decodePicture(requireFile(files, "tyrian.pic"), 3);
    } catch {
      pic = null;
    }
    this.frame = pic;
  }

  set visible(v: boolean) {
    this.box.style.display = v ? "flex" : "none";
  }

  /** Draw one tick's draw list the original way. Call right after the tick, before the next. */
  draw(list: DrawList): void {
    if (this.box.style.display === "none") return;
    drawSidebar(this.screen, this.frame);
    this.renderer.render(list, this.screen, drawBeforeFilter, drawAfterFilter);
    if (this.rgba?.palette !== list.palette) {
      const pal = g.res.palettes[list.palette] ?? g.res.palettes[0];
      this.rgba = { palette: list.palette, table: paletteToRgba8(pal) };
    }
    const t = this.rgba.table;
    const d = this.image.data;
    const px = this.screen.px;
    for (let i = 0; i < px.length; i++) {
      const c = px[i] * 4;
      d[i * 4] = t[c];
      d[i * 4 + 1] = t[c + 1];
      d[i * 4 + 2] = t[c + 2];
      d[i * 4 + 3] = 255;
    }
    this.ctx.putImageData(this.image, 0, 0);
  }
}
