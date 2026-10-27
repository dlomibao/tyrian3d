# The interface framework (`src/ui/`)

Every screen outside the action itself (the data picker, title, item screen, messages, pause, and
the Data Cubes, Options, high scores, endings and story screens still to come) is an HTML screen
built from this folder, over a 3D backdrop. That gives them one look (a remastered Tyrian: dark
panels, gold and cyan accents, crisp vector text at any size) and one way to drive them (keyboard,
gamepad, mouse and touch). The game rules behind a screen stay in `src/sim/` and don't change;
a screen only draws the state and turns input into the rules' inputs.

| File | What it holds |
|---|---|
| `tokens.css` | Design tokens: colours, type scale, spacing, motion. Change the look here. |
| `components.css`, `components.ts` | Base components: panel, logo, title, menu list, buttons, key hints, stat bars, scroll box. |
| `screen.ts` | The screen manager (`showScreen`, `ui`), screens, modals (`screen.modal`, `screen.confirm`). |
| `nav.ts`, `focus.ts` | The navigation model: keys and pad buttons become intents; focus movement. |
| `backdrop.ts` | The 3D scene behind the menus (attached by `main.ts`). |
| `index.ts` | Everything but the backdrop, for screens to import from `../ui`. |

## Building a screen

```ts
import { button, h, keyHints, MenuList, showScreen, title } from "../ui";

/** Options: pick one, or back out. Resolves with the choice, or null. */
export function showOptions(): Promise<string | null> {
  return new Promise((resolve) => {
    const done = (v: string | null) => {
      screen.close();
      resolve(v);
    };
    const screen = showScreen({
      id: "options",          // root gets .ui-screen--options for screen-specific CSS
      backdrop: "space",      // "title" | "hangar" | "space" | "none" (the game stays visible)
      layout: "center",       // panel width: "narrow" | "center" | "wide"
      onBack: () => done(null), // Escape, Backspace, pad B
    });
    const list = new MenuList({
      items: [{ label: "Music volume", detail: "80%" }, { label: "Sound effects" }, { label: "Detail", disabled: true }],
      onSelect: (i) => done(["music", "sfx", "detail"][i]),
    });
    screen.add(
      title("Options", "Item screen"),
      list, // a Navigable: added to the panel *and* to screen.controls
      keyHints([
        { key: "↑↓", pad: "✛", label: "Move" },
        { key: "Enter", pad: "A", touch: "Tap", label: "Select" },
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    );
  });
}
```

- **One screen at a time.** `showScreen` closes whatever screen is up (they cross-fade) and routes
  all input to the new one. `screen.close()` fades it out; `screen.closed` resolves then. With no
  screen up (a level is running) nothing is routed and the backdrop sleeps.
- **Screens over screens.** A screen opened from another (Options, Load Game or High Scores from the title,
  the settings or save prompt from the item screen) passes `over: true`: the one beneath stays
  open, hidden and without input, and gets the input back when this one closes, so its caller just
  awaits it. `over: "show"` leaves the one beneath in view (a dialog over the item screen). Without
  a `backdrop` of its own, the mood stays the one beneath. A screen shown without `over` closes
  them all.
- **Content** goes in `screen.panel` (`screen.add(...)` appends nodes and Navigables). Anything
  outside the panel, such as the title's logo, goes in `screen.root`.
- **Text from the game data** goes in with `h(tag, { text })` or `textContent`, never as markup.
  Tyrian's `~highlight~` text needs escaping first (see `highlight` in `src/app/shop.ts`).

## Input: intents

Keys, pad buttons and stick become eight intents (`nav.ts`):

| Intent | Keyboard | Gamepad |
|---|---|---|
| `up` `down` `left` `right` | arrows, WASD | d-pad, left stick (repeat while held) |
| `accept` | Enter, Space | A |
| `back` | Escape, Backspace | B |
| `alt` | `/` | X |
| `start` | | Start |

