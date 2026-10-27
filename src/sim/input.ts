// The per-tick input the host hands the simulation, replacing OpenTyrian's SDL state
// (keysactive[], joystick[], mouse) as read by JE_playerMovement (mainint.c).
//
// How the host fills it, once per sim tick, before JE_main's tick runs:
// - up/down/left/right/fire/changeFire/leftSidekick/rightSidekick: whether the key bound to
//   KEY_SETTING_UP .. KEY_SETTING_RIGHT_SIDEKICK is held *now* (keysactive[keySettings[...]]).
//   OR a gamepad's d-pad and buttons into the same fields: OpenTyrian's digital joystick moves
//   the ship exactly like the keys (CURRENT_KEY_SPEED px), and its buttons OR into button[].
//   Default OpenTyrian keys: arrows, Space = fire, Enter = change fire (rear weapon mode),
//   Left Ctrl = left sidekick, Left Alt = right sidekick.
//   (In the C the joystick's mode-swap button is edge-triggered, action_pressed[1]; the keyboard's
//   is held. Holding is fine: the sim only swaps again after portConfigDone is set by a tick
//   where the button was up.)
// - analogX/analogY: an analog stick, already reduced with joystick_axis_reduce() below (the C
//   adds joystick_axis_reduce(j, axis) to mouseXC/mouseYC). Leave 0 without one.
// - mouseXR/mouseYR: relative mouse motion since the last tick, in game pixels (the C adds
//   mouseGetRelativePosition() to mouseXC/mouseYC). Optional; leave 0 to disable mouse steering.
// - mouseLeft/mouseRight/mouseMiddle: mouse buttons (left = fire, right = left sidekick,
//   middle = right sidekick; with a two-button mouse the C uses right for both sidekicks).
//
// [two-player] Each player has one: simInputs[0] (also exported as simInput) is player 1's and
// simInputs[1] player 2's (playerInput). In the C both players read the same SDL state and
// inputDevice[] picks a device for each (1 keyboard, 2 mouse, 3+ a joystick); here the host fills
// each player's SimInput from that player's own keys, pad and pointer (DECISIONS.md D28), and the
// C's device filter still applies to it.

export interface SimInput {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
  /** KEY_SETTING_FIRE -> button[0] */
  fire: boolean;
  /** KEY_SETTING_CHANGE_FIRE -> button[3] (cycle rear weapon mode) */
  changeFire: boolean;
  /** KEY_SETTING_LEFT_SIDEKICK -> button[1] */
  leftSidekick: boolean;
  /** KEY_SETTING_RIGHT_SIDEKICK -> button[2] */
  rightSidekick: boolean;
  /** Analog stick, already passed through joystick_axis_reduce (range about -13..13). */
  analogX: number;
  analogY: number;
  /** Relative mouse motion this tick, game pixels. */
  mouseXR: number;
  mouseYR: number;
  mouseLeft: boolean;
  mouseRight: boolean;
  mouseMiddle: boolean;
  /**
   * [two-player] joystick_analog_angle for the stick, or null when it's centred (or there is no
   * stick): the linked dragonwing's gun points this way while firing.
   */
  analogAngle: number | null;
}

export const newSimInput = (): SimInput => ({
  up: false, down: false, left: false, right: false,
  fire: false, changeFire: false, leftSidekick: false, rightSidekick: false,
  analogX: 0, analogY: 0, mouseXR: 0, mouseYR: 0,
  mouseLeft: false, mouseRight: false, mouseMiddle: false,
  analogAngle: null,
});

/** [two-player] Each player's input for the current tick. The host overwrites their fields before each tick. */
export const simInputs: readonly [SimInput, SimInput] = [newSimInput(), newSimInput()];

/** Player 1's input (the only one a one-player game reads). */
export const simInput: SimInput = simInputs[0];

/**
 * [two-player] The input JE_playerMovement reads for player `playerNum` (1 or 2): player 2's own in
 * a two-player game. In galaga mode the C moves both ships with every device (inputDevice 0), so
 * the spawned dragonwing follows player 1's input there.
 */
export function playerInput(playerNum: number, twoPlayerMode: boolean, galagaMode: boolean): SimInput {
  return playerNum === 2 && twoPlayerMode && !galagaMode ? simInputs[1] : simInputs[0];
}

/** Clear every field of both players' input (e.g. on focus loss or level start). */
export function clearSimInput(): void {
  for (const input of simInputs) Object.assign(input, newSimInput());
}

/** OpenTyrian's default joystick settings (joystick.c): threshold 5, sensitivity 5. */
const JOYSTICK_THRESHOLD = 5;
const JOYSTICK_SENSITIVITY = 5;

/** joystick_axis_threshold (joystick.c L50-63) for an axis given as -1..1, in SDL's units. */
function joystick_axis_threshold(axis: number): number {
  let value = Math.trunc(Math.max(-1, Math.min(1, axis)) * 32767);
  const negative = value < 0;
  if (negative) value = -value;
  if (value <= JOYSTICK_THRESHOLD * 1000) return 0;
  value -= JOYSTICK_THRESHOLD * 1000;
  return negative ? -value : value;
}

/**
 * [two-player] joystick_analog_angle (joystick.c L81-100) for one stick, axes -1..1: the angle the
 * linked gun turns to (0 = down the screen, as linkGunDirec), or null when the stick is centred.
 * The C adds to an angle starting at 0; with one stick that's the value itself. Float math as the C's.
 */
export function joystick_analog_angle(axisX: number, axisY: number): number | null {
  const f = Math.fround;
  const x = f(joystick_axis_threshold(axisX));
  const y = f(joystick_axis_threshold(axisY));
  if (x !== 0) {
    let angle = f(0 + f(Math.atan(f(-y / x))));
    angle = f(angle + (x < 0 ? -Math.PI / 2 : Math.PI / 2));
    return angle;
  }
  if (y !== 0) return y < 0 ? f(Math.PI) : 0;
  return null;
}

/**
 * joystick_axis_threshold + joystick_axis_reduce (joystick.c L50-77) for an axis given as -1..1
 * (the browser Gamepad API's range): scaled to SDL's -32767..32767, a dead zone of
 * threshold * 1000, then divided by (3000 - 200 * sensitivity), truncating like C.
 */
export function joystick_axis_reduce(axis: number): number {
  let value = Math.trunc(Math.max(-1, Math.min(1, axis)) * 32767);
  const negative = value < 0;
  if (negative) value = -value;
  if (value <= JOYSTICK_THRESHOLD * 1000) return 0;
  value -= JOYSTICK_THRESHOLD * 1000;
  value = negative ? -value : value;
  return Math.trunc(value / (3000 - 200 * JOYSTICK_SENSITIVITY));
}
