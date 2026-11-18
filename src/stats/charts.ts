// The stats page's charts, drawn by hand: HTML bars where a bar is enough (they reflow on a phone
// and read as text to a screen reader), SVG for the daily columns and the death grids. Colours
// come from stats.css custom properties; every mark has a hover/tap tooltip (data-tip).

import { h } from "../ui/components";

const SVG_NS = "http://www.w3.org/2000/svg";

/** An SVG element with attributes. */
export function s<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, ...children: (SVGElement | null)[]): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  for (const c of children) if (c) el.append(c);
  return el;
}

const nf = new Intl.NumberFormat("en");
export const fmt = (n: number): string => nf.format(Math.round(n));
export const pct = (x: number): string => (x > 0 && x < 0.01 ? "<1%" : `${Math.round(x * 100)}%`);
/** 12,345 → "12.3k" for tight labels. */
export const compact = (n: number): string => new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n);

// --- tooltip ---

/** One tooltip for the page: follows the pointer over any [data-tip], and a tap shows it too. */
export function installTooltip(root: HTMLElement): void {
  const tip = h("div", { class: "st-tip", attrs: { role: "tooltip", "aria-hidden": "true" } });
  document.body.append(tip);
  let current: Element | null = null;
  const place = (x: number, y: number) => {
    const r = tip.getBoundingClientRect();
    const left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8);
    const top = y - r.height - 14 < 8 ? y + 18 : y - r.height - 14;
    tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  };
  const show = (el: Element, x: number, y: number) => {
    if (el !== current) {
      current = el;
      tip.textContent = el.getAttribute("data-tip") ?? "";
    }
    tip.classList.add("is-on");
    place(x, y);
  };
  const hide = () => {
    current = null;
    tip.classList.remove("is-on");
  };
  root.addEventListener("pointermove", (e) => {
    const el = (e.target as Element).closest?.("[data-tip]");
    if (el) show(el, e.clientX, e.clientY);
    else hide();
  });
  root.addEventListener("pointerleave", hide);
  root.addEventListener("focusin", (e) => {
    const el = (e.target as Element).closest?.("[data-tip]");
    if (!el) return;
    const r = el.getBoundingClientRect();
    show(el, r.left + r.width / 2, r.top);
  });
  root.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
}

// --- bars ---

export interface BarRow {
  label: string;
  /** A small tag before the label (e.g. the shop slot). */
  tag?: string;
  n: number;
  /** 0..1 of the longest bar. */
  scale: number;
  value: string;
  tip: string;
}

/** A ranked list with a bar under each label, the value on the right. */
export function barList(rows: BarRow[], cls = ""): HTMLElement {
  return h(
    "ol",
    { class: `st-bars ${cls}` },
    ...rows.map((r) =>
      h(
        "li",
        { class: "st-bars__row", attrs: { "data-tip": r.tip } },
        h("span", { class: "st-bars__label" }, r.tag ? h("small", { class: "st-tag", text: r.tag }) : null, h("span", { text: r.label })),
        h("span", { class: "st-bars__value", text: r.value }),
        h("span", { class: "st-bars__track", attrs: { "aria-hidden": "true" } }, h("span", { class: "st-bars__fill", attrs: { style: `--w:${(r.scale * 100).toFixed(2)}%` } })),
      ),
    ),
  );
}

/** Finished / died / quit as one stacked bar (2px gaps between segments). */
export function outcomeBar(o: { finished: number; died: number; quit: number }, label: string): HTMLElement {
  const n = o.finished + o.died + o.quit;
  const seg = (k: "finished" | "died" | "quit", word: string) =>
    o[k] > 0 ? h("span", { class: `st-seg st-seg--${k}`, attrs: { style: `flex-grow:${o[k]}`, "data-tip": `${label}: ${fmt(o[k])} ${word} (${pct(o[k] / n)})` } }) : null;
  return h("div", { class: "st-outcome", attrs: { role: "img", "aria-label": `${label}: ${fmt(o.finished)} cleared, ${fmt(o.died)} lost, ${fmt(o.quit)} quit` } }, seg("finished", "cleared"), seg("died", "lost"), seg("quit", "quit"));
}

