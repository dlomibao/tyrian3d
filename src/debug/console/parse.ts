// The debug console's command line (D109): splitting a line into words, finding the command, tab
// completion and the input history. Pure, so it is tested without a page.

/** What the console knows of a command to parse, complete and list it. */
export interface CommandSpec {
  name: string;
  aliases?: readonly string[];
  /** The arguments, as `help` shows them: `front|rear <id> [power]`. */
  usage: string;
  /** One line for `help`. */
  help: string;
  /** Words that may come at argument `index` (0-based) after `args` so far, for tab completion. */
  complete?(index: number, args: readonly string[]): readonly string[];
}

/** Split a line into words: spaces separate, "double" or 'single' quotes keep spaces in one word. */
export function tokenize(line: string): string[] {
  const out: string[] = [];
  const re = /"([^"]*)"?|'([^']*)'?|(\S+)/g;
  for (let m = re.exec(line); m; m = re.exec(line)) out.push(m[1] ?? m[2] ?? m[3]);
  return out;
}

/** The command a word names (its name or an alias, any case), or undefined. */
export function findCommand<T extends CommandSpec>(specs: readonly T[], word: string): T | undefined {
  const w = word.toLowerCase();
  return specs.find((c) => c.name === w || c.aliases?.includes(w));
}

/** The longest start every word shares. */
export function commonPrefix(words: readonly string[]): string {
  if (!words.length) return "";
  let p = words[0];
  for (const w of words) while (!w.toLowerCase().startsWith(p.toLowerCase())) p = p.slice(0, -1);
  return p;
}

export interface Completion {
  /** The line with the word under completion extended (or finished, with a space after). */
  line: string;
  /** Every word that fits, when more than one does (to list them). */
  options: string[];
}

/**
 * Tab on `line` (the cursor at its end): the first word completes to a command, later ones to what
 * the command's complete() offers. One fit finishes the word and adds a space; several extend it to
 * what they share and list them.
 */
export function completeLine(specs: readonly CommandSpec[], line: string): Completion {
  const endsInSpace = /\s$/.test(line) || line === "";
  const words = tokenize(line);
  const current = endsInSpace ? "" : (words.pop() ?? "");
  const head = line.slice(0, line.length - current.length);
  let candidates: readonly string[];
  if (words.length === 0) {
    candidates = specs.flatMap((c) => [c.name, ...(c.aliases ?? [])]);
  } else {
    const cmd = findCommand(specs, words[0]);
    candidates = cmd?.complete?.(words.length - 1, words.slice(1)) ?? [];
  }
  const fits = [...new Set(candidates.filter((c) => c.toLowerCase().startsWith(current.toLowerCase())))].sort();
  if (fits.length === 0) return { line, options: [] };
  if (fits.length === 1) return { line: `${head}${fits[0]} `, options: [] };
  const shared = commonPrefix(fits);
  return { line: `${head}${shared.length > current.length ? shared : current}`, options: fits };
}

/**
 * The `help` lines: each command with its arguments, a tab, then what it does (the console lays the
 * two out as columns, or one under the other on a phone).
 */
export function helpLines(specs: readonly CommandSpec[]): string[] {
  return specs.map((c) => `${[c.name, ...(c.aliases ?? [])].join("/")}${c.usage ? ` ${c.usage}` : ""}\t${c.help}`);
}

/**
 * The input history: Up goes back through earlier lines, Down forward again, past the newest to
 * what was being typed. A line repeating the one before isn't kept twice.
 */
export class History {
  private pos: number;
  private draft = "";

  constructor(
    readonly lines: string[] = [],
    private readonly max = 100,
  ) {
    this.pos = lines.length;
  }

  push(line: string): void {
    const l = line.trim();
    if (l && this.lines.at(-1) !== l) this.lines.push(l);
    while (this.lines.length > this.max) this.lines.shift();
    this.pos = this.lines.length;
    this.draft = "";
  }

  /** Up: the line before; `current` is kept as the draft when leaving it. */
  up(current: string): string {
    if (this.pos === this.lines.length) this.draft = current;
    if (this.pos > 0) this.pos--;
    return this.lines[this.pos] ?? current;
  }

  /** Down: the line after, or the draft past the newest. */
  down(current: string): string {
    if (this.pos >= this.lines.length) return current;
    this.pos++;
    return this.pos === this.lines.length ? this.draft : this.lines[this.pos];
  }
}
