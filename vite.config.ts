import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { defineConfig, type Plugin } from "vitest/config";

/**
 * Dev server only: serves the local, git-ignored Tyrian data at /tyrian-data/ so the game can be
 * played without the file picker. Never part of a build (DECISIONS.md D3). Set TYRIAN_DATA to
 * point elsewhere (e.g. from a worktree).
 */
function tyrianDataDevServer(): Plugin {
  const dir = resolve(process.env.TYRIAN_DATA ?? "data");
  return {
    name: "tyrian-data-dev-server",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/tyrian-data", (req, res) => {
        if (!existsSync(dir)) {
          res.statusCode = 404;
          res.end("no Tyrian data directory");
          return;
        }
        const name = decodeURIComponent((req.url ?? "/").replace(/^\//, "").split("?")[0]);
        if (name === "" || name === "index.json") {
          const files = readdirSync(dir).filter((f) => statSync(join(dir, f)).isFile());
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(files));
          return;
        }
        const path = join(dir, name);
        if (name.includes("/") || name.includes("\\") || !existsSync(path)) {
          res.statusCode = 404;
          res.end();
          return;
        }
        res.setHeader("Content-Type", "application/octet-stream");
        res.end(readFileSync(path));
      });
    },
  };
}

export default defineConfig({
  // Relative asset URLs so the build works from the GitHub Pages subpath.
  base: "./",
  plugins: [tyrianDataDevServer()],
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