/** Score gained on a shared scale: the middle half as a band, the median as a tick, p90 as a dot. */
export function scoreRange(p: { p25?: number; p50?: number; p75?: number; p90?: number; n: number }, max: number, label: string): HTMLElement {
  const x = (v: number | undefined) => `${((Math.min(max, Math.max(0, v ?? 0)) / max) * 100).toFixed(2)}%`;
  const over = (p.p75 ?? 0) > max || (p.p90 ?? 0) > max;
  const tip = `${label}: median ${fmt(p.p50 ?? 0)} points, middle half ${fmt(p.p25 ?? 0)}–${fmt(p.p75 ?? 0)}, top tenth from ${fmt(p.p90 ?? 0)} (${fmt(p.n)} clears)`;
  return h(
    "div",
    { class: `st-range${over ? " st-range--over" : ""}`, attrs: { role: "img", "aria-label": tip, "data-tip": tip } },
    h("span", { class: "st-range__band", attrs: { style: `left:${x(p.p25)};width:calc(${x(p.p75)} - ${x(p.p25)})` } }),
    h("span", { class: "st-range__mid", attrs: { style: `left:${x(p.p50)}` } }),
    p.p90 !== undefined && p.p90 <= max ? h("span", { class: "st-range__top", attrs: { style: `left:${x(p.p90)}` } }) : null,
  );
}

/** Shares of a whole as one bar, each segment labelled below. */
export function splitBar(parts: { label: string; n: number; share: number }[], what: string): HTMLElement {
  return h(
    "div",
    { class: "st-split" },
    h(
      "div",
      { class: "st-split__bar", attrs: { "aria-hidden": "true" } },
      ...parts.map((p, i) => h("span", { class: `st-split__seg st-cat-${Math.min(i, 3)}`, attrs: { style: `flex-grow:${p.n}`, "data-tip": `${p.label}: ${fmt(p.n)} ${what} (${pct(p.share)})` } })),
    ),
    h(
      "ul",
      { class: "st-split__legend" },
      ...parts.map((p, i) => h("li", {}, h("span", { class: `st-key st-cat-${Math.min(i, 3)}`, attrs: { "aria-hidden": "true" } }), h("span", { class: "st-split__name", text: p.label }), h("b", { text: pct(p.share) }))),
    ),
  );
}

// --- the daily columns ---

export interface DayColumn {
  day: string;
  new: number;
  returning: number;
}

/** Pilots per day: new (bottom) and returning (top) stacked, with a light grid and sparse dates. */
export function dailyColumns(days: DayColumn[]): HTMLElement {
  const W = 720;
  const H = 200;
  const padL = 34;
  const padB = 22;
  const padT = 8;
  const max = Math.max(1, ...days.map((d) => d.new + d.returning));
  const step = niceStep(max / 3);
  const top = Math.ceil(max / step) * step;
  const y = (v: number) => padT + (H - padT - padB) * (1 - v / top);
  const slot = (W - padL) / days.length;
  const bw = Math.max(1.5, Math.min(18, slot - 2));
  const g = s("g");
  for (let v = 0; v <= top; v += step) {
    g.append(s("line", { x1: padL, x2: W, y1: y(v), y2: y(v), class: v === 0 ? "st-axis" : "st-grid" }));
    g.append(Object.assign(s("text", { x: padL - 6, y: y(v) + 3.5, class: "st-tick", "text-anchor": "end" }), { textContent: compact(v) }));
  }
  const labelEvery = Math.max(1, Math.ceil(days.length / 7));
  const dayFmt = new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" });
  days.forEach((d, i) => {
    const x = padL + i * slot + (slot - bw) / 2;
    const date = dayFmt.format(new Date(`${d.day}T00:00:00Z`));
    const tip = `${date}: ${fmt(d.new + d.returning)} pilots (${fmt(d.new)} new, ${fmt(d.returning)} returning)`;
    const col = s("g", { "data-tip": tip, class: "st-col" });
    col.append(s("rect", { x: padL + i * slot, y: padT, width: slot, height: H - padT - padB, class: "st-hit" }));
    const r = Math.min(2, bw / 2);
    if (d.new > 0) col.append(s("path", { d: roundTop(x, y(d.new), bw, y(0) - y(d.new), d.returning > 0 ? 0 : r), class: "st-fill-new" }));
    if (d.returning > 0) {
      const y0 = y(d.new) - (d.new > 0 ? 1.5 : 0);
      col.append(s("path", { d: roundTop(x, y(d.new + d.returning), bw, Math.max(0.5, y0 - y(d.new + d.returning)), r), class: "st-fill-returning" }));
    }
    g.append(col);
    if (i % labelEvery === 0) g.append(Object.assign(s("text", { x: x + bw / 2, y: H - 6, class: "st-tick", "text-anchor": "middle" }), { textContent: date }));
  });
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "st-daily", role: "img", "aria-label": `Pilots per day, ${days[0]?.day} to ${days.at(-1)?.day}` }, g);
  return h("div", { class: "st-daily-wrap" }, svg as unknown as HTMLElement);
}

