// The remastered shot and explosion effects (DECISIONS.md D35): presentation only, read from the
// draw list like everything else the renderer draws, so the simulation and its draws are untouched.
//
// - Shots (both passes) keep their extruded sprite, so their silhouette and palette colour are the
//   original's, but drawn fully emissive with no dark outline, over an additive halo of their own
//   colour that stretches back along their motion into a short trail. A new shot gets a muzzle flash.
//   The halo is drawn under the shot's flat art, so it rims the painting instead of bleaching it;
//   halos of touching shots (a beam's segments) are capped so they don't add up to white; missiles
//   and bombs (ORDNANCE_FRAMES) get no halo and no flash and keep their lit, outlined look (D169).
// - Explosions are told apart by their sprite index (explosionFrames.ts), which also says how far
//   through its life each one is. A fireball's sprite stays, glowing, under a light that fades with
//   it (with remastered sprite art it's the flat painting from public/art/sprites, D80: the router
//   draws it flat and this look is ignored); when one starts, it throws sparks, embers and tumbling debris, leaves smoke drifting with
//   the scroll, and lights its surroundings for a moment with one of a few pooled point lights.
//   A shot's hit puff becomes a spark burst and a flash; smoke sprites become soft smoke puffs.
//   Flashes, sparks, embers and lights take the explosion's own colour (the mean of its sprite's
//   colours), and flashes close together in place and time are thinned to one (D169).
// - The shield's hit arcs become one energy bubble round the ship (shieldLayer.ts, D77), in the
//   arcs' colour and for their three ticks, with a faint flash of light.
//   Coin values (flat art of their own in the remastered look, D76), shot trails and anything else
//   are drawn as before.
//
// Nothing here allocates per frame: particles live in GPU ring buffers (particles.ts), glows in
// reused instanced buffers (glowLayer.ts), and the lights are a fixed pool.

import * as THREE from "three";
import { VFX_LAYER } from "./vfxMode";
import { CLASSIC_TICK_HZ } from "../../core/timing";
import { PX_PER_UNIT, screenWorldX, screenWorldZ } from "../../game/playfield";
import { Pass, sparkColor, type Draw, type SparkPixel, type SpriteDraw, type TableSpriteDraw } from "../../sim/draw";
import type { PaletteTexture } from "../paletteTexture";
import { passHeight } from "../passHeights";
import type { SpriteMeshCache } from "../spriteMesh";
import { SPRITE_ART_ORDER } from "../spriteArtLayer";
import { EXPLOSION_SHEET_ID, ExplosionKind, explosionFrame, shieldArcCentre } from "./explosionFrames";
import { GlowLayer, GlowShape } from "./glowLayer";
import { ParticleShape, ParticleSystem } from "./particles";
import { ShieldLayer } from "./shieldLayer";

/** How the draw-list renderer should draw a sprite the effects have seen. */
export const enum SpriteLook {
  /** As always. */
  Default = 0,
  /** Fully emissive and without the dark outline. */
  Hot = 1,
  /** Not at all: the effects draw it. */
  Hidden = 2,
}

/** Shot trails reach back this many ticks of the shot's motion. */
const TRAIL_TICKS = 1.6;
/** Halo radius as a multiple of the sprite's own radius. */
const SHOT_HALO = 1.7;
/** D169: 0.8 and 0.9 (D35), drawn over the shot; now under it, in the shot's mean colour. */
const SHOT_HALO_INTENSITY = 0.6;
const ENEMY_SHOT_HALO_INTENSITY = 0.7;
/**
 * Shot halos whose centres are closer than this share of their radii's sum overlap heavily (a
 * beam's segments, a tight volley): each is dimmed by 1 / (1 + HALO_CROWD x its neighbours), so a
 * run of them reads about as bright as one instead of adding up to white (D169).
 */
const HALO_TOUCH = 0.8;
const HALO_CROWD = 0.75;
/** Shot halos one frame can hold (stress tests draw 800 shots; more are drawn uncapped). */
const MAX_HALOS = 2048;
const HALO_STRIDE = 12;
/**
 * The halos' place in the transparent order: under the player shots' flat art (spriteArtLayer.ts,
 * SPRITE_ART_ORDER + pass / 100), so the painting covers the halo's core and its colours stay.
 */
const SHOT_HALO_ORDER = SPRITE_ART_ORDER + Pass.PlayerShots / 100 - 0.002;
/**
 * Flashes closer than FLASH_REACH screen px to one started less than FLASH_GAP s before are not
 * drawn: a big explosion's four quarters, or hits stacking under sustained fire, flash once (D169).
 */
