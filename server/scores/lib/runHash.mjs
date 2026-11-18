// The run hash: a SHA-256 over the run's data, computed by the game when it submits a score and
// re-computed by the server. It is a CONSISTENCY CHECK ONLY: the algorithm ships in the game's
// JavaScript, so anyone can compute a valid hash for any data they like. It catches corrupted or
// hand-edited submissions that forgot to update it, nothing more. It is not security; the
// server's real checks are the run token and the plausibility rules (plausibility.mjs).
//
// Shared by the server (Node 22) and the game (bundled by Vite): Web Crypto only, no Node APIs.

/** The fields the hash covers, in a fixed order (JSON of an array, so key order can't vary). */
export function canonicalRun(run) {
  const item = (w) => [w?.id ?? 0, w?.power ?? 0];
  return JSON.stringify([
    "tyrian3d-run-v1",
    run.token ?? "",
    run.episode,
    run.difficulty,
    run.mode,
    run.tickHz,
    run.ended,
    run.ship,
    item(run.front),
    item(run.rear),
    run.shield,
    run.generator,
    run.sidekicks ?? [],
    (run.levels ?? []).map((l) => [l.lvl, l.ticks, l.score, l.done ? 1 : 0]),
    run.score,
  ]);
}

/** Hex SHA-256 of canonicalRun(run). */
export async function runHash(run) {
  const bytes = new TextEncoder().encode(canonicalRun(run));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
