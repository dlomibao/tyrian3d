// The SQLite database (Node 22's built-in node:sqlite): WAL, a busy timeout, and schema migrations
// keyed by PRAGMA user_version. Every value goes through a prepared statement.
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { DatabaseSync } from "node:sqlite";

/** Migrations, in order: user_version N means the first N have run. Append only. */
const MIGRATIONS = [
  `
  -- A run token's row: issued by POST /api/runs, consumed by one POST /api/scores.
  CREATE TABLE runs (
    id           TEXT PRIMARY KEY,           -- the token's id (16 random bytes, hex)
    issued_at    INTEGER NOT NULL,           -- ms since the epoch
    episode      INTEGER NOT NULL,
    difficulty   INTEGER NOT NULL,           -- initial difficulty
    mode         TEXT NOT NULL,
    build        TEXT NOT NULL,
    player_id    TEXT,                       -- only when the player shares stats
    country      TEXT NOT NULL,              -- 2 letters, 'ZZ' unknown
    used_at      INTEGER,                    -- set when a score submission consumed the token
    report_count INTEGER NOT NULL DEFAULT 0  -- level reports sent with this token (cap 200)
  );
  CREATE INDEX runs_player ON runs (player_id);
  CREATE INDEX runs_country ON runs (country);

  -- Accepted scores: the shared high-score list.
  CREATE TABLE scores (
    id          INTEGER PRIMARY KEY,
    run_id      TEXT NOT NULL UNIQUE REFERENCES runs (id),
    name        TEXT NOT NULL,
    score       INTEGER NOT NULL,
    episode     INTEGER NOT NULL,
    difficulty  INTEGER NOT NULL,
    ended       TEXT NOT NULL,               -- 'quit' or 'episode'
    levels      TEXT NOT NULL,               -- JSON [{lvl, ticks, score, done}]
    level_count INTEGER NOT NULL,            -- finished levels
    ticks       INTEGER NOT NULL,            -- summed level ticks
    cap         INTEGER NOT NULL,            -- the plausibility bound the score passed
    verified    TEXT NOT NULL DEFAULT 'plausible',
    created_at  INTEGER NOT NULL,
    country     TEXT NOT NULL
  );
  CREATE INDEX scores_board ON scores (episode, difficulty, score DESC, created_at);
  CREATE INDEX scores_episode ON scores (episode, score DESC, created_at);

  -- Rejected submissions (bad token, hash, plausibility), kept for tuning the bounds.
  CREATE TABLE rejected (
    id          INTEGER PRIMARY KEY,
    created_at  INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    run_id      TEXT,
    episode     INTEGER,
    difficulty  INTEGER,
    score       INTEGER,
    country     TEXT NOT NULL
  );
  CREATE INDEX rejected_reason ON rejected (reason);

  -- One row per level report (POST /api/levels/report), flattened for the summary's GROUP BYs.
  CREATE TABLE levels (
    id              INTEGER PRIMARY KEY,
    created_at      INTEGER NOT NULL,
    month           TEXT NOT NULL,           -- 'YYYY-MM' (UTC)
    day             TEXT NOT NULL,           -- 'YYYY-MM-DD' (UTC)
    run_id          TEXT NOT NULL,
    player_id       TEXT NOT NULL,
    country         TEXT NOT NULL,
    build           TEXT NOT NULL,
    tainted         INTEGER NOT NULL,        -- 1: cheat/debug used in the run
    episode         INTEGER NOT NULL,
    difficulty      INTEGER NOT NULL,
    difficulty_now  INTEGER NOT NULL,
    mode            TEXT NOT NULL,
    tick_hz         REAL NOT NULL,
    lvl             INTEGER NOT NULL,
    name            TEXT NOT NULL,
    section         INTEGER NOT NULL,
    idx             INTEGER NOT NULL,
    prev            INTEGER,
    via             TEXT NOT NULL,
    ship            INTEGER NOT NULL,
    front_id        INTEGER NOT NULL,
    front_power     INTEGER NOT NULL,
    rear_id         INTEGER NOT NULL,
    rear_power      INTEGER NOT NULL,
    sidekick_l      INTEGER NOT NULL,
    sidekick_r      INTEGER NOT NULL,
    shield          INTEGER NOT NULL,
    generator       INTEGER NOT NULL,
    armor           INTEGER NOT NULL,
    credits         INTEGER NOT NULL,
    result          TEXT NOT NULL,           -- 'finished', 'died', 'quit'
    ticks           INTEGER NOT NULL,
    score_gained    INTEGER NOT NULL,
    enemies_killed  INTEGER NOT NULL,
    enemies_spawned INTEGER NOT NULL,
    bosses_killed   INTEGER,                 -- null: not tracked
    shots_fired     INTEGER,
    hits            INTEGER,
    damage_taken    INTEGER NOT NULL,
    pickups         INTEGER,
    coins           INTEGER,
    cubes           INTEGER NOT NULL,
    warps           INTEGER NOT NULL,
    superbombs      INTEGER NOT NULL,
    specials        INTEGER,
    deaths          TEXT                     -- JSON [[tick, x, y], ...], null when none
  );
  CREATE INDEX levels_lvl ON levels (lvl, episode);
  CREATE INDEX levels_difficulty ON levels (difficulty);
  CREATE INDEX levels_month ON levels (month, country);
  CREATE INDEX levels_player ON levels (player_id, day);
  CREATE INDEX levels_country ON levels (country);

  -- The item screen's trades before a level (a report's shop[]).
  CREATE TABLE shop_trades (
    level_id INTEGER NOT NULL REFERENCES levels (id),
    tainted  INTEGER NOT NULL,
    kind     TEXT NOT NULL,                  -- buy, sell, upgrade, downgrade
    slot     TEXT NOT NULL,                  -- ship, front, rear, shield, generator, left, right
    item_id  INTEGER NOT NULL,
    power    INTEGER NOT NULL,
    price    INTEGER NOT NULL
  );
  CREATE INDEX shop_trades_item ON shop_trades (kind, slot, item_id);
  CREATE INDEX shop_trades_level ON shop_trades (level_id);

  -- DB-IP "IP to Country Lite" ranges (tools/load-geo.mjs). start/end are 16-byte BLOBs (IPv4 as
  -- ::ffff:a.b.c.d) so memcmp order is address order.
  CREATE TABLE geo (
    start   BLOB PRIMARY KEY,
    end     BLOB NOT NULL,
    country TEXT NOT NULL
  ) WITHOUT ROWID;
  `,
];