const FLASH_REACH = 14;
const FLASH_GAP = 0.12;
const FLASH_MEMORY = 64;
/** Lights for explosion flashes: a fixed pool, so the scene's light count (and shaders) never change. */
const LIGHTS = 4;
/** Lights sit this high, between the ground and the enemies, at the explosion's screen position. */
const LIGHT_HEIGHT = 2.2;
const LIGHT_RANGE = 9;
/** The shield bubble's radii in screen px: across, down the screen and (as px at its height) up. */
const SHIELD_RX = 20;
const SHIELD_RZ = 19;
const SHIELD_RY = 11;
/** Its intensity and size over the hit's three frames: it grows as the arcs do. */
const SHIELD_FADE = [1, 0.8, 0.5];
const SHIELD_GROW = [0.84, 0.94, 1.04];
/** A spark's glow radius (screen px, its plus is three across), streak (of its last tick's flight) and gain. */
const SPARK_RADIUS = 1.6;
const SPARK_STREAK = 0.6;
const SPARK_GAIN = 1.1;
/** Bubbles one frame can draw (a hit a tick for three ticks, for two players, with room to spare). */
const MAX_SHIELDS = 16;
/** Births queued between ticks and frames (a big boss death starts dozens at once). */
const MAX_BIRTHS = 256;

/**
 * Physical ordnance among the shot frames: the missiles and bombs, i.e. the frames on tyrian.shp#7
 * (spriteSheet8) of every weapon whose trail is smoke (trail 6 or 98, JE_setupExplosion's smoke;
 * tests/render/vfx.test.ts derives the set from the item data). They are steel, not energy: no
 * halo, no muzzle flash, and drawn lit with their outline (D169).
 */
export const ORDNANCE_SHEET_ID = "tyrian.shp#7";
export const ORDNANCE_FRAMES: ReadonlySet<number> = new Set([
  13, 14, 15, 19, 31, 32, 33, 34, 52, 53, 57, 68, 71, 72, 76, 90, 95, 96, 115, 142, 171,
]);

/** Whether a shot draw is a missile or bomb (ORDNANCE_FRAMES). */
export function isOrdnance(d: SpriteDraw | TableSpriteDraw): boolean {
  return d.kind === "sprite2" && d.sheet.id === ORDNANCE_SHEET_ID && ORDNANCE_FRAMES.has(d.index);
}

const enum Birth {
  Hit = 0,
  Fireball,
  Large,
  PlayerShot,
  EnemyShot,
  Shield,
}

/** What the effects need to know about a sprite: its middle, its size and its glow colour. */
interface SpriteInfo {
  /** Centre of its opaque pixels, from the sprite's top-left (px). */
  cx: number;
  cy: number;
  /** Radius of a disc of about its area (px). */
  radius: number;
  /** Palette indices of its top faces and how many vertices each has. */
  indices: Uint8Array;
  counts: Float32Array;
  /** Glow colour (linear RGB) and the palette version it was worked out for. */
  r: number;
  g: number;
  b: number;
  version: number;
}

interface FlashLight {
  light: THREE.PointLight;
  age: number;
  life: number;
  peak: number;
  /** Screen position and tick it started, to merge a big explosion's four quarters into one light. */
  sx: number;
  sy: number;
  tick: number;
}

export class RemasteredFx {
  readonly root = new THREE.Group();
  private readonly additive = new ParticleSystem(4096, THREE.AdditiveBlending);
  private readonly blended = new ParticleSystem(2048, THREE.NormalBlending);
  private readonly glows = new GlowLayer(THREE.AdditiveBlending, 512);
  /** Shot halos, under the shots' flat art (D169). */
  private readonly shotGlows = new GlowLayer(THREE.AdditiveBlending, 256, SHOT_HALO_ORDER);
  /** This frame's shot halos, held until end() to cap overlapping ones (screen px; see haloAt). */
  private readonly halos = new Float32Array(MAX_HALOS * HALO_STRIDE);
  private haloCount = 0;
  private readonly haloOrder = new Int32Array(MAX_HALOS);
  /** Recent flashes (screen x, y, start time), a ring, to thin flashes on one spot (D169). */
  private readonly flashes = new Float32Array(FLASH_MEMORY * 3).fill(-1e9);
  private flashHead = 0;
  /** Seconds of display time, for the flash memory. */
  private clock = 0;
  /**
   * Smoke puffs, under the shots' halos and flat art (D169): a missile's or bomb's trail puffs
   * start where it was a tick ago and grow over it, and in the C the shot is drawn clear of them.
   */
  private readonly puffs = new GlowLayer(THREE.NormalBlending, 128, SHOT_HALO_ORDER - 0.001);
  private readonly shields = new ShieldLayer();
  /** This frame's shield bubbles so far (screen x, y and the hit's frame), so a hit's nine arcs make one. */
  private readonly shieldSeen = new Float32Array(MAX_SHIELDS * 3);
  private shieldCount = 0;
  private readonly lights: FlashLight[] = [];
  private readonly info = new WeakMap<THREE.BufferGeometry, SpriteInfo | null>();
  private readonly colour = new THREE.Color();
  private readonly shieldPos = new THREE.Vector3();
  private cam = new THREE.Vector3(0, 30, 10);
  private tickCount = 0;
  /** Births seen in the last tick, spawned at the next frame (when the camera is known). */
  private readonly births = new Float32Array(MAX_BIRTHS * 6);
  private birthCount = 0;
  /** Shot keys drawn last tick and this tick, to spot new shots. */
  private shotKeys = new Set<number>();
  private nextShotKeys = new Set<number>();
  /** The scroll, as explosions move with it (px per tick, down the screen). */
  private scrollPx = 0;

