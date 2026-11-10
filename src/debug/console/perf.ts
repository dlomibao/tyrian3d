// The console's `fps` overlay (D109): frame rate and frame time from the display frames, the
// level's tick and the sim speed, and the draw list's size. A corner of text that takes no input.

import type { ConsoleBridge } from "../../app/consoleBridge";

let el: HTMLDivElement | null = null;
let raf = 0;

export function perfOverlayOn(): boolean {
  return el !== null;
}

export function setPerfOverlay(bridge: ConsoleBridge, on: boolean): void {
  if (on === perfOverlayOn()) return;
  if (!on) {
    cancelAnimationFrame(raf);
    el?.remove();
    el = null;
    return;
  }
  const div = document.createElement("div");
  div.className = "con-perf";
  div.setAttribute("aria-hidden", "true");
  document.body.append(div);
  el = div;
  const times: number[] = [];
  let last = performance.now();
  let shown = 0;
  const frame = (now: number) => {
    times.push(now - last);
    last = now;
    if (now - shown > 500 && times.length) {
      shown = now;
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const max = Math.max(...times);
      const draws = bridge.view?.draws.stats().items ?? 0;
      const place = bridge.place === "level" ? `tick ${bridge.ticks}${bridge.speed !== 1 ? ` ×${bridge.speed}` : ""}` : bridge.place;
      div.textContent = `${(1000 / avg).toFixed(0)} fps · frame ${avg.toFixed(1)} ms (max ${max.toFixed(1)}) · ${place} · ${draws} draws`;
      times.length = 0;
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
}
