// Configuration from the environment (README.md "Configuration").
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

/** Rate limits per hour, per salted IP hash and (separately) per player id. */
export const DEFAULT_LIMITS = {
  runs: 30,
  scores: 10,
  reports: 600,
  get: 1200,
};

/**
 * Read the config from `env` (process.env). Throws when a required secret is missing or weak, so
 * the service refuses to start.
 */
export function loadConfig(env = process.env) {
  const secret = env.SCORES_HMAC_SECRET ?? "";
  if (secret.length < 32) throw new Error("SCORES_HMAC_SECRET must be set and at least 32 characters");
  const salt = env.SCORES_IP_SALT ?? "";
  if (salt.length < 16) throw new Error("SCORES_IP_SALT must be set and at least 16 characters");
  const port = env.PORT === undefined || env.PORT === "" ? 8787 : Number(env.PORT);
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error(`bad PORT ${env.PORT}`);
  return {
    port,
    host: env.HOST || "127.0.0.1",
    dbPath: env.SCORES_DB || join(homedir(), "apps", "tyrian-scores", "scores.db"),
    hmacSecret: secret,
    ipSalt: salt,
    maxScoresPath: env.SCORES_MAX_SCORES || join(HERE, "..", "maxScores.json"),
    trustProxy: parseTrustProxy(env.SCORES_TRUST_PROXY),
    corsOrigin: env.SCORES_CORS_ORIGIN || null,
  };
}

/**
 * SCORES_TRUST_PROXY: unset or "loopback" = trust X-Real-IP / X-Forwarded-For only from a loopback
 * peer (nginx on the same host); "none" = never; otherwise a comma-separated list of peer addresses.
 */
export function parseTrustProxy(value) {
  const v = (value ?? "").trim();
  if (v === "" || v === "loopback") return ["127.0.0.1", "::1", "::ffff:127.0.0.1"];
  if (v === "none") return [];
  return v.split(",").map((s) => s.trim()).filter(Boolean);
}