  constructor(
    private readonly cache: SpriteMeshCache,
    private readonly palette: PaletteTexture,
  ) {
    this.root.name = "vfx";
    const meshes = [this.blended.mesh, this.puffs.mesh, this.shotGlows.mesh, this.glows.mesh, this.shields.mesh, this.additive.mesh];
    this.root.add(...meshes);
    // [filters] On their own layer, so the screen filters can draw them after the smoothies (D35).
    for (const mesh of meshes) mesh.layers.set(VFX_LAYER);
    for (let i = 0; i < LIGHTS; i++) {
      const light = new THREE.PointLight(0xffa040, 0, LIGHT_RANGE, 1.6);
      light.castShadow = false;
      this.root.add(light);
      this.lights.push({ light, age: 1, life: 1, peak: 0, sx: 0, sy: 0, tick: -1 });
    }
  }

  /** A new tick's draws (after interpolation matched them): note what started this tick. */
  tick(items: readonly Draw[], prevX: Float32Array, prevY: Float32Array): void {
    this.tickCount++;
    const next = this.nextShotKeys;
    next.clear();
    let scrollSeen = false;
    for (let i = 0; i < items.length; i++) {
      const d = items[i];
      if (d.kind !== "sprite2" && d.kind !== "sprite") continue;
      if (d.pass === Pass.PlayerShots || d.pass === Pass.EnemyShots) {
        if (d.key < 0 || d.effect === "darken") continue;
        next.add(d.key);
        if (!this.shotKeys.has(d.key) && !isOrdnance(d)) {
          const geometry = d.kind === "sprite2" ? this.cache.sprite2Geometry(d.sheet, d.index, d.size) : this.cache.tableGeometry(d.table, d.index);
          const info = geometry && this.spriteInfo(geometry);
          if (info) this.queueBirth(d.pass === Pass.PlayerShots ? Birth.PlayerShot : Birth.EnemyShot, d.x + info.cx, d.y + info.cy, info.radius, d.pass, geometry);
        }
      } else if (d.kind === "sprite2" && d.pass === Pass.Explosions && d.sheet.id === EXPLOSION_SHEET_ID) {
        const f = explosionFrame(d.index);
        if (!f) continue;
        if (f.frame > 0 && !scrollSeen && (f.kind === ExplosionKind.Fireball || f.kind === ExplosionKind.Large)) {
          const dy = d.y - prevY[i];
          if (d.x === prevX[i] && Math.abs(dy) <= 8) {
            this.scrollPx = dy;
            scrollSeen = true;
          }
        }
        if (f.frame !== 0) continue;
        let birth: Birth;
        if (f.kind === ExplosionKind.Hit) birth = Birth.Hit;
        else if (f.kind === ExplosionKind.Fireball) birth = Birth.Fireball;
        else if (f.kind === ExplosionKind.Large) birth = Birth.Large;
        else if (f.kind === ExplosionKind.Shield) {
          // One light for the hit's nine arcs (light() merges the rest into it).
          const at = shieldArcCentre(f.type)!;
          this.queueBirth(Birth.Shield, d.x + at[0], d.y + at[1], SHIELD_RX, d.pass, this.cache.sprite2Geometry(d.sheet, d.index, 1));
          continue;
        } else continue;
        const geometry = this.cache.sprite2Geometry(d.sheet, d.index, 1);
        const info = geometry && this.spriteInfo(geometry);
        // A large explosion's quarters are drawn toward its middle; its first frames are tiny, so
        // aim the burst at the tile corner they grow from.
        const cx = info ? info.cx : 6;
        const cy = info ? info.cy : 7;
        this.queueBirth(birth, d.x + cx, d.y + cy, info ? info.radius : 4, d.pass, geometry);
      }
    }
    this.nextShotKeys = this.shotKeys;
    this.shotKeys = next;
  }

  private queueBirth(kind: Birth, sx: number, sy: number, radius: number, pass: Pass, geometry: THREE.BufferGeometry | null): void {
    if (this.birthCount >= MAX_BIRTHS) return;
    const o = this.birthCount++ * 6;
    const info = geometry ? this.spriteInfo(geometry) : null;
    if (info) this.infoColour(info);
    this.births[o] = kind;
    this.births[o + 1] = sx;
    this.births[o + 2] = sy;
    this.births[o + 3] = radius;
    this.births[o + 4] = pass;
    // Pack the colour as 8-bit linear RGB.
    this.births[o + 5] = info ? (Math.min(255, info.r * 255) << 16) | (Math.min(255, info.g * 255) << 8) | Math.min(255, info.b * 255) : 0xffb060;
  }

