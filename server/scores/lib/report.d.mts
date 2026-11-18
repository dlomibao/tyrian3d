// The per-level play report the game sends (fire-and-forget) at the end of every level, finished,
// died or quit, when "Share anonymous play stats" is on: POST /api/levels/report. The server
// validates and clamps every field (server/scores/lib/report.mjs). null means "not tracked".

export interface LevelReportItem {
  id: number;
  power: number;
}

export interface ShopTrade {
  /** "buy", "sell" (a slot's item replaced: the old one sold, the new one bought), "upgrade" or "downgrade" (weapon power). */
  kind: "buy" | "sell" | "upgrade" | "downgrade";
  /** ship, front, rear, shield, generator, left, right */
  slot: "ship" | "front" | "rear" | "shield" | "generator" | "left" | "right";
  id: number;
  /** Power level after the trade, for weapons; else 0. */
  power: number;
  /** What it cost (buy, upgrade) or paid back (sell, downgrade): the item's value. */
  price: number;
}

export interface LevelReport {
  v: 1;
  /** The run token from POST /api/runs (reports without one aren't sent). */
  token: string;
  /** Random UUID kept in this browser while stats sharing is on (never derived from the device). */
  playerId: string;
  /** Client build id (git commit or "dev"). */
  build: string;
  /** Any cheat or debug use in this run (the run can't submit scores; its reports are flagged). */
  tainted: boolean;
  run: {
    episode: number;
    /** initialDifficulty */
    difficulty: number;
    /** difficultyLevel when the level started (adjust_difficulty raises it with the score). */
    difficultyNow: number;
    mode: "story" | "arcade" | "twoPlayer" | "superArcade" | "superTyrian";
    /** Sim speed: the port's one rate (~34.8 Hz) times the debug console's speed (1 unless tainted). */
    tickHz: number;
  };
  level: {
    /** lvlFileNum */
    lvl: number;
    name: string;
    /** The script section JE_loadMap started from. */
    section: number;
    /** 0-based position in the run's path (levels finished before this one). */
    index: number;
    /** The previous finished level's lvl, or null for the first. */
    prev: number | null;
    /** How it was reached: the episode's first, the story's next, a choice made in the item screen, an in-level warp, a retry after dying, or a loaded game. */
    via: "start" | "story" | "branch" | "warp" | "retry" | "load";
  };
  loadout: {
    ship: number;
    front: LevelReportItem;
    rear: LevelReportItem;
    /** Left and right sidekicks. */
    sidekicks: [number, number];
    shield: number;
    generator: number;
    armor: number;
    credits: number;
  };
  outcome: {
    result: "finished" | "died" | "quit";
    ticks: number;
    /** JE_totalScore at the end minus at the start. */
    scoreGained: number;
    /** Where the ship was lost (one-player: at most one per attempt). */
    deaths: { tick: number; x: number; y: number }[];
    enemiesKilled: number;
    enemiesSpawned: number;
    bossesKilled: number | null;
    shotsFired: number | null;
    hits: number | null;
    damageTaken: number;
    pickups: number | null;
    coins: number | null;
    cubes: number;
    /** An in-level warp (secret level) was taken. */
    warps: number;
    superbombs: number;
    specials: number | null;
  };
  /** The item screen's trades before this level. */
  shop: ShopTrade[];
}
