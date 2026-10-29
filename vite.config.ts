import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import type { IncomingMessage, ServerResponse } from "node:http";
import { extname, join, resolve, sep } from "node:path";
import { defineConfig, type Plugin } from "vitest/config";

/** Serve a local folder at a URL path: its files, and index.json listing its top-level files. If the
 * folder doesn't exist, the request goes on to the next handler. */
function serveFolder(dir: string, allowSubfolders: boolean) {
  return (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    // No local folder: fall through to whatever else serves this path (public/tyrian-remaster/).
    if (!existsSync(dir)) return next();
    const name = decodeURIComponent((req.url ?? "/").replace(/^\//, "").split("?")[0]);
    if (name === "" || name === "index.json") {
      const files = readdirSync(dir).filter((f) => statSync(join(dir, f)).isFile());
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(files));
      return;
    }
    const path = resolve(dir, name);
    const inside = path.startsWith(resolve(dir) + sep);
    if (!inside || (!allowSubfolders && (name.includes("/") || name.includes("\\"))) || !existsSync(path) || !statSync(path).isFile()) {
      res.statusCode = 404;
      res.end();
      return;
    }
    const types: Record<string, string> = { ".json": "application/json", ".ogg": "audio/ogg", ".wav": "audio/wav", ".png": "image/png" };
    res.setHeader("Content-Type", types[extname(path)] ?? "application/octet-stream");
    res.end(readFileSync(path));
  };
}

/**
 * Local only: serves the git-ignored Tyrian data at /tyrian-data/ (TYRIAN_DATA, default data/) and,
 * if present, the private remaster pack at /tyrian-remaster/ (TYRIAN_REMASTER, default
 * ../tyrian3d-remaster/out), on the dev server and on `vite preview` (npm run play:local). The
 * private pack (music plus the remade sound effects) shadows the public music-only one in
 * public/tyrian-remaster/ (D40). Nothing private is copied into a build (DECISIONS.md D3, D18).
 */
function localFiles(): Plugin {
  const data = resolve(process.env.TYRIAN_DATA ?? "data");
  const remaster = resolve(process.env.TYRIAN_REMASTER ?? "../tyrian3d-remaster/out");
  const mount = (server: { middlewares: { use(path: string, fn: ReturnType<typeof serveFolder>): void } }) => {
    server.middlewares.use("/tyrian-data", serveFolder(data, false));
    server.middlewares.use("/tyrian-remaster", serveFolder(remaster, true));
  };
  return {
    name: "tyrian-local-files",
    configureServer: mount,
    configurePreviewServer: mount,
  };
}

export default defineConfig({
  // Relative asset URLs so the build works from the GitHub Pages subpath.
  base: "./",
  plugins: [localFiles()],
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
