// Overlay screens around the game: asking for the data, the title, and end-of-level messages.

import "./overlay.css";
import { filesFromZip, type FileMap } from "../assets/files";
import { storeZip } from "../assets/store";

function overlay(html: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "overlay";
  el.innerHTML = `<div class="panel">${html}</div>`;
  document.body.appendChild(el);
  return el;
}

/** Ask the player for tyrian21.zip (DECISIONS.md D3). Resolves once valid data is loaded. */
export function askForData(): Promise<FileMap> {
  const el = overlay(`
    <h1>TYRIAN 3D</h1>
    <p>This game runs on the original <b>Tyrian 2.1</b> data, which isn't included here.</p>
    <p>Download <b>tyrian21.zip</b> (the freeware release; OpenTyrian links to
      <span class="key">camanis.net/tyrian/tyrian21.zip</span>), then choose or drop it below.
      It stays in your browser.</p>
    <label class="drop" tabindex="0">Choose or drop tyrian21.zip
      <input type="file" accept=".zip,application/zip" hidden />
    </label>
    <p class="status"></p>`);
  const drop = el.querySelector<HTMLLabelElement>(".drop")!;
  const input = el.querySelector<HTMLInputElement>("input")!;
  const status = el.querySelector<HTMLParagraphElement>(".status")!;

  return new Promise((resolve) => {
    const accept = async (file: File | undefined) => {
      if (!file) return;
      status.className = "status";
      status.textContent = "Reading…";
      try {
        const zip = new Uint8Array(await file.arrayBuffer());
        const files = await filesFromZip(zip);
        await storeZip(zip);
        el.remove();
        resolve(files);
      } catch (err) {
        status.className = "status error";
        status.textContent = err instanceof Error ? err.message : String(err);
      }
    };
    input.addEventListener("change", () => accept(input.files?.[0]));
    drop.addEventListener("dragover", (e) => {
      e.preventDefault();
      drop.classList.add("over");
    });
    drop.addEventListener("dragleave", () => drop.classList.remove("over"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("over");
      accept(e.dataTransfer?.files[0]);
    });
  });
}

/** Wait for the player to press Enter, Space, a gamepad button, or click. */
function waitForStart(el: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    let raf = 0;
    const done = () => {
      window.removeEventListener("keydown", onKey);
      el.removeEventListener("click", done);
      cancelAnimationFrame(raf);
      el.remove();
      resolve();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Enter" || e.code === "Space") {
        e.preventDefault();
        done();
      }
    };
    // Ignore buttons already held when the screen appears (e.g. fire held through a death).
    let armed = false;
    const poll = () => {
      const pressed = (navigator.getGamepads?.() ?? []).some((p) => p?.buttons.some((b) => b.pressed));
      if (!pressed) armed = true;
      else if (armed) return done();
      raf = requestAnimationFrame(poll);
    };
    window.addEventListener("keydown", onKey);
    el.addEventListener("click", done);
    raf = requestAnimationFrame(poll);
  });
}

export interface TitleChoice {
  episode: number;
  difficulty: number;
}

export interface TitleOptions {
  /** episode_name from the data: [0] is the menu title, [n] episode n. */
  episodeNames: string[];
  /** Episodes whose data is present. */
  episodes: number[];
  /** difficulty_name: [n] is difficulty level n. */
  difficultyNames: string[];
  /** Selectable difficulty levels. */
  difficulties: number[];
  initial: TitleChoice;
  /**
   * Music styles to choose from ("original" first) when a local remaster pack is present (only on
   * local builds); omitted otherwise. `onMusicStyle` switches as soon as one is picked.
   */
  musicStyles?: string[];
  musicStyle?: string;
  onMusicStyle?: (style: string) => void;
}