  /** Start a display frame: age the particles and lights, and spawn what the last tick started. */
  begin(dt: number, camera: THREE.Camera): void {
    this.cam = camera.position;
    this.clock += dt;
    this.shieldCount = 0;
    this.haloCount = 0;
    this.additive.advance(dt);
    this.blended.advance(dt);
    for (let b = 0; b < this.birthCount; b++) {
      const o = b * 6;
      const rgb = this.births[o + 5];
      this.spawnBirth(this.births[o] as Birth, this.births[o + 1], this.births[o + 2], this.births[o + 3], this.births[o + 4] as Pass,
        ((rgb >> 16) & 255) / 255, ((rgb >> 8) & 255) / 255, (rgb & 255) / 255);
    }
    this.birthCount = 0;
    for (const f of this.lights) {
      if (f.age >= f.life) continue;
      f.age += dt;
      const t = Math.min(1, f.age / f.life);
      f.light.intensity = f.peak * (1 - t) * (1 - t);
    }
  }

  /**
   * A sprite in a shot or explosion pass, about to be drawn with its top-left at (x, y) (screen px,
   * interpolated), having moved (vx, vy) px since the last tick. Adds its glows; says how to draw it.
   */
  sprite(d: SpriteDraw | TableSpriteDraw, geometry: THREE.BufferGeometry, x: number, y: number, vx: number, vy: number): SpriteLook {
    const info = this.spriteInfo(geometry);
    if (!info) return SpriteLook.Default;
    this.infoColour(info);
    const cx = x + info.cx;
    const cy = y + info.cy;
    if (d.pass === Pass.PlayerShots || d.pass === Pass.EnemyShots) {
      // Missiles and bombs are steel: no halo, and lit with their outline (D169).
      if (isOrdnance(d)) return SpriteLook.Default;
      const intensity = d.pass === Pass.EnemyShots ? ENEMY_SHOT_HALO_INTENSITY : SHOT_HALO_INTENSITY;
      // Teleports and new shots have no motion to trail.
      const tx = Math.abs(vx) > 30 ? 0 : vx * TRAIL_TICKS;
      const ty = Math.abs(vy) > 30 ? 0 : vy * TRAIL_TICKS;
      this.halo(cx, cy, cx - tx, cy - ty, passHeight(d.pass), Math.max(2.5, info.radius * SHOT_HALO), info.r, info.g, info.b, intensity);
      return SpriteLook.Hot;
    }
    if (d.kind !== "sprite2" || d.pass !== Pass.Explosions || d.sheet.id !== EXPLOSION_SHEET_ID) return SpriteLook.Default;
    const f = explosionFrame(d.index);
    if (!f) return SpriteLook.Default;
    const h = passHeight(d.pass);
    const k = h / this.cam.y;
    const s = (1 - k) / PX_PER_UNIT;
    const t = (f.frame + 0.5) / f.ttl;
    switch (f.kind) {
      case ExplosionKind.Hit: {
        // D169: (1, 0.75 + 0.2g, 0.45) at 0.9, a near-white puff; now a warm orange one.
        const fade = (1 - t) * (1 - t);
        this.glow(this.glows, cx, cy, cx, cy, h, (3 + 4 * t) * s, 1, 0.5 + 0.2 * info.g, 0.18, 0.6 * fade, 0, GlowShape.Glow, 0);
        return SpriteLook.Hidden;
      }
      case ExplosionKind.Fireball:
      case ExplosionKind.Large: {
        const fade = 1 - t;
        this.glow(this.glows, cx, cy, cx, cy, h, Math.max(3, info.radius * 2) * s, info.r, info.g, info.b, 0.3 * fade, 0, GlowShape.Glow, 0);
        return SpriteLook.Hot;
      }
      case ExplosionKind.Smoke: {
        const grey = 0.35 + 0.3 * Math.max(info.r, info.g, info.b);
        this.glow(this.puffs, cx, cy, cx, cy, h, Math.max(2, info.radius * 1.35) * s,
          grey * 0.9, grey * 0.9, grey, 0.55 * (1 - t * t), 0, GlowShape.Puff, (d.key % 97) / 97);
        return SpriteLook.Hidden;
      }
      case ExplosionKind.Spark:
        return SpriteLook.Hot;
      case ExplosionKind.Shield:
        this.shield(x, y, f.type, f.frame, info);
        return SpriteLook.Hidden;
      default:
        return SpriteLook.Default;
    }
  }

  /**
   * A spark (JE_drawSP's superpixel, D147), its centre pixel at screen (x, y): a small additive
   * glow drawn out back along its flight into a short streak, in its hue at the brightness the C's
   * plus has over a bright screen, white-hot when new, fading with its life (z, 15 ticks). Stands
   * for the whole five-pixel plus.
   */
  spark(x: number, y: number, pass: Pass, sp: SparkPixel): void {
    const h = passHeight(pass);
    const s = (1 - h / this.cam.y) / PX_PER_UNIT;
    const life = sp.z / 15;
    const c = this.palette.color(sparkColor(sp, 0x0f), this.colour);
    const hot = 0.3 * life;
    const cx = x + 0.5, cy = y + 0.5;
    const tail = SPARK_STREAK * Math.min(1, 6 / Math.max(1, Math.hypot(sp.dx, sp.dy)));
    this.glow(this.glows, cx, cy, cx - sp.dx * tail, cy - sp.dy * tail, h, SPARK_RADIUS * (0.7 + 0.3 * life) * s,
      mix(c.r, 1, hot) * SPARK_GAIN, mix(c.g, 1, hot) * SPARK_GAIN, mix(c.b, 1, hot) * SPARK_GAIN,
      0.3 + 0.7 * life, 0, GlowShape.Glow, 0);
  }

