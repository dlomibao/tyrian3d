import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { ENEMY_KEY_BASE, Pass, type Draw, type DrawList, type EnemyDeath, type SpriteDraw, type TileDraw } from "../../src/sim/draw";
import { DrawInterpolator } from "../../src/render/interpolation";
import { ScorchLayer, StructureMark } from "../../src/render/remaster/scorchLayer";

const sheet = { id: "test", data: new Uint8Array(0) };
const solid = new Uint8Array(24 * 28).fill(5);

function tile(key: number, x: number, y: number): TileDraw {
  return { kind: "tile", layer: 2, tile: solid, tileId: `t:${key}`, x, y, pass: Pass.Background3, key, effect: "none" };
}

function enemy(key: number, x: number, y: number): SpriteDraw {
  return {
    kind: "sprite2", sheet, index: 1, x, y, size: 1, pass: Pass.TopEnemies, key, effect: "none", filter: 0, value: 0,
    groupIndex: 1, groupSize: 2, groupDx: 6, groupDy: 7, groupFirst: true,
  };
}

function list(items: Draw[], deaths: EnemyDeath[] = []): DrawList {
  return { items, palette: 0, filter: -99, brightness: 0, screen: null, deaths };
}

describe("ScorchLayer (D96)", () => {
  const key = ENEMY_KEY_BASE + 4 * 7;
  function run(enemyStep: number, mark: StructureMark = StructureMark.Scorch) {
    const structure = () => mark;
    const layer = new ScorchLayer();
    const interp = new DrawInterpolator();
    const push = (l: DrawList) => {
      interp.push(l.items);
      layer.tick(l, interp.prevX, interp.prevY, structure);
    };
    push(list([tile(500, 100, 40), enemy(key, 106, 46)]));
    // The ground scrolls 1 px; the enemy moves with it (standing) or not (flying over), then dies.
    push(list([tile(500, 100, 41), enemy(key, 106, 47 + enemyStep)], [{ key, x: 112, y: 54 + enemyStep, layer: 2, size: 2 }]));
    return { layer, interp, push };
  }

  it("marks a structure where an enemy standing on it died, and keeps it while the tile shows", () => {
    const { layer, interp, push } = run(0);
    expect(layer.count).toBe(1);
    push(list([tile(500, 100, 42)]));
    expect(layer.count).toBe(1);
    layer.update(list([tile(500, 100, 42)]).items, interp.prevX, interp.prevY, 0.5, new THREE.Vector3(0, 30, 10));
    expect(layer.mesh.visible).toBe(true);
    push(list([tile(501, 100, 0)])); // its tile scrolled away
    expect(layer.count).toBe(0);
  });

  it("leaves no mark for an enemy that moved over the structure", () => {
    expect(run(3).layer.count).toBe(0);
  });

  it("marks a structure whose model shows the broken socket as a socket mark (D115)", () => {
    const { layer, interp } = run(0, StructureMark.Socket);
    expect(layer.count).toBe(1);
    layer.update(list([tile(500, 100, 41)]).items, interp.prevX, interp.prevY, 0.5, new THREE.Vector3(0, 30, 10));
    const params = layer.mesh.geometry.getAttribute("aParams");
    expect(params.itemSize).toBe(3);
    expect(params.getZ(0)).toBe(1);
  });

  it("leaves no mark off structures", () => {
    expect(run(0, StructureMark.None).layer.count).toBe(0);
  });
});
