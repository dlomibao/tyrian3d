// Cross-check driver for tests/destruct/trace.test.ts: runs OpenTyrian's real Destruct
// (src/destruct.c, included whole so its static functions are reachable) with both sides played by
// the computer, and prints a per-tick trace of the game state. Built and run by build.sh here.
//
// Usage: driver <datadir> <seed> <mode> <ticks> [full]
//   Without "full", prints a running FNV-1a digest of the trace every 10 ticks (the fixture);
//   with it, every line (to find where a difference starts).
#include "opentyr.h"
#include "file.h"
#include "mtrand.h"
#include "sprite.h"
#include "video.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Correctly rounded sinf and cosf, as glibc's are (and as the port's Math.fround(Math.sin(x)) is).
// macOS's libm sinf is sometimes an ulp off, which would make the trace depend on the platform.
#define sinf(x) ((float)sin((double)(float)(x)))
#define cosf(x) ((float)cos((double)(float)(x)))

void driver_play_song(unsigned int song_num);
#define play_song(n) driver_play_song(n)
#define JE_showVGA() ((void)0) /* no window: JE_generateTerrain shows the screen */
#include "destruct.c"
#undef play_song
#undef JE_showVGA

extern const char *customDataDirPath;

static int driverSong = -1;
void driver_play_song(unsigned int song_num) { driverSong = song_num; }

static int full = 0;
static Uint32 digest = 2166136261u;

static void emit(const char *fmt, ...)
{
	char line[512];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(line, sizeof line, fmt, ap);
	va_end(ap);
	for (const char *p = line; *p; ++p)
	{
		digest ^= (Uint8)*p;
		digest *= 16777619u;
	}
	digest ^= '\n';
	digest *= 16777619u;
	if (full)
		printf("%s\n", line);
}

static Uint32 F(float x)
{
	Uint32 u;
	memcpy(&u, &x, 4);
	return u;
}

static Uint32 hashBytes(const Uint8 *p, size_t n)
{
	Uint32 h = 2166136261u;
	for (size_t i = 0; i < n; ++i)
	{
		h ^= p[i];
		h *= 16777619u;
	}
	return h;
}

static Uint32 screenHash(void)
{
	return hashBytes(destructTempScreen->pixels, 320 * 200);
}

static void newRound(int round)
{
	destructFirstTime = true;
	JE_loadPic(VGAScreen, 11, false);
	DE_ResetUnits();
	DE_ResetLevel();
	Uint32 b[321];
	for (int i = 0; i < 320; ++i)
		b[i] = world.baseMap[i];
	emit("N %d %u %d %08x %08x", round, world.mapFlags, driverSong, hashBytes((Uint8 *)b, 320 * 4), screenHash());
	if (!full)
		printf("N %d %u %d\n", round, world.mapFlags, driverSong);
}

