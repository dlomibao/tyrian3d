// [two-player] The item screen's two-player parts (shop.ts draws the screen). In a two-player game
// the C's item screen is the 2 Player Arcade menu (Play Next Level, Player 1 Input, Player 2
// Input, Options, Quit Game) and, where a one-player game shows the ship, both players' scores
// ("Player 1 Score: ...", game_menu.c L630-644). It hides the cash and the armor and shield bars.
// Here the left column shows each player's score, ship, weapon and devices, and the input rows
// show and cycle each player's gamepad (cyclePad, DECISIONS.md D28).

import "./twoPlayer.css";
import { cyclePad, keyName, keys, keys2, pads } from "./bindings";
import { savePrefs } from "./prefs";
import { menu } from "../sim/game_menu";
import { FRONT_WEAPON, g, REAR_WEAPON } from "../sim/state";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/** The n-th connected gamepad (pads[] counts connected ones), if there is one. */
function connectedPad(n: number): Gamepad | null {
  if (n < 0) return null;
  return (navigator.getGamepads?.() ?? []).filter((p): p is Gamepad => !!p)[n] ?? null;
}

/** A player's devices, for the input rows and the side panel: their keys, the mouse (player 1) and their pad. */
export function inputDevicesText(player: 0 | 1): string {
  const table = player === 0 ? keys : keys2;
  const moveKeys = [table.up[0], table.left[0], table.down[0], table.right[0]].filter((c) => c);
  const parts = [`Keyboard (${moveKeys.map(keyName).join(" ")})`];
  if (player === 0) parts.push("Mouse");
  const n = pads[player];
  if (n >= 0) parts.push(`Gamepad ${n + 1}${connectedPad(n) ? "" : " (not connected)"}`);
  return parts.join(" · ");
}

/**
 * The host's answer to the input rows (menu.inputRequest): the next gamepad for that player.
 * True if there was one to answer.
 */
export function twoPlayerInputRequest(): boolean {
  if (menu.inputRequest === null) return false;
  cyclePad(menu.inputRequest);
  menu.inputRequest = null;
  savePrefs();
  return true;
}

/** The left column in a two-player game: each player's score, ship, weapon and devices. */
export function twoPlayerSideHtml(): string {
  const { items } = g.res;
  return `<div class="shop-two">${[0, 1]
    .map((i) => {
      const p = g.player[i];
      const port = i === 0 ? FRONT_WEAPON : REAR_WEAPON;
      const weapon = p.items.weapon[port];
      const ship = p.items.ship > 90 ? `Custom Ship ${p.items.ship - 90}` : i === 1 && g.shipGr2 === 0 ? "Dragonwing" : (items.ships[p.items.ship]?.name ?? "");
      const label = g.miscText[40 + i]?.trim() || `Player ${i + 1} Score:`; // "Player 1 Score:"
      return `<section class="shop-two__player shop-two__player--${i + 1}">
        <div class="shop-two__head"><b>${esc(g.miscText[48 + i]?.trim() || `Player ${i + 1}`)}</b><span class="shop-two__score" title="${esc(label)}">${p.cash}</span></div>
        <div class="shop-two__line">${esc(ship.trim())}</div>
        <div class="shop-two__line">${esc(items.weaponPorts[weapon.id]?.name?.trim() ?? "")} · ${weapon.power}</div>
        <div class="shop-two__line">${esc(inputDevicesText(i as 0 | 1))}</div>
      </section>`;
    })
    .join("")}</div>`;
}