  /**
   * The bubble for a shield arc's hit, drawn once for its nine arcs: centred where the arcs' ring
   * is (just below the ship's middle), at the ship's height, round the ship model.
   */
  private shield(x: number, y: number, type: number, frame: number, info: SpriteInfo): void {
    const at = shieldArcCentre(type)!;
    const sx = x + at[0];
    const sy = y + at[1];
    const seen = this.shieldSeen;
    for (let i = 0; i < this.shieldCount; i++) {
      const o = i * 3;
      if (seen[o + 2] === frame && Math.abs(seen[o] - sx) < 1 && Math.abs(seen[o + 1] - sy) < 1) return;
    }
    if (this.shieldCount >= MAX_SHIELDS) return;
    const o = this.shieldCount++ * 3;
    seen[o] = sx;
    seen[o + 1] = sy;
    seen[o + 2] = frame;
    const p = this.shieldPos;
    const s = this.place(p, sx, sy, passHeight(Pass.Player));
    // Two hits on one ship overlap: each keeps its own cell pattern, from the tick it started.
    const seed = ((this.tickCount - frame) % 7) * 0.37;
    const k = (SHIELD_GROW[frame] ?? 1) * s;
    this.shields.add(p.x, p.y, p.z, SHIELD_RX * k, SHIELD_RY * k, SHIELD_RZ * k, info.r, info.g, info.b,
      SHIELD_FADE[frame] ?? 0.3, (frame + 0.5) / 3, seed);
  }

  /** Upload this frame's glows and new particles. */
  end(): void {
    this.flushHalos();
    this.shields.commit();
    this.shotGlows.commit();
    this.glows.commit();
    this.puffs.commit();
    this.additive.flush();
    this.blended.flush();
  }

  /** Drop every particle, glow and flash (a new level). */
  reset(): void {
    this.additive.clear();
    this.blended.clear();
    this.birthCount = 0;
    this.haloCount = 0;
    this.flashes.fill(-1e9);
    this.shotKeys.clear();
    for (const f of this.lights) {
      f.age = f.life;
      f.light.intensity = 0;
    }
  }

  stats(): { particles: number; spawned: number } {
    return { particles: this.additive.alive() + this.blended.alive(), spawned: this.additive.spawned + this.blended.spawned };
  }

  dispose(): void {
    this.additive.dispose();
    this.blended.dispose();
    this.glows.dispose();
    this.shotGlows.dispose();
    this.puffs.dispose();
    this.shields.dispose();
    for (const f of this.lights) f.light.dispose();
    this.root.removeFromParent();
  }

  // --- spawning ---

  private spawnBirth(kind: Birth, sx: number, sy: number, radius: number, pass: Pass, r: number, g: number, b: number): void {
    const h = passHeight(pass);
    // D169: every flash and spark is the explosion's own colour (the mean of its sprite's colours,
    // infoColour), no longer mixed 40-50% toward white and boosted x1.3; flashes are smaller,
    // dimmer and thinned on one spot (flash()), so the fire reads red-orange, not white.
    switch (kind) {
      case Birth.PlayerShot:
      case Birth.EnemyShot:
        this.flash(sx, sy, h, Math.max(2, radius * 0.7), Math.max(4, radius * 1.5), 0.08, mix(r, 1, 0.15), mix(g, 1, 0.15), mix(b, 1, 0.15), kind === Birth.PlayerShot ? 0.45 : 0.35);
        break;
      case Birth.Hit:
        this.flash(sx, sy, h, 3, 7, 0.1, 1, 0.55, 0.22, 0.5);
        this.sparks(sx, sy, h, 5, 70, 150, 0.12, 0.24, 1, 0.55, 0.2);
        break;
      case Birth.Fireball:
        // Small fireballs also mark every hit on a big enemy, many a second under a laser, so
        // they're kept light: debris and smoke only now and then.
        this.flash(sx, sy, h, 5, 11, 0.14, r, g, b, 0.32);
        this.sparks(sx, sy, h, 3, 80, 170, 0.14, 0.28, r, g, b);
        this.embers(sx, sy, h, 1, r, g, b);
        if (Math.random() < 0.3) this.debris(sx, sy, h, 1, 1.0);
        if (Math.random() < 0.3) this.smoke(sx, sy, h, 1, 3, 8);
        this.light(sx, sy, 2, 0.2, r, g, b);
        break;
      case Birth.Large:
        // One of four quarters: each throws a share, and they share one light and one flash.
        this.flash(sx, sy, h, 7, 16, 0.22, r, g, b, 0.32);
        this.sparks(sx, sy, h, 4, 90, 190, 0.2, 0.42, r, g, b);
        this.embers(sx, sy, h, 2, r, g, b);
        this.debris(sx, sy, h, 2, 1.3);
        this.smoke(sx, sy, h, 1, 6, 14);
        this.light(sx, sy, 5, 0.32, r, g, b);
        break;
      case Birth.Shield:
        this.light(sx, sy, 1.2, 0.12, r, g, b);
        break;
    }
  }

