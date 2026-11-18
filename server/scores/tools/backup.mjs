#!/usr/bin/env node
// A consistent copy of the scores database (VACUUM INTO, safe while the server runs), named by the
// UTC date, keeping the newest N.
//
//   node tools/backup.mjs [scores.db] [backup dir] [keep]
//
// Defaults: SCORES_DB or ~/apps/tyrian-scores/scores.db, ~/apps/tyrian-scores/backups, 30.
import { existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";

const home = join(homedir(), "apps", "tyrian-scores");
const [dbArg, dirArg, keepArg] = process.argv.slice(2);
const dbPath = dbArg || process.env.SCORES_DB || join(home, "scores.db");
const dir = dirArg || join(home, "backups");
const keep = Math.max(1, Number(keepArg) || 30);

mkdirSync(dir, { recursive: true });
const out = join(dir, `scores-${new Date().toISOString().slice(0, 10)}.db`);
if (existsSync(out)) rmSync(out); // VACUUM INTO won't overwrite: today's run replaces today's copy
const db = new DatabaseSync(dbPath, { readOnly: true });
db.exec("PRAGMA busy_timeout = 10000");
db.prepare("VACUUM INTO ?").run(out);
db.close();

const old = readdirSync(dir).filter((f) => /^scores-\d{4}-\d{2}-\d{2}\.db$/.test(f)).sort().slice(0, -keep);
for (const f of old) rmSync(join(dir, f));
console.log(JSON.stringify({ backup: out, removed: old.length }));
