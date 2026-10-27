// The TypeScript twin of tools/destruct-trace/driver.c: plays Destruct with the computer on both
// sides from a seed and produces the same trace (or its running digest) line for line.
import { decodePicture } from "../../src/data";
import { DestructGame, PLAYER_LEFT, PLAYER_RIGHT, type KeysActive } from "../../src/destruct/sim";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";

const NO_KEYS: KeysActive = { isDown: () => false, release: () => {} };

const hex = (n: number): string => (n >>> 0).toString(16).padStart(8, "0");
const fbits = new Float32Array(1);
const ubits = new Uint32Array(fbits.buffer);
const F = (x: number): string => {
  fbits[0] = x;
  return hex(ubits[0]);
};
const b = (x: boolean): number => (x ? 1 : 0);

function fnv(bytes: Uint8Array): number {
  let h = 2166136261;
  for (let i = 0; i < bytes.length; i++) h = Math.imul(h ^ bytes[i], 16777619);
  return h >>> 0;
}

/** driver.c's output for one case: "N"/"D"/"R" lines, or every line when `full`. */
export function destructTrace(tyrianPic: Uint8Array, seed: number, mode: number, ticks: number, full = false): string[] {
  const out: string[] = [];
  let digest = 2166136261;
  const emit = (line: string) => {
    for (let i = 0; i < line.length; i++) digest = Math.imul(digest ^ line.charCodeAt(i), 16777619);
    digest = Math.imul(digest ^ 10, 16777619);
    if (full) out.push(line);
  };
  const picture = decodePicture(tyrianPic, 11)!;
  const game = new DestructGame();
  const screenHash = () => hex(fnv(game.tempScreen));

  mt_srand(seed);
  game.DE_ResetPlayers();
  game.destruct_player[PLAYER_LEFT].is_cpu = true;
  game.destruct_player[PLAYER_RIGHT].is_cpu = true;

  const newRound = (round: number) => {
    game.startRound(mode, picture);
    const base = new Uint8Array(new Uint32Array(game.world.baseMap.slice(0, 320)).buffer);
    emit(`N ${round} ${game.world.mapFlags} ${game.song} ${hex(fnv(base))} ${screenHash()}`);
    if (!full) out.push(`N ${round} ${game.world.mapFlags} ${game.song}`);
  };

  let round = 0;
  newRound(round);
  for (let tick = 0; tick < ticks; tick++) {
    const state = game.DE_RunTick(NO_KEYS);
    const sq = game.soundQueue;
    emit(`T ${tick} ${game.endDelay} ${screenHash()} ${sq.join(" ")}`);
    game.destruct_player.forEach((p, i) => {
      const ai = p.aiMemory;
      emit(`P ${i} ${b(p.is_cpu)} ${p.unitsRemaining} ${p.unitSelected} ${p.shotDelay} ${p.score} ${ai.c_Angle} ${ai.c_Power} ${ai.c_Fire} ${ai.c_noDown}`);
      p.unit.forEach((u, j) => {
        if (u.health <= 0) return;
        emit(`U ${i} ${j} ${u.unitX} ${F(u.unitY)} ${F(u.unitYMov)} ${b(u.isYInAir)} ${u.unitType} ${u.shotType} ${F(u.angle)} ${F(u.power)} ${u.lastMove} ${u.ani_frame} ${u.health}`);
      });
    });
    game.shotRec.forEach((s, i) => {
      if (s.isAvailable) return;
      emit(`S ${i} ${F(s.x)} ${F(s.y)} ${F(s.xmov)} ${F(s.ymov)} ${s.shottype} ${s.trailx.join(" ")} ${s.traily.join(" ")} ${s.trailc.join(" ")}`);
    });
    game.exploRec.forEach((e, i) => {
      if (e.isAvailable) return;
      emit(`E ${i} ${e.x} ${e.y} ${e.explowidth} ${e.explomax} ${e.explofill} ${e.exploType}`);
    });
    game.world.mapWalls.forEach((w, i) => {
      if (w.wallExist) emit(`W ${i} ${w.wallX} ${w.wallY}`);
    });
    if (!full && tick % 10 === 9) out.push(`D ${tick} ${hex(digest)}`);
    if (state === 1 /* STATE_RELOAD */) newRound(++round);
  }
  out.push(`R ${mt_rand()}`);
  return out;
}