  /** World position of screen point (sx, sy) on the ray to height h (DECISIONS.md D6). */
  private place(spec: { x: number; y: number; z: number }, sx: number, sy: number, h: number): number {
    const cam = this.cam;
    const k = h / cam.y;
    const gx = screenWorldX(sx);
    const gz = screenWorldZ(sy);
    spec.x = gx + (cam.x - gx) * k;
    spec.y = h;
    spec.z = gz + (cam.z - gz) * k;
    return (1 - k) / PX_PER_UNIT; // world units per screen px at that height
  }

  /** The scroll's velocity in world units/s along Z, at scale s. */
  private scrollVz(s: number): number {
    return this.scrollPx * CLASSIC_TICK_HZ * s;
  }

  /** A flash, unless one started close by a moment ago (FLASH_REACH, FLASH_GAP). */
  private flash(sx: number, sy: number, h: number, size0: number, size1: number, life: number, r: number, g: number, b: number, a: number): void {
    const f = this.flashes;
    for (let i = 0; i < FLASH_MEMORY * 3; i += 3) {
      if (this.clock - f[i + 2] < FLASH_GAP && Math.abs(f[i] - sx) < FLASH_REACH && Math.abs(f[i + 1] - sy) < FLASH_REACH) return;
    }
    const o = this.flashHead * 3;
    this.flashHead = (this.flashHead + 1) % FLASH_MEMORY;
    f[o] = sx;
    f[o + 1] = sy;
    f[o + 2] = this.clock;
    const p = this.additive.spec;
    const s = this.place(p, sx, sy, h);
    p.vx = 0;
    p.vy = 0;
    p.vz = this.scrollVz(s);
    p.gravity = 0;
    p.delay = 0;
    p.life = life;
    p.size0 = size0 * s;
    p.size1 = size1 * s;
    p.stretch = 0;
    p.shape = ParticleShape.Glow;
    p.r0 = r;
    p.g0 = g;
    p.b0 = b;
    p.a0 = a;
    p.r1 = r;
    p.g1 = g * 0.6;
    p.b1 = b * 0.4;
    p.a1 = 0;
    this.additive.spawn();
  }

  /** Spark streaks, hot in the explosion's colour (r, g, b, brightest channel 1) and cooling to red. */
  private sparks(sx: number, sy: number, h: number, n: number, speed0: number, speed1: number, life0: number, life1: number,
    r: number, g: number, b: number): void {
    const p = this.additive.spec;
    // D169: a fixed (2.2, 1.7, 0.9) before, white-yellow whatever burned.
    const r0 = 0.2 + 1.1 * r, g0 = 0.1 + 0.75 * g, b0 = 0.05 + 0.35 * b;
    for (let i = 0; i < n; i++) {
      const s = this.place(p, sx, sy, h);
      const a = Math.random() * Math.PI * 2;
      const v = (speed0 + Math.random() * (speed1 - speed0)) * s;
      p.vx = Math.cos(a) * v;
      p.vz = Math.sin(a) * v + this.scrollVz(s);
      p.vy = (Math.random() * 2 - 0.5) * v * 0.5;
      p.gravity = 0;
      p.delay = 0;
      p.life = life0 + Math.random() * (life1 - life0);
      p.size0 = 1.1 * s;
      p.size1 = 0.6 * s;
      p.stretch = 0.022;
      p.shape = ParticleShape.Spark;
      p.r0 = r0;
      p.g0 = g0;
      p.b0 = b0;
      p.a0 = 1;
      p.r1 = r;
      p.g1 = 0.25 * g;
      p.b1 = 0.04 * b;
      p.a1 = 0;
      this.additive.spawn();
    }
  }

  private embers(sx: number, sy: number, h: number, n: number, r: number, g: number, b: number): void {
    const p = this.additive.spec;
    for (let i = 0; i < n; i++) {
      const s = this.place(p, sx, sy, h);
      const a = Math.random() * Math.PI * 2;
      const v = (25 + Math.random() * 50) * s;
      p.vx = Math.cos(a) * v;
      p.vz = Math.sin(a) * v + this.scrollVz(s);
      p.vy = (0.5 + Math.random()) * 1.5;
      p.gravity = 2.5;
      p.delay = Math.random() * 0.05;
      p.life = 0.5 + Math.random() * 0.4;
      p.size0 = 1.6 * s;
      p.size1 = 0.6 * s;
      p.stretch = 0;
      p.shape = ParticleShape.Glow;
      p.r0 = mix(r, 1, 0.2) * 1.3;
      p.g0 = mix(g, 1, 0.1) * 1.1;
      p.b0 = b * 0.6;
      p.a0 = 1;
      p.r1 = r * 0.8;
      p.g1 = g * 0.3;
      p.b1 = 0;
      p.a1 = 0;
      this.additive.spawn();
    }
  }

