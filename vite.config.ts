import { defineConfig } from "vitest/config";

export default defineConfig({
  // Relative asset URLs so the build works from the GitHub Pages subpath.
  base: "./",
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
