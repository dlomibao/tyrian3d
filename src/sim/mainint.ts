// STUB: replaced by the player port.
// Only the signatures the world port (tyrian2.ts) calls, so it typechecks on its own branch.

import { g } from "./state";

/**
 * JE_drawTextWindow (mainint.c L76-83): shows `text` in the in-game message bar for 100 ticks.
 * The bar is HTML, so this only sets the state it reads.
 */
export function JE_drawTextWindow(text: string): void {
  g.textErase = 100;
  g.messageText = text;
}