An intent goes, in order, to: an open modal; the screen's `onIntent` (return true to keep it);
each of `screen.controls` in order (the first `Navigable.handle` that returns true wins); and
finally `back` calls `onBack`. A vertical `MenuList` takes up/down/accept, a horizontal one
(a row of choices) left/right, so a list and a row of choices on one screen share the arrows the
way the title's episodes and difficulty do. For a screen-specific key (the title's `M`), use
`onKey(e)`. Keys typed into a text field (a high-score name) are left alone, except Enter and
Escape.

Pad buttons held when a screen appears are ignored until released, so the fire button held
through a death or the press that opened the screen don't act on it. The other pad buttons (Y,
Back, the shoulders) aren't intents; a screen gets their presses in `onPadButton(index)` (the
title's Y opens High Scores, Back opens Options).

A screen that reads the keys and pads itself (none of the game's menus do any more) is opened with `screen.aside`. A framework screen opening one does it
inside `screen.aside(() => showOptions(...), { hide })`: the navigation stops sending it input
until the promise settles (pad buttons still held then are ignored), and `hide` (default true)
hides the screen meanwhile, leaving the backdrop.

Pointer and touch: components handle taps themselves (a `MenuList` tap focuses and selects the
item). Nothing needs a swipe or a drag. Make every target at least `--ui-hit` tall.

## Components

- `panel(...)`, `logo()`, `title(text, kicker?)`, `h("span", { class: "ui-label", text })` for
  a small section label.
- `new MenuList({ items, focused, orientation, wrap, onSelect, onFocus })`: items have `label`,
  `detail`, `icon` (URL or element), `badge`, `disabled`. `setItems` replaces them; `focus(i)`.
  The focused item is always scrolled into view (`reveal`).
- `button({ label, variant: "primary" | "default" | "ghost", hint, onPress })` and
  `backButton(onPress)` for a touch-friendly back in the panel's corner.
- `keyHints([{ key, pad, touch, label }])`: shows the glyph for the device used last
  (`<html data-input="keys|pad|mouse|touch">`). A hint without `touch` hides on touch screens.
- `statBar(label, "armor" | "shield" | "power" | "gold" | "cyan", fraction)` returns `{ el, set }`.
- `new ScrollBox(...content)`: long text that up/down scroll; add it as a control.
- `screen.modal({ title, body, actions, focused, cancel })` and `screen.confirm(text, opts)`:
  a box over the screen that takes all input until answered.

Screens that redraw from state (like the item screen) can also write the markup directly with the
same classes: `ui-menu`, `ui-menu__item is-focused`, `ui-menu__icon`, `ui-menu__text`,
`ui-menu__label`, `ui-menu__detail`, `ui-badge`, `ui-stat`, `ui-button`, `ui-modal`.

## Look

Use the tokens (`var(--ui-gold)`, `var(--ui-space-3)`, `var(--ui-text-lg)`,
`var(--ui-med)`...) rather than raw values, the display face (`--ui-font-display`, Orbitron) for
titles and labels and the text face (`--ui-font-text`, Exo 2) for reading. Motion stays subtle and
honours `prefers-reduced-motion` through the tokens. Check a new screen at phone size (a 390 px
wide portrait screen and a landscape one) as well as on a desktop.

The older classes in `src/app/overlay.css` (`.overlay`, `.panel`, `.choices`, `.key`) still
work and take the tokens' colours and font, so a screen written with them looks close already;
moving it onto `showScreen` gives it the navigation, transitions and backdrop.

## Backdrop

`main.ts` attaches a `Backdrop` that draws with the game View's renderer while a screen with a
backdrop mood is up, and stops when none is (it costs nothing during levels). Without WebGL a CSS
starfield stands in. `ui.backdrop?.setShipGraphic?.(shipGraphic)` shows a player ship (the item
screen does this as ships are browsed).