/** Title screen: pick an episode and difficulty (keyboard, gamepad, click or tap), then start. */
export function showTitle(opts: TitleOptions): Promise<TitleChoice> {
  const el = overlay(`
    <h1>TYRIAN 3D</h1>
    <div class="choices episodes" role="listbox" aria-label="Episode"></div>
    <div class="choices difficulty" role="radiogroup" aria-label="Difficulty"></div>
    <div class="choices music" role="radiogroup" aria-label="Music" hidden></div>
    <p><span class="key">↑↓</span> episode · <span class="key">←→</span> difficulty ·
       <span class="key">Enter</span> start<span class="music-key" hidden> · <span class="key">M</span> music</span></p>
    <p><span class="key">←↑↓→</span> / <span class="key">WASD</span> move · <span class="key">Space</span> fire ·
       mouse, touch and gamepads work too</p>`);
  const episodesEl = el.querySelector<HTMLDivElement>(".episodes")!;
  const difficultyEl = el.querySelector<HTMLDivElement>(".difficulty")!;
  let ep = Math.max(0, opts.episodes.indexOf(opts.initial.episode));
  let diff = Math.max(0, opts.difficulties.indexOf(opts.initial.difficulty));

  const episodeButtons = opts.episodes.map((n, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = opts.episodeNames[n]?.trim() || `Episode ${n}`;
    b.addEventListener("click", () => {
      ep = i;
      render();
      finish();
    });
    episodesEl.appendChild(b);
    return b;
  });
  const difficultyButtons = opts.difficulties.map((n, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = opts.difficultyNames[n]?.trim() || String(n);
    b.addEventListener("click", () => {
      diff = i;
      render();
    });
    difficultyEl.appendChild(b);
    return b;
  });
  // Music style (local remaster packs only).
  const styles = opts.musicStyles ?? [];
  let style = Math.max(0, styles.indexOf(opts.musicStyle ?? "original"));
  const musicEl = el.querySelector<HTMLDivElement>(".music")!;
  const label = (s: string) => `${s[0].toUpperCase()}${s.slice(1)} music`;
  const musicButtons = styles.length > 1 ? styles.map((name, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label(name);
    b.addEventListener("click", () => setStyle(i));
    musicEl.appendChild(b);
    return b;
  }) : [];
  musicEl.hidden = musicButtons.length === 0;
  el.querySelector<HTMLSpanElement>(".music-key")!.hidden = musicButtons.length === 0;
  const setStyle = (i: number) => {
    style = (i + styles.length) % styles.length;
    opts.onMusicStyle?.(styles[style]);
    render();
  };
  const render = () => {
    episodeButtons.forEach((b, i) => b.classList.toggle("selected", i === ep));
    difficultyButtons.forEach((b, i) => b.classList.toggle("selected", i === diff));
    musicButtons.forEach((b, i) => b.classList.toggle("selected", i === style));
  };
  render();

  let resolveFn: (c: TitleChoice) => void = () => {};
  let raf = 0;
  const finish = () => {
    window.removeEventListener("keydown", onKey);
    cancelAnimationFrame(raf);
    el.remove();
    resolveFn({ episode: opts.episodes[ep], difficulty: opts.difficulties[diff] });
  };
  const move = (dEp: number, dDiff: number) => {
    ep = (ep + dEp + episodeButtons.length) % episodeButtons.length;
    diff = Math.min(difficultyButtons.length - 1, Math.max(0, diff + dDiff));
    render();
  };
  const onKey = (e: KeyboardEvent) => {
    const map: Record<string, () => void> = {
      ArrowUp: () => move(-1, 0),
      KeyW: () => move(-1, 0),
      ArrowDown: () => move(1, 0),
      KeyS: () => move(1, 0),
      ArrowLeft: () => move(0, -1),
      KeyA: () => move(0, -1),
      ArrowRight: () => move(0, 1),
      KeyD: () => move(0, 1),
      Enter: finish,
      Space: finish,
      ...(musicButtons.length ? { KeyM: () => setStyle(style + 1) } : {}),
    };
    const action = map[e.code];
    if (!action) return;
    e.preventDefault();
    action();
  };
  // Gamepad: d-pad moves, A starts; act on presses, not holds (and ignore buttons held on entry).
  let prev: boolean[] | null = null;
  const poll = () => {
    const pad = (navigator.getGamepads?.() ?? []).find((p) => p);
    if (pad) {
      const now = pad.buttons.map((b) => b.pressed);
      if (prev) {
        const pressed = (i: number) => now[i] && !prev![i];
        if (pressed(12)) move(-1, 0);
        if (pressed(13)) move(1, 0);
        if (pressed(14)) move(0, -1);
        if (pressed(15)) move(0, 1);
        if (pressed(0) || pressed(9)) return finish();
      }
      prev = now;
    }
    raf = requestAnimationFrame(poll);
  };
  window.addEventListener("keydown", onKey);
  raf = requestAnimationFrame(poll);
  return new Promise((resolve) => (resolveFn = resolve));
}

/** A message screen (level complete, game over); resolves when the player continues. */
export function showMessage(title: string, lines: string[], prompt = "Press Enter to continue"): Promise<void> {
  const body = lines.map((l) => `<p>${l}</p>`).join("");
  const el = overlay(`<h2>${title}</h2>${body}<p><span class="key">${prompt}</span></p>`);
  return waitForStart(el);
}

/** A non-blocking status line (e.g. loading), removed by calling the returned function. */
export function showStatus(text: string): () => void {
  const el = overlay(`<p>${text}</p>`);
  return () => el.remove();
}
