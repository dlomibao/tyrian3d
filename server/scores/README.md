# Tyrian 3D scores service

The shared high-score list and the anonymous play stats for Tyrian 3D. One small Node 22 process,
no dependencies: `node:http` plus the built-in `node:sqlite`. It sits behind nginx on the game's
site at `/api/`.

- **High scores.** The game asks for a run token when a story-mode game starts (`POST /api/runs`)
  and keeps it in the save. When the run ends it submits the run (`POST /api/scores`). The server
  checks the token, re-computes the run hash (`lib/runHash.mjs`, a consistency check only) and
  checks that the run was possible (`lib/plausibility.mjs` against `maxScores.json`). A plausible
  run goes on the list, and anything else goes in `rejected`. There is no replay: `verified` is
  `'plausible'`.
- **Play stats.** With "Share anonymous play stats" on, the game sends a report at the end of each
  level (`POST /api/levels/report`, shape in `lib/report.d.mts`). `GET /api/stats/summary` sums
  them up.
- **Privacy.** No IP address is ever stored. An address is used for two things only, during the
  request:
  - the rate limit, through an in-memory key `HMAC-SHA256(SCORES_IP_SALT + "|" + UTC 'YYYY-MM',
    address)`. An IPv6 address is cut to its /64 first. The key changes every month.
  - a lookup of its 2-letter country.

  Rate-limit state is memory only. IP hashes and player ids are kept in separate maps and are
  never joined. The player id is a random UUID the browser keeps while stats sharing is on.

## Files

| Path | What |
|---|---|
| `server.mjs` | Entry point and HTTP routes (`createServer(config)`, `start()`) |
| `lib/config.mjs` | Environment → config |
| `lib/db.mjs` | Opens SQLite (WAL, busy timeout) and runs migrations keyed by `PRAGMA user_version` |
| `lib/token.mjs` | Run tokens (HMAC-signed) |
| `lib/validate.mjs` | Validation for runs and scores, and the name rule |
| `lib/report.mjs` | Validating, clamping and storing level reports |
| `lib/stats.mjs` | The summary aggregates |
| `lib/geo.mjs` | IP → country (DB-IP Lite ranges) |
| `lib/ratelimit.mjs` | Salted monthly IP hash and fixed-window limiter |
| `lib/http.mjs` | Body limit, JSON replies, client address |
| `lib/plausibility.mjs`, `lib/runHash.mjs`, `maxScores.json` | Run checks (made by `tools/maxScores/maxScores.ts`) |
| `tools/load-geo.mjs` | (Re)loads the DB-IP CSV into the `geo` table |
| `tools/backup.mjs` | Dated `VACUUM INTO` backup that keeps the newest N |
| `ecosystem.config.cjs` | pm2 app (placeholders) |

Tests: `tests/server/*.test.ts`. Run them with
`NODE_OPTIONS= npx vitest run tests/server --no-fsModuleCache`.

## Configuration (environment)

| Variable | Default | |
|---|---|---|
| `SCORES_HMAC_SECRET` | required | Signs run tokens. At least 32 characters, or the service won't start. |
| `SCORES_IP_SALT` | required | Salt for the rate-limit IP hash. At least 16 characters. |
| `PORT` | `8787` | `0` = a random port. On start the service prints `{"listening":<port>}` on stdout. |
| `HOST` | `127.0.0.1` | Listen address (only nginx talks to it). |
| `SCORES_DB` | `$HOME/apps/tyrian-scores/scores.db` | SQLite file (`-wal` and `-shm` sit next to it) |
| `SCORES_MAX_SCORES` | `./maxScores.json` next to `server.mjs` | |
| `SCORES_TRUST_PROXY` | `loopback` | Whose `X-Real-IP` / `X-Forwarded-For` to believe. `loopback`: only a peer at 127.0.0.1, ::1 or ::ffff:127.0.0.1. `none`: never. Or a comma-separated list of peer addresses. `X-Real-IP` wins; otherwise the **last** `X-Forwarded-For` entry (the one nginx added). |
| `SCORES_CORS_ORIGIN` | unset | Optional. Allows one cross-origin caller, such as a dev server. Not needed when the game and `/api/` are on the same site. |

