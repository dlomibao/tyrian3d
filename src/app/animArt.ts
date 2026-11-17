// The remastered ending animation (DECISIONS.md D219): episode 3's `]A[`, tyrend.anm, re-created
// as a 3D scene in Blender (assets/blender/cutscenes/tyrend.py) and shipped as a video,
// public/art/cutscenes/tyrend.webm (VP9, 1600x1000). It runs at the original's timing: three video
// frames to each of the original's 111 frames, each of those 7 setFrameCount periods (~100.6 ms),
// so the video lasts as long as playAnim does (11.17 s).
//
// The look follows the flat art's switch (D42, as the shop icons, D210): `?sprites=`, else the
// effects look; the original look plays the original frames. So does a browser that can't play
// the video, or a video that doesn't load or start in time (anim playback falls back per call).

import { spriteArtModeFromSearch, type SpriteArtMode } from "../render/spriteArt";
import { vfxModeFromSearch } from "../render/vfx/vfxMode";

/** The video, relative to the site root. */
export const ANIM_VIDEO = "art/cutscenes/tyrend.webm";
export const ANIM_VIDEO_TYPE = 'video/webm; codecs="vp9"';

/** How long the video may take to be ready to play before the original frames play instead. */
const READY_TIMEOUT_MS = 8000;

/** The animation look the page asks for: `?sprites=`, else the effects look (D42's switch). */
export function animArtMode(search?: string): SpriteArtMode {
  return spriteArtModeFromSearch(search) ?? (vfxModeFromSearch(search) === "remastered" ? "remastered" : "original");
}

/** What the video playback did: played to the end, stopped by a key, or couldn't play at all. */
export type AnimVideoResult = "ended" | "skipped" | "failed";

export interface AnimVideoTarget {
  /** Draw the video's current frame (the stage's picture). */
  draw(video: HTMLVideoElement): void;
  /** A key, click, tap or pad button since the last call (the stage's getInput). */
  getInput(): boolean;
}

const nextFrame = () =>
  new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, 50); // rAF doesn't run in a hidden tab; the video does
    requestAnimationFrame(() => {
      clearTimeout(timer);
      resolve();
    });
  });

/** Resolve true once the video can play, false on an error or after `ms`. */
function whenReady(video: HTMLVideoElement, ms: number): Promise<boolean> {
  return new Promise((resolve) => {
    if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) return resolve(true);
    const done = (ok: boolean) => {
      clearTimeout(timer);
      video.removeEventListener("canplay", onReady);
      video.removeEventListener("error", onError);
      resolve(ok);
    };
    const onReady = () => done(true);
    const onError = () => done(false);
    const timer = setTimeout(() => done(false), ms);
    video.addEventListener("canplay", onReady);
    video.addEventListener("error", onError);
  });
}

/**
 * Play the remastered animation onto `target` until it ends or a key is pressed, as playAnim's
 * waitUntilGetInputOrElapsed loop does. "failed" (nothing was shown) means play the original.
 */
export async function playAnimVideo(target: AnimVideoTarget, url = `${import.meta.env.BASE_URL}${ANIM_VIDEO}`): Promise<AnimVideoResult> {
  const video = document.createElement("video");
  if (video.canPlayType(ANIM_VIDEO_TYPE) === "") return "failed";
  video.muted = true; // the animation has no sound of its own; the episode's music plays on
  video.playsInline = true;
  video.preload = "auto";
  video.src = url;
  if (import.meta.env.DEV) Object.assign(window, { tyrianAnimVideo: video }); // for scripted captures
  const release = () => {
    video.pause();
    video.removeAttribute("src");
    video.load();
  };
  try {
    if (!(await whenReady(video, READY_TIMEOUT_MS))) {
      console.warn(`ending animation: ${url} didn't load; playing the original frames`);
      return "failed";
    }
    try {
      await video.play();
    } catch (err) {
      console.warn("ending animation: the video didn't start; playing the original frames", err);
      return "failed";
    }
    for (;;) {
      target.draw(video);
      if (target.getInput()) return "skipped";
      if (video.ended || video.error) return "ended";
      await nextFrame();
    }
  } finally {
    release();
  }
}
