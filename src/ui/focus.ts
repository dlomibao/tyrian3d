// Moving the focused item of a list. Pure, so it's tested without a browser.

export interface FocusOptions {
  /** Wrap from the last item to the first and back (default true). */
  wrap?: boolean;
  /** Items the focus skips (disabled rows). */
  skip?: (index: number) => boolean;
}

/**
 * The index `delta` steps from `from` among `count` items, skipping `skip`ped ones. Without wrap it
 * stops at the ends. If every item is skipped, the focus stays where it is.
 */
export function moveFocus(count: number, from: number, delta: number, opts: FocusOptions = {}): number {
  const { wrap = true, skip = () => false } = opts;
  if (count <= 0) return -1;
  const step = Math.sign(delta);
  if (step === 0) return from;
  let at = from;
  for (let moved = 0; moved < Math.abs(delta); moved++) {
    let next = at;
    for (let tries = 0; tries < count; tries++) {
      next += step;
      if (next < 0 || next >= count) {
        if (!wrap) {
          next = -1;
          break;
        }
        next = (next + count) % count;
      }
      if (!skip(next)) break;
      if (tries === count - 1) next = -1;
    }
    if (next < 0) break;
    at = next;
  }
  return at;
}

/** The first index that isn't skipped at or after `from` (wrapping), or -1. */
export function firstFocusable(count: number, from: number, skip: (index: number) => boolean = () => false): number {
  for (let i = 0; i < count; i++) {
    const at = (((from + i) % count) + count) % count;
    if (!skip(at)) return at;
  }
  return -1;
}