Rate limits per hour, counted separately per IP hash and per player id: runs 30, scores 10,
reports 600, GETs 1200 (health isn't limited). Over the limit the reply is 429 with
`Retry-After`. A run token takes at most 200 level reports.

## Endpoints

| | Body / query | Reply |
|---|---|---|
| `POST /api/runs` | `{episode 1-4, difficulty 1,2,3,4,6,8, mode "story"\|"arcade"\|"twoPlayer"\|"superArcade"\|"superTyrian", build ≤40 printable ASCII, playerId? UUID v4}` | `200 {token, issuedAt}` · 400 |
| `POST /api/scores` | RunData (`lib/runHash.d.mts`) + `name` + `hash` (≤ 32 KB) | `200 {ok, rank, total}` · `400 {ok:false, reason:"invalid"\|"mode", error}` · `422 {ok:false, reason}` |
| `GET /api/scores?episode=E[&difficulty=D]` | | `{episode, difficulty, scores:[{rank, name, score, difficulty, levels, date}]}` (the top 20) |
| `POST /api/levels/report` | LevelReport (`lib/report.d.mts`), any Content-Type | `204` · 400 invalid · 403 `token`/`expired`/`mismatch` · 429 `rate-limited`/`cap`/`unknown-run` |
| `GET /api/stats/summary` | | The summary (below), cached for 10 minutes |
| `GET /api/health` | | `{ok:true, db:true}` |

**How a score is checked, in order:**

1. The body is validated (400s are not stored).
2. The token is checked. It must be:
   - correctly signed (else `token`),
   - no more than 30 days old (else `expired`),
   - for the body's episode, difficulty and mode (else `mismatch`),
   - issued by this server (else `unknown-run`),
   - not used yet (else `reused`).
3. From here on, the token is spent, whether the run is then accepted or rejected.
4. The run hash is compared (else `hash`).
5. `checkRun` runs, which can reject with `path`, `ticks`, `wall`, `cap`, `level` or `rate`.

Every 422 adds a row to `rejected`.

The rest of the score rules:

- Only `mode: "story"` is ranked.
- `tickHz` must equal `maxScores.json`'s within 1e-6.
- Names follow the game's name entry (`highScoreNameAccepts`): characters it wouldn't accept are
  dropped, runs of spaces are collapsed, the name is trimmed and cut to 28 characters. A name
  that ends up empty is a 400.
- `rank` counts within the run's episode and difficulty. On a tie the earlier score ranks first.
- `levels` in the list is the number of finished levels.

**Level reports:**

- These must be valid, or the report is rejected: `v`, the player id (UUID v4), episode,
  difficulty, mode, `lvl`, `via`, `result`, the 2 sidekicks.
- Counts are cut down to fixed ranges.
- Strings are kept to printable ASCII (build ≤ 40 characters, level name ≤ 32).
- `deaths` keeps the first 20 entries (x and y clamped to 0..511) and `shop` the first 100.
- The token must be correctly signed, no more than 60 days old, and match the report's episode,
  difficulty and mode.
- Tainted reports are stored with `tainted = 1`.

### Summary

```
{ generatedAt, deathBucketPx: 16,
  reports: {total, tainted}, runs: {total, submitted},
  paths:       {episode: [{from: prev|null, to: lvl, n}]},            // "retry" entries aren't transitions
  outcomes:    {episode: {lvl: {difficulty: {finished, died, quit}}}},
  deaths:      {episode: {lvl: [[bx, by, n]]}},                       // bx = floor(x / 16)
  weapons:     {episode: {lvl: {frontId: n}}},  ships: {episode: {lvl: {ship: n}}},
  scoreGained: {episode: {lvl: {n, p25, p50, p75, p90}}},             // finished levels; nearest rank
  shop:        {kind: {slot: {itemId: n}}},
  countries:   {runs: {CC: n}, reports: {CC: n}, runsByMonth: {YYYY-MM: {CC: n}}, reportsByMonth: {...}},
  players:     {total, perDay: [{day, players, new, returning}], perMonth: [{month, players, new, returning}],
                runsPerPlayer: {runs: players}, daysPerPlayer: {days: players}},
  funnel:      {episode: {k: players who reached at least the k-th level of the run}} }
```

- Gameplay aggregates leave out tainted reports: paths, outcomes, deaths, weapons, ships,
  scoreGained, shop and funnel.
- Country and player counts include tainted reports.
- On a day, a player is "returning" if they were first seen on an earlier day.
- In a month, a player is "returning" if they were first seen in an earlier month.

## Database schema

SQLite in WAL mode, `busy_timeout` 5000 ms. `lib/db.mjs` holds the migrations, and
`PRAGMA user_version` is the schema version (currently 1). Every value is bound through a
prepared statement.

```sql
CREATE TABLE runs (id TEXT PRIMARY KEY,            -- the token id (16 random bytes, hex)
  issued_at INTEGER NOT NULL, episode INTEGER NOT NULL, difficulty INTEGER NOT NULL,
  mode TEXT NOT NULL, build TEXT NOT NULL, player_id TEXT, country TEXT NOT NULL,
  used_at INTEGER, report_count INTEGER NOT NULL DEFAULT 0);
CREATE INDEX runs_player ON runs (player_id);  CREATE INDEX runs_country ON runs (country);

CREATE TABLE scores (id INTEGER PRIMARY KEY, run_id TEXT NOT NULL UNIQUE REFERENCES runs (id),
  name TEXT NOT NULL, score INTEGER NOT NULL, episode INTEGER NOT NULL, difficulty INTEGER NOT NULL,
  ended TEXT NOT NULL, levels TEXT NOT NULL,      -- JSON [{lvl, ticks, score, done}]
  level_count INTEGER NOT NULL, ticks INTEGER NOT NULL, cap INTEGER NOT NULL,
  verified TEXT NOT NULL DEFAULT 'plausible', created_at INTEGER NOT NULL, country TEXT NOT NULL);
CREATE INDEX scores_board ON scores (episode, difficulty, score DESC, created_at);
CREATE INDEX scores_episode ON scores (episode, score DESC, created_at);

CREATE TABLE rejected (id INTEGER PRIMARY KEY, created_at INTEGER NOT NULL, reason TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '', run_id TEXT, episode INTEGER, difficulty INTEGER, score INTEGER,
  country TEXT NOT NULL);
CREATE INDEX rejected_reason ON rejected (reason);

CREATE TABLE levels (id INTEGER PRIMARY KEY, created_at INTEGER NOT NULL,
  month TEXT NOT NULL, day TEXT NOT NULL,         -- UTC 'YYYY-MM', 'YYYY-MM-DD'
  run_id TEXT NOT NULL, player_id TEXT NOT NULL, country TEXT NOT NULL, build TEXT NOT NULL,
  tainted INTEGER NOT NULL, episode INTEGER NOT NULL, difficulty INTEGER NOT NULL,
  difficulty_now INTEGER NOT NULL, mode TEXT NOT NULL, tick_hz REAL NOT NULL,
  lvl INTEGER NOT NULL, name TEXT NOT NULL, section INTEGER NOT NULL, idx INTEGER NOT NULL,
  prev INTEGER, via TEXT NOT NULL, ship INTEGER NOT NULL, front_id INTEGER NOT NULL,
  front_power INTEGER NOT NULL, rear_id INTEGER NOT NULL, rear_power INTEGER NOT NULL,
  sidekick_l INTEGER NOT NULL, sidekick_r INTEGER NOT NULL, shield INTEGER NOT NULL,
  generator INTEGER NOT NULL, armor INTEGER NOT NULL, credits INTEGER NOT NULL,
  result TEXT NOT NULL, ticks INTEGER NOT NULL, score_gained INTEGER NOT NULL,
  enemies_killed INTEGER NOT NULL, enemies_spawned INTEGER NOT NULL, bosses_killed INTEGER,
  shots_fired INTEGER, hits INTEGER, damage_taken INTEGER NOT NULL, pickups INTEGER,
  coins INTEGER, cubes INTEGER NOT NULL, warps INTEGER NOT NULL, superbombs INTEGER NOT NULL,
  specials INTEGER,                               -- null columns: not tracked by the client
  deaths TEXT);                                   -- JSON [[tick, x, y]], null when none
CREATE INDEX levels_lvl ON levels (lvl, episode);   CREATE INDEX levels_difficulty ON levels (difficulty);
CREATE INDEX levels_month ON levels (month, country); CREATE INDEX levels_player ON levels (player_id, day);
CREATE INDEX levels_country ON levels (country);

CREATE TABLE shop_trades (level_id INTEGER NOT NULL REFERENCES levels (id), tainted INTEGER NOT NULL,
  kind TEXT NOT NULL, slot TEXT NOT NULL, item_id INTEGER NOT NULL, power INTEGER NOT NULL,
  price INTEGER NOT NULL);
CREATE INDEX shop_trades_item ON shop_trades (kind, slot, item_id);
CREATE INDEX shop_trades_level ON shop_trades (level_id);

CREATE TABLE geo (start BLOB PRIMARY KEY, end BLOB NOT NULL, country TEXT NOT NULL) WITHOUT ROWID;
-- start/end: 16-byte addresses (IPv4 as ::ffff:a.b.c.d), so BLOB order is address order
```

## Deploying (pm2)

Layout on the server, where `<user>` is the account that runs pm2:

```
~/apps/tyrian-scores/
  app/          a copy of server/scores/ (server.mjs, lib/, tools/, maxScores.json, ecosystem.config.cjs)
  scores.env    chmod 600: secrets and port
  scores.db     (+ -wal, -shm)
  backups/
  geo/          the downloaded DB-IP CSV
```

1. **Copy the code:**
   `rsync -a server/scores/ <host>:apps/tyrian-scores/app/`
2. **Create the env file**, once:
   ```sh
   cd ~/apps/tyrian-scores
   umask 077
   printf 'SCORES_HMAC_SECRET=%s\nSCORES_IP_SALT=%s\nPORT=8787\nSCORES_DB=%s\n' \
     "$(openssl rand -hex 32)" "$(openssl rand -hex 24)" "$HOME/apps/tyrian-scores/scores.db" > scores.env
   chmod 600 scores.env
   ```
   Changing `SCORES_HMAC_SECRET` invalidates every run token in players' saves. Changing
   `SCORES_IP_SALT` only resets the rate limits.
3. **Check the system Node:** `/usr/bin/node --version` must be v22.13 or newer
   (`node:sqlite` without a flag).
4. **Start it under pm2.** pm2 itself runs under nvm's Node 18. `ecosystem.config.cjs` therefore
   sets `interpreter: "none"` and `script: "/usr/bin/node"`, with args
   `--env-file=/home/<user>/apps/tyrian-scores/scores.env server.mjs`. Replace `<user>` in it,
   then:
   ```sh
   source ~/.nvm/nvm.sh
   cd ~/apps/tyrian-scores/app && pm2 start ecosystem.config.cjs && pm2 save
   curl -s http://127.0.0.1:8787/api/health      # {"ok":true,"db":true}
   ```
   To update, rsync the code and run `pm2 restart tyrian-scores`. Migrations run on start.

## nginx

Two parts. They are also in `tyrian-scratch/shared-scores/nginx-tyrian-scores.conf`.

**Part 1: the rate-limit zone.** `limit_req_zone` is only valid in the `http{}` context, so it
goes in its own file, `/etc/nginx/conf.d/tyrian-scores-ratelimit.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=tyrian_scores:10m rate=5r/s;
limit_req_status 429;
```

**Part 2: the location block.** Add it to the tyrian3d site's `server{}` block, through its extra
snippet or template in the lomibao.net infra repo:

```nginx
location /api/ {
    limit_req zone=tyrian_scores burst=20 nodelay;
    proxy_pass http://127.0.0.1:8787;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
    client_max_body_size 64k;
}
```

Then run `sudo nginx -t && sudo systemctl reload nginx`.

## Backups

Run `node tools/backup.mjs [db] [dir] [keep]`. It writes `backups/scores-YYYY-MM-DD.db` with
`VACUUM INTO`, which is safe while the service runs, and keeps the newest 30.

Cron line (`crontab -e`), daily at 03:15:

```
15 3 * * * cd /home/<user>/apps/tyrian-scores/app && /usr/bin/node --disable-warning=ExperimentalWarning tools/backup.mjs /home/<user>/apps/tyrian-scores/scores.db /home/<user>/apps/tyrian-scores/backups 30 >> /home/<user>/apps/tyrian-scores/backup.log 2>&1
```

## Geo table (monthly)

Countries come from DB-IP's free "IP to Country Lite" database.

> IP geolocation by [DB-IP](https://db-ip.com) (CC BY 4.0)

This credit must appear wherever the stats are shown (and in CREDITS.md).

**Monthly refresh.** DB-IP publishes a new file early each month.

1. **Download (manual).** Get the "IP to Country Lite" CSV for the month from
   https://db-ip.com/db/download/ip-to-country-lite. The file is `dbip-country-lite-YYYY-MM.csv.gz`.
   Put it in `~/apps/tyrian-scores/geo/` and `gunzip` it.
2. **Load it:**
   ```sh
   cd ~/apps/tyrian-scores/app
   /usr/bin/node --disable-warning=ExperimentalWarning tools/load-geo.mjs \
     ../geo/dbip-country-lite-YYYY-MM.csv ../scores.db
   ```
   This prints `{"rows":…,"skipped":…}`. It fills a new table in chunks and swaps it in, so the
   service can keep running.
3. Delete the old CSV.

Until a table is loaded, every country is `ZZ`.
