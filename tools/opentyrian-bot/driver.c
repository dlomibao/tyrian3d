// Cross-check driver for tests/sim/botTrace.test.ts: runs OpenTyrian's real JE_loadMap and JE_main
// (the whole level loop, not a re-creation of it) with the bot of tests/sim/episode.test.ts, and
// prints what the TypeScript port must reproduce. Built and run by run.sh in this directory, which
// first patches a copy of OpenTyrian's sources with the hooks called here (bot_level_loaded,
// bot_level_tick, bot_level_end, bot_episode_end), turns off the frame delay and save-game writes.
// Links against all of OpenTyrian's src/*.c (GPL-2.0-or-later, like this repo).
//
//   driver route <data> <episode> <section>
//       JE_loadMap from episode-script `section` with constantPlay set (so the item screen picks the
//       next level by itself, game_menu.c L786-791), then prints the level it lands on, or the
//       section whose ]Q[ ends the episode.
//   driver play <data> <episode> <section> <ticks> [every]
//       A new one-player game (normal difficulty) starting at `section`, then JE_main. The front
//       weapon gets power 11 once the level is loaded; from the second tick on the ship is kept
//       invulnerable with armor >= 10, fires, and sweeps left/right every 50 ticks. Prints the
//       level, then one line every `every` ticks (default 1) and the last tick, and stops at
//       `ticks` or when the level ends.
#include "backgrnd.h"
#include "config.h"
#include "demo.h"
#include "editship.h"
#include "episodes.h"
#include "file.h"
#include "helptext.h"
#include "keyboard.h"
#include "loudness.h"
#include "mainint.h"
#include "mtrand.h"
#include "opentyr.h"
#include "palette.h"
#include "params.h"
#include "player.h"
#include "sprite.h"
#include "tyrian2.h"
#include "varz.h"
#include "video.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern const char *customDataDirPath;

static long botTick = -1;  // index of the level_loop pass in progress
static long maxTicks = 0;
static long every = 1;
static int routeEpisode, routeSection;

static void printTick(long k)
{
	int enemies = 0;
	for (int i = 0; i < 100; i++)
		if (enemyAvail[i] != 1)
			enemies++;
	printf("T %ld %u %u %u %u %u %d %d %lu %u %d %u %u\n", k, curLoc, eventLoc, backMove, backMove2, enemyOnScreen,
	       player[0].x, player[0].y, player[0].cash, enemyKilled, enemies, endLevel, levelEnd);
}

void bot_level_loaded(void)
{
	if (botTick >= 0)
		return;
	printf("LEVEL '%s' main %u next %u file %u galaga %d onePlayerAction %d superTyrian %d ship %u weapon %u\n", levelName,
	       mainLevel, nextLevel, lvlFileNum, galagaMode, onePlayerAction, superTyrian, player[0].items.ship,
	       player[0].items.weapon[FRONT_WEAPON].id);
	player[0].items.weapon[FRONT_WEAPON].power = 11;
}

// Top of level_loop: report the pass that just finished, then set this pass's input.
void bot_level_tick(void)
{
	botTick++;
	if (botTick > 0 && (botTick - 1) % every == 0)
		printTick(botTick - 1);
	if (botTick >= maxTicks)
	{
		if ((botTick - 1) % every != 0)
			printTick(botTick - 1);
		printf("STOP %ld\n", botTick);
		exit(0);
	}

	memset(keysactive, 0, sizeof(keysactive));
	if (botTick > 0)
	{
		long t = botTick - 1;
		player[0].invulnerable_ticks = 2;
		if (player[0].armor < 10)
			player[0].armor = 10;
		bool left = (t / 50) % 2 == 0;
		keysactive[keySettings[KEY_SETTING_FIRE]] = 1;
		keysactive[keySettings[KEY_SETTING_LEFT]] = left;
		keysactive[keySettings[KEY_SETTING_RIGHT]] = !left;
	}
}

// reallyEndLevel at the bottom of level_loop.
void bot_level_end(void)
{
	printTick(botTick);
	printf("END %ld next %u dead %d\n", botTick + 1, nextLevel, all_players_dead());
	exit(0);
}

// JE_nextEpisode: the script reached ]Q[.
void bot_episode_end(void)
{
	printf("ROUTE %d %d -> episode %u ends: ]Q[ in section %u\n", routeEpisode, routeSection, episodeNum, mainLevel);
	exit(0);
}

int main(int argc, char **argv)
{
	if (argc < 5)
	{
		fprintf(stderr, "usage: driver route|play <data> <episode> <section> [ticks] [every]\n");
		return 2;
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	const char *mode = argv[1];
	customDataDirPath = argv[2];
	routeEpisode = atoi(argv[3]);
	routeSection = atoi(argv[4]);

	SDL_Init(0);
	if (!findDataFiles())
	{
		fprintf(stderr, "no data\n");
		return 1;
	}
	init_video();
	init_keyboard();
	loadPals();
	JE_loadMainShapeTables("tyrian.shp");
	audio_disabled = true;
	loadExtraShapes();
	JE_loadHelpText();
	memcpy(keySettings, defaultKeySettings, sizeof(keySettings));

	// opentyr.c's main loop and newGame() for "1 Player Full Game", normal difficulty (what
	// newOnePlayerGame in src/sim/newgame.ts follows).
	JE_initPlayerData();
	playDemo = false;
	gameLoaded = false;
	jumpSection = false;
	onePlayerAction = false;
	twoPlayerMode = false;
	JE_initEpisode(routeEpisode);
	difficultyLevel = DIFFICULTY_NORMAL;
	gameLoaded = true;
	initialDifficulty = difficultyLevel;
	const unsigned long initial_cash[] = { 10000, 15000, 20000, 30000 };
	player[0].cash = initial_cash[routeEpisode - 1];

	mt_srand(1);
	mainLevel = routeSection;

	if (strcmp(mode, "route") == 0)
	{
		constantPlay = true;
		JE_loadMap();
		printf("ROUTE %d %d -> episode %u main %u level '%s' next %u file %u\n", routeEpisode, routeSection, episodeNum,
		       mainLevel, levelName, nextLevel, lvlFileNum);
		return 0;
	}

	maxTicks = argc > 5 ? atol(argv[5]) : 60000;
	every = argc > 6 ? atol(argv[6]) : 1;
	JE_main();
	return 0;
}
