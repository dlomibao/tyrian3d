// Whether the HUD's touch targets are on (D100), kept free of the DOM so it can be tested.

/** The URL's `?touchhud=1|0` forces them on (to try them with a mouse) or off. */
export function touchHudParam(search: string): boolean | null {
  const v = new URLSearchParams(search).get("touchhud");
  return v === "1" ? true : v === "0" ? false : null;
}

/** On a touch screen (a coarse pointer, or a finger was the last input), unless the URL says otherwise. */
export function touchHudWanted(param: boolean | null, coarse: boolean, device: string | undefined): boolean {
  return param ?? (coarse || device === "touch");
}