/** A column with only its top corners rounded. */
function roundTop(x: number, y: number, w: number, hgt: number, r: number): string {
  r = Math.min(r, hgt, w / 2);
  return `M${x},${y + hgt}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + hgt}Z`;
}

/** 1, 2, 5 × 10^n at or above `x`. */
export function niceStep(x: number): number {
  if (x <= 1) return 1;
  const p = 10 ** Math.floor(Math.log10(x));
  for (const m of [1, 2, 5, 10]) if (m * p >= x) return m * p;
  return 10 * p;
}

// --- where ships go down ---

/**
 * The player ship's range in the playfield (mainint.c: x 40..256, y 10..160) in death buckets,
 * so the grid has the playfield's proportions and every bucket a ship can die in.
 */
export const FIELD = { x0: 40, x1: 256, y0: 0, y1: 160 };

/** A level's deaths on the playfield: brighter = more ships lost in that 16 px square. */
export function deathGrid(cells: [number, number, number][], bucket: number, label: string): SVGSVGElement {
  const bx0 = Math.floor(FIELD.x0 / bucket);
  const bx1 = Math.floor(FIELD.x1 / bucket);
  const by0 = Math.floor(FIELD.y0 / bucket);
  const by1 = Math.floor(FIELD.y1 / bucket);
  const cols = bx1 - bx0 + 1;
  const rows = by1 - by0 + 1;
  const C = 10;
  const max = Math.max(1, ...cells.map((c) => c[2]));
  const total = cells.reduce((a, c) => a + c[2], 0);
  const svg = s("svg", { viewBox: `-1 -1 ${cols * C + 2} ${rows * C + 2}`, class: "st-grid-map", role: "img", "aria-label": `${label}: ${total} ships lost; where on the playfield` });
  svg.append(s("rect", { x: 0, y: 0, width: cols * C, height: rows * C, class: "st-field" }));
  for (let i = 1; i < cols; i++) svg.append(s("line", { x1: i * C, x2: i * C, y1: 0, y2: rows * C, class: "st-field-line" }));
  for (let j = 1; j < rows; j++) svg.append(s("line", { y1: j * C, y2: j * C, x1: 0, x2: cols * C, class: "st-field-line" }));
  for (const [bx, by, n] of cells) {
    const cx = Math.min(Math.max(bx, bx0), bx1) - bx0;
    const cy = Math.min(Math.max(by, by0), by1) - by0;
    const t = Math.sqrt(n / max); // perceptual: a lone death still shows beside a hot spot
    svg.append(
      s("rect", {
        x: cx * C + 0.75,
        y: cy * C + 0.75,
        width: C - 1.5,
        height: C - 1.5,
        rx: 1.5,
        class: "st-heat",
        style: `--t:${t.toFixed(3)}`,
        "data-tip": `${label}: ${n} ${n === 1 ? "ship" : "ships"} lost here (${Math.round((n / total) * 100)}% of the level's losses)`,
      }),
    );
  }
  return svg;
}
