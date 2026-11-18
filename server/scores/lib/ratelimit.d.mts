export function utcMonth(now: number): string;
export function utcDay(now: number): string;
export function ipHash(salt: string, ip: string, now: number): string;
export class RateLimiter {
  constructor(windowMs?: number);
  hit(key: string, limit: number, now: number): number;
  sweep(now: number): void;
}
