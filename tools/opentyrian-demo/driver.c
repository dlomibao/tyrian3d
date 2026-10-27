// Cross-check driver for tests/sim/demo.test.ts: plays one of Tyrian's attract-mode demos
// (demo.1 .. demo.5) through OpenTyrian's real JE_main with playDemo set, the way titleScreen's idle
// timer starts one (tyrian2.c L3304-3311, then opentyr.c's main loop calls JE_main), and prints what
// the TypeScript port must reproduce. Built and run by run.sh in this directory, which first patches
// a copy of OpenTyrian's sources with the hooks called here (demo_level_tick, demo_level_end),
// makes demo.c's demoNum visible, and turns off the frame delay and save-game writes.
// Links against all of OpenTyrian's src/*.c (GPL-2.0-or-later, like this repo).
//
//   driver <data> <demo 1-5> [every]
//       Prints the demo's level, then one line every `every` ticks (default 1) and the last tick,
//       then END with the tick count and the next random number.
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
extern Uint8 demoNum;  // demo.c (made non-static by run.sh)

static long demoTick = -1;  // index of the level_loop pass in progress
static long every = 1;

static void printTick(long k)
{
	int enemies = 0;
	for (int i = 0; i < 100; i++)
		if (enemyAvail[i] != 1)
			enemies++;
	printf("T %ld %u %u %u %u %u %d %d %lu %u %d %u %u %d %d %d %d\n", k, curLoc, eventLoc, backMove, backMove2,
	       enemyOnScreen, player[0].x, player[0].y, player[0].cash, enemyKilled, enemies, endLevel, levelEnd,
	       player[0].armor, player[0].shield, player[0].is_alive, player[0].weapon_mode);
}

// Top of level_loop: report the pass that just finished.
void demo_level_tick(void)
{
	if (demoTick < 0)
		printf("LEVEL '%s' episode %u file %u song %u ship %u front %u/%u rear %u/%u sidekicks %u %u shield %u generator %u special %u armor %d\n",
		       levelName, episodeNum, lvlFileNum, levelSong, player[0].items.ship, player[0].items.weapon[FRONT_WEAPON].id,
		       player[0].items.weapon[FRONT_WEAPON].power, player[0].items.weapon[REAR_WEAPON].id,
		       player[0].items.weapon[REAR_WEAPON].power, player[0].items.sidekick[LEFT_SIDEKICK],
		       player[0].items.sidekick[RIGHT_SIDEKICK], player[0].items.shield, player[0].items.generator,
		       player[0].items.special, player[0].armor);
	demoTick++;
	if (demoTick > 0 && (demoTick - 1) % every == 0)
		printTick(demoTick - 1);
}

// reallyEndLevel at the bottom of level_loop.
void demo_level_end(void)
{
	printTick(demoTick);
	printf("END %ld dead %d R %lu\n", demoTick + 1, all_players_dead(), mt_rand());
	exit(0);
}

int main(int argc, char **argv)
{
	if (argc < 3)
	{
		fprintf(stderr, "usage: driver <data> <demo 1-5> [every]\n");
		return 2;
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	customDataDirPath = argv[1];
	int which = atoi(argv[2]);
	every = argc > 3 ? atol(argv[3]) : 1;

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

	// opentyr.c's main loop before titleScreen (L873-880), then titleScreen's idle timeout
	// (tyrian2.c L3304-3311) and JE_main. beginPlayDemo picks demo ++demoNum.
	JE_initPlayerData();
	gameLoaded = false;
	jumpSection = false;
	playDemo = true;
	demoNum = which - 1;

	JE_main();
	printf("RETURNED\n");
	return 0;
}