export const SCHEMA_VERSION = MIGRATIONS.length;

/** Open (creating if needed) the database at `path` and bring its schema up to date. */
export function openDb(path) {
  if (path !== ":memory:") mkdirSync(dirname(path), { recursive: true });
  const db = new DatabaseSync(path);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec("PRAGMA busy_timeout = 5000");
  db.exec("PRAGMA synchronous = NORMAL");
  db.exec("PRAGMA foreign_keys = ON");
  migrate(db);
  return db;
}

function migrate(db) {
  const version = db.prepare("PRAGMA user_version").get().user_version;
  if (version > MIGRATIONS.length) throw new Error(`database schema ${version} is newer than this server (${MIGRATIONS.length})`);
  for (let v = version; v < MIGRATIONS.length; v++) {
    db.exec("BEGIN IMMEDIATE");
    try {
      db.exec(MIGRATIONS[v]);
      db.exec(`PRAGMA user_version = ${v + 1}`); // a constant, not user input (PRAGMA can't bind)
      db.exec("COMMIT");
    } catch (e) {
      db.exec("ROLLBACK");
      throw e;
    }
  }
}

/** Run `fn` in a transaction. */
export function transaction(db, fn) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const r = fn();
    db.exec("COMMIT");
    return r;
  } catch (e) {
    db.exec("ROLLBACK");
    throw e;
  }
}