  private debris(sx: number, sy: number, h: number, n: number, size: number): void {
    const p = this.blended.spec;
    for (let i = 0; i < n; i++) {
      const s = this.place(p, sx, sy, h);
      const a = Math.random() * Math.PI * 2;
      const v = (35 + Math.random() * 90) * s;
      p.vx = Math.cos(a) * v;
      p.vz = Math.sin(a) * v + this.scrollVz(s);
      p.vy = 2 + Math.random() * 4;
      p.gravity = 22;
      p.delay = 0;
      p.life = 0.7 + Math.random() * 0.4;
      p.size0 = size * (0.6 + Math.random() * 0.6) * s;
      p.size1 = p.size0 * 0.8;
      p.stretch = 0;
      p.shape = ParticleShape.Debris;
      // Charred chunks: a dull glow that's gone by the time they land.
      p.r0 = 0.45;
      p.g0 = 0.16;
      p.b0 = 0.05;
      p.a0 = 1;
      p.r1 = 0.012;
      p.g1 = 0.011;
      p.b1 = 0.01;
      p.a1 = 0;
      this.blended.spawn();
    }
  }

  private smoke(sx: number, sy: number, h: number, n: number, size0: number, size1: number): void {
    const p = this.blended.spec;
    for (let i = 0; i < n; i++) {
      const s = this.place(p, sx + (Math.random() - 0.5) * 6, sy + (Math.random() - 0.5) * 6, h - 0.15);
      const a = Math.random() * Math.PI * 2;
      const v = (4 + Math.random() * 10) * s;
      p.vx = Math.cos(a) * v;
      p.vz = Math.sin(a) * v + this.scrollVz(s);
      p.vy = 0.3;
      p.gravity = 0;
      p.delay = 0.06 + Math.random() * 0.12;
      p.life = 0.9 + Math.random() * 0.6;
      p.size0 = size0 * s;
      p.size1 = size1 * (0.8 + Math.random() * 0.4) * s;
      p.stretch = 0;
      p.shape = ParticleShape.Smoke;
      const grey = 0.018 + Math.random() * 0.025;
      p.r0 = grey * 2.5;
      p.g0 = grey * 1.7;
      p.b0 = grey * 1.2;
      p.a0 = 0.42;
      p.r1 = grey;
      p.g1 = grey;
      p.b1 = grey * 1.1;
      p.a1 = 0;
      this.blended.spawn();
    }
  }

  /** Light the explosion's surroundings: merged with a light started this tick close by, else a free one. */
  private light(sx: number, sy: number, peak: number, life: number, r: number, g: number, b: number): void {
    let best: FlashLight | null = null;
    for (const f of this.lights) {
      if (f.tick === this.tickCount && Math.abs(f.sx - sx) < 30 && Math.abs(f.sy - sy) < 30) {
        f.peak = Math.max(f.peak, peak);
        return;
      }
      if (!best || f.light.intensity < best.light.intensity) best = f;
    }
    if (!best || best.light.intensity > peak) return;
    const pos = best.light.position;
    this.place(pos, sx, sy, LIGHT_HEIGHT);
    // D169: its own colour, a touch warmed (was mixed 35% toward a fixed warm white).
    best.light.color.setRGB(mix(r, 1, 0.15), mix(g, 0.5, 0.15), mix(b, 0.2, 0.15));
    best.age = 0;
    best.life = life;
    best.peak = peak;
    best.light.intensity = peak;
    best.sx = sx;
    best.sy = sy;
    best.tick = this.tickCount;
  }

  /** Hold a shot halo (screen px, radius in screen px) for flushHalos. */
  private halo(hx: number, hy: number, tx: number, ty: number, h: number, radius: number, r: number, g: number, b: number, a: number): void {
    if (this.haloCount >= MAX_HALOS) {
      this.glow(this.shotGlows, hx, hy, tx, ty, h, radius * (1 - h / this.cam.y) / PX_PER_UNIT, r, g, b, a, 0, GlowShape.Glow, 0);
      return;
    }
    const o = this.haloCount++ * HALO_STRIDE;
    const v = this.halos;
    v[o] = hx;
    v[o + 1] = hy;
    v[o + 2] = tx;
    v[o + 3] = ty;
    v[o + 4] = h;
    v[o + 5] = radius;
    v[o + 6] = r;
    v[o + 7] = g;
    v[o + 8] = b;
    v[o + 9] = a;
    v[o + 10] = 0; // neighbours
  }

