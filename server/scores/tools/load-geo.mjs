#!/usr/bin/env node
// (Re)load the DB-IP "IP to Country Lite" CSV (ip_start,ip_end,country; IPv4 and IPv6; CC BY 4.0,
// "IP geolocation by DB-IP", https://db-ip.com) into the scores database's geo table.
//
//   node tools/load-geo.mjs <dbip-country-lite.csv> [scores.db]
//
// The database defaults to SCORES_DB, else ~/apps/tyrian-scores/scores.db. Safe while the server
// runs: the new table is filled in chunks and swapped in with one short transaction.
import { readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { openDb } from "../lib/db.mjs";
import { loadGeo } from "../lib/geo.mjs";

export { loadGeo };

/** Load `csvPath` into the database at `dbPath`. Returns {rows, skipped}. */
export function loadGeoFile(csvPath, dbPath) {
  const db = openDb(dbPath);
  try {
    return loadGeo(db, readFileSync(csvPath, "utf8").split(/\r?\n/));
  } finally {
    db.close();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  const [csv, dbArg] = process.argv.slice(2);
  if (!csv) {
    console.error("usage: node tools/load-geo.mjs <dbip-country-lite.csv> [scores.db]");
    process.exit(2);
  }
  const dbPath = dbArg || process.env.SCORES_DB || join(homedir(), "apps", "tyrian-scores", "scores.db");
  const { rows, skipped } = loadGeoFile(csv, dbPath);
  console.log(JSON.stringify({ rows, skipped }));
  if (rows === 0) process.exit(1);
}
