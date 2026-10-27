// Remastered artwork for the full-screen pictures between levels (DECISIONS.md, "Screens between
// levels").
//
// The story screens draw every picture through pictureSource() in storyScreens.ts, which looks
// here first. To replace a picture, put the image under public/art/ and map its number to the file
// name below; nothing else changes. Numbers are JE_loadPic's (1..13, tyrian.pic), and 0 is
// tshp2.pcx (the `]P 000[` picture). The image is stretched over the 320x200 screen (16:10), so
// it should have that aspect ratio; any size works, and larger looks sharper (the screen canvas is
// STORY_SCALE times 320x200). It's shown with the picture's own fades and the text drawn over it,
// in the same place, so keep the layout of the original picture.
//
// Pictures the scripts show: 5 (most text screens), 7 (episode 2's ending), 8 and 9 (episode 1's
// ending and the ALE bonus), 13 (episode 4's last world) and 0 (tshp2.pcx, before Time War).
// Picture 3 is the in-game HUD frame, which this port draws differently.

/** Picture number → file name under public/art/ (e.g. `5: "pic05.webp"`). Empty: the original pictures. */
const PICTURE_ART: Readonly<Record<number, string>> = {};

/** The override image's URL for a picture, or undefined to use the original from the game data. */
export function pictureArtUrl(pic: number): string | undefined {
  const file = PICTURE_ART[pic];
  return file === undefined ? undefined : `${import.meta.env.BASE_URL}art/${file}`;
}