static void trace(int tick, unsigned int endDelay)
{
	emit("T %d %u %08x %d %d %d %d %d %d %d %d", tick, endDelay, screenHash(),
	     soundQueue[0], soundQueue[1], soundQueue[2], soundQueue[3], soundQueue[4], soundQueue[5], soundQueue[6], soundQueue[7]);
	for (int i = 0; i < MAX_PLAYERS; ++i)
	{
		struct destruct_player_s *p = &destruct_player[i];
		emit("P %d %d %u %u %u %u %d %d %d %u", i, p->is_cpu, p->unitsRemaining, p->unitSelected, p->shotDelay, p->score,
		     p->aiMemory.c_Angle, p->aiMemory.c_Power, p->aiMemory.c_Fire, p->aiMemory.c_noDown);
		for (unsigned int j = 0; j < config.max_installations; ++j)
		{
			struct destruct_unit_s *u = &p->unit[j];
			if (!DE_isValidUnit(u))
				continue;
			emit("U %d %u %u %08x %08x %d %d %d %08x %08x %d %u %d", i, j, u->unitX, F(u->unitY), F(u->unitYMov), u->isYInAir,
			     u->unitType, u->shotType, F(u->angle), F(u->power), u->lastMove, u->ani_frame, u->health);
		}
	}
	for (unsigned int i = 0; i < config.max_shots; ++i)
	{
		struct destruct_shot_s *s = &shotRec[i];
		if (s->isAvailable)
			continue;
		emit("S %u %08x %08x %08x %08x %u %u %u %u %u %u %u %u %u %u %u %u %u", i, F(s->x), F(s->y), F(s->xmov), F(s->ymov), s->shottype,
		     s->trailx[0], s->trailx[1], s->trailx[2], s->trailx[3], s->traily[0], s->traily[1], s->traily[2], s->traily[3],
		     s->trailc[0], s->trailc[1], s->trailc[2], s->trailc[3]);
	}
	for (unsigned int i = 0; i < config.max_explosions; ++i)
	{
		struct destruct_explo_s *e = &exploRec[i];
		if (e->isAvailable)
			continue;
		emit("E %u %u %u %u %u %u %d", i, e->x, e->y, e->explowidth, e->explomax, e->explofill, e->exploType);
	}
	for (unsigned int i = 0; i < config.max_walls; ++i)
		if (world.mapWalls[i].wallExist)
			emit("W %u %u %u", i, world.mapWalls[i].wallX, world.mapWalls[i].wallY);
}

int main(int argc, char **argv)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	customDataDirPath = argv[1];
	unsigned int seed = strtoul(argv[2], NULL, 10);
	int mode = atoi(argv[3]);
	int ticks = atoi(argv[4]);
	full = argc > 5;

	VGAScreen = VGAScreenSeg = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);
	game_screen = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);
	VGAScreen2 = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);

	// JE_destructGame, without load_destruct_config (the defaults) and with zeroed allocations.
	shotRec = calloc(config.max_shots, sizeof(struct destruct_shot_s));
	exploRec = calloc(config.max_explosions, sizeof(struct destruct_explo_s));
	world.mapWalls = calloc(config.max_walls, sizeof(struct destruct_wall_s));
	for (int i = 0; i < 10; i++)
		config.max_installations = MAX(config.max_installations, basetypes[i][0]);
	destruct_player[PLAYER_LEFT].unit = calloc(config.max_installations, sizeof(struct destruct_unit_s));
	destruct_player[PLAYER_RIGHT].unit = calloc(config.max_installations, sizeof(struct destruct_unit_s));
	destructTempScreen = game_screen;
	world.VGAScreen = VGAScreen;
	JE_loadCompShapes(&destructSpriteSheet, '~');

	mt_srand(seed);

	// JE_destructMain, with the computer playing both sides and the mode given.
	DE_ResetPlayers();
	destruct_player[PLAYER_LEFT].is_cpu = true;
	destruct_player[PLAYER_RIGHT].is_cpu = true;
	world.destructMode = mode;

	int round = 0;
	newRound(round);
	unsigned int endDelay = 0;
	for (int tick = 0; tick < ticks; ++tick)
	{
		// DE_RunTick without its drawing of the HUD, timing, keyboard and palette fades.
		memset(soundQueue, 0, sizeof(soundQueue));
		JE_tempScreenChecking();
		DE_ResetActions();
		DE_RunTickCycleDeadUnits();
		DE_RunTickGravity();
		DE_RunTickAnimate();
		DE_RunTickDrawWalls();
		DE_RunTickExplosions();
		DE_RunTickShots();
		DE_RunTickAI();
		if (destructFirstTime)
		{
			destructFirstTime = false;
			endDelay = 0;
		}
		DE_ProcessInput();

		bool reload = false;
		if (endDelay > 0)
		{
			if (--endDelay == 0)
				reload = true;
		}
		else if (DE_RunTickCheckEndgame() == true)
		{
			endDelay = 80;
		}

		trace(tick, endDelay);
		if (!full && tick % 10 == 9)
			printf("D %d %08x\n", tick, digest);

		if (reload)
			newRound(++round);
	}
	printf("R %lu\n", mt_rand());
	return 0;
}
