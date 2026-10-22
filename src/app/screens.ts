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

export function showTitle(): Promise<void> {
  const el = overlay(`
    <h1>TYRIAN 3D</h1>
    <p>Episode 1 — Escape</p>
    <p><span class="key">←↑↓→</span> / <span class="key">WASD</span> move ·
       <span class="key">Space</span> fire · gamepad works too</p>
    <p>Press <span class="key">Enter</span> to start</p>`);
  return waitForStart(el);
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