  /**
   * Draw this frame's shot halos, each dimmed by how many others it overlaps heavily at its own
   * height (centres closer than HALO_TOUCH of their radii's sum): a beam's stacked segments or a
   * tight volley then read about as bright as one halo, not white (D169). Sorted along x, so the
   * search only looks at halos within reach.
   */
  private flushHalos(): void {
    const n = this.haloCount;
    if (n === 0) return;
    const v = this.halos;
    const order = this.haloOrder;
    let maxR = 0;
    for (let i = 0; i < n; i++) {
      order[i] = i;
      maxR = Math.max(maxR, v[i * HALO_STRIDE + 5]);
    }
    const sorted = order.subarray(0, n).sort((a, b) => v[a * HALO_STRIDE] - v[b * HALO_STRIDE]);
    const reach = 2 * maxR * HALO_TOUCH;
    for (let i = 0; i < n; i++) {
      const a = sorted[i] * HALO_STRIDE;
      for (let j = i + 1; j < n; j++) {
        const c = sorted[j] * HALO_STRIDE;
        const dx = v[c] - v[a];
        if (dx > reach) break;
        if (v[c + 4] !== v[a + 4]) continue;
        const touch = (v[a + 5] + v[c + 5]) * HALO_TOUCH;
        const dy = v[c + 1] - v[a + 1];
        if (dx * dx + dy * dy < touch * touch) {
          v[a + 10]++;
          v[c + 10]++;
        }
      }
    }
    for (let i = 0; i < n; i++) {
      const o = i * HALO_STRIDE;
      const h = v[o + 4];
      const s = (1 - h / this.cam.y) / PX_PER_UNIT;
      this.glow(this.shotGlows, v[o], v[o + 1], v[o + 2], v[o + 3], h, v[o + 5] * s, v[o + 6], v[o + 7], v[o + 8],
        v[o + 9] / (1 + HALO_CROWD * v[o + 10]), 0, GlowShape.Glow, 0);
    }
    this.haloCount = 0;
  }

  private glow(layer: GlowLayer, hx: number, hy: number, tx: number, ty: number, h: number, radius: number,
    r: number, g: number, b: number, a: number, tailFade: number, shape: GlowShape, seed: number): void {
    const cam = this.cam;
    const k = h / cam.y;
    const ghx = screenWorldX(hx);
    const ghz = screenWorldZ(hy);
    const gtx = screenWorldX(tx);
    const gtz = screenWorldZ(ty);
    layer.add(ghx + (cam.x - ghx) * k, h, ghz + (cam.z - ghz) * k, gtx + (cam.x - gtx) * k, h, gtz + (cam.z - gtz) * k,
      radius, r, g, b, a, tailFade, shape, seed);
  }

  // --- sprite facts ---

  private spriteInfo(geometry: THREE.BufferGeometry): SpriteInfo | null {
    let info = this.info.get(geometry);
    if (info === undefined) {
      info = measureSprite(geometry);
      this.info.set(geometry, info);
    }
    return info;
  }

  /** Bring a sprite's glow colour up to date with the palette. */
  private infoColour(info: SpriteInfo): void {
    if (info.version === this.palette.version) return;
    info.version = this.palette.version;
    const c = spriteGlowColour(info.indices, info.counts, (i) => this.palette.color(i, this.colour));
    info.r = c[0];
    info.g = c[1];
    info.b = c[2];
  }
}

/** Centre, size and colours of a sprite mesh's top faces (spriteMesh.ts: px, top-left at the origin). */
export function measureSprite(geometry: THREE.BufferGeometry): SpriteInfo | null {
  const pos = geometry.getAttribute("position");
  const nrm = geometry.getAttribute("normal");
  const pal = geometry.getAttribute("palIndex");
  if (!pos || !nrm || !pal) return null;
  let n = 0, sx = 0, sz = 0;
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  const counts = new Float32Array(256);
  for (let i = 0; i < pos.count; i++) {
    if (nrm.getY(i) < 0.3) continue;
    const x = pos.getX(i);
    const z = pos.getZ(i);
    n++;
    sx += x;
    sz += z;
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    z0 = Math.min(z0, z);
    z1 = Math.max(z1, z);
    counts[pal.getX(i) & 255]++;
  }
  if (n === 0) return null;
  const used: number[] = [];
  for (let i = 0; i < 256; i++) if (counts[i] > 0) used.push(i);
  return {
    cx: sx / n,
    cy: sz / n,
    radius: Math.max(1, Math.sqrt((x1 - x0) * (z1 - z0)) / 2),
    indices: Uint8Array.from(used),
    counts: Float32Array.from(used.map((i) => counts[i])),
    r: 1,
    g: 1,
    b: 1,
    version: -1,
  };
}

/**
 * A sprite's glow colour (linear RGB, brightest channel 1): the mean of its pixels' colours, each
 * pixel counted once, so the glow is the colour the sprite mostly is (a fire's red-orange, a laser's
 * blue). D35 weighted by luminance squared, the colour of its brightest pixels, which for most
 * shots and fires is a near-white core (D169). The glow carries the hue, the shader the intensity.
 */
export function spriteGlowColour(indices: ArrayLike<number>, counts: ArrayLike<number>,
  color: (index: number) => { r: number; g: number; b: number }): [number, number, number] {
  let r = 0, g = 0, b = 0;
  for (let i = 0; i < indices.length; i++) {
    const c = color(indices[i]);
    r += c.r * counts[i];
    g += c.g * counts[i];
    b += c.b * counts[i];
  }
  const m = Math.max(r, g, b);
  return m > 0 ? [r / m, g / m, b / m] : [1, 1, 1];
}

const mix = (a: number, b: number, t: number) => a + (b - a) * t;
