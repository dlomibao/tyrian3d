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
//   driver play <data> <episode> <section> <ticks> <every> <mode>
//       [arcade] The same, in another kind of game (mode): `arcade` (1 Player Arcade), `sa1`..`sa7`
//       (a Super Arcade ship) or `supertyrian` (ENGAGE), set up as newGame(), newSuperArcadeGame()
//       and newSuperTyrianGame() do once their menus have returned (tyrian2.c L3529-3675; the
//       menus themselves wait for a player). The front weapon keeps its power (it's the lives),
//       and each sampled tick gets an `A` line with the ship's arcade state.
//   driver play2 <data> <episode> <section> <ticks> [every]
//       The same for a two-player game (newGame's "2 Player Arcade": Silver Ship and dragonwing, one
//       difficulty step harder, player 1 on the keyboard and player 2 on the mouse). Player 1 is
//       the bot above; player 2 (rear weapon power 3, so 3 lives) is not invulnerable: it fires,
//       steers toward player 1 until the two link, turns the linked gun, then breaks away (see
//       bot2Mouse). The lines also print player 2 and the link.
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
static const char *gameMode = "full";  // [arcade]
static bool twoPlayers = false;

// keyboard.c's mouseGetRelativePosition is patched (run.sh) to return these: player 2's mouse.
int bot_mouse_x, bot_mouse_y;

static void printTick(long k)
{
	int enemies = 0;
	for (int i = 0; i < 100; i++)
		if (enemyAvail[i] != 1)
			enemies++;
	printf("T %ld %u %u %u %u %u %d %d %lu %u %d %u %u\n", k, curLoc, eventLoc, backMove, backMove2, enemyOnScreen,
	       player[0].x, player[0].y, player[0].cash, enemyKilled, enemies, endLevel, levelEnd);
	if (strcmp(gameMode, "full") != 0)  // [arcade]
		printf("A %ld %u %u %u %u %u %u %u %u %u %u %u\n", k, player[0].items.weapon[FRONT_WEAPON].id,
		       player[0].items.weapon[FRONT_WEAPON].power, player[0].items.weapon[REAR_WEAPON].id,
		       player[0].items.weapon[REAR_WEAPON].power, player[0].items.special, player[0].items.sidekick[0],
		       player[0].items.sidekick[1], *player[0].lives, player[0].purple_balls_needed, superArcadePowerUp, power);
	if (twoPlayers)
		printf("P %ld %d %d %lu %u %u %d %u %d %d %.4f %d %d\n", k, player[1].x, player[1].y, player[1].cash, player[1].armor,
		       *player[1].lives, player[1].is_alive, player[1].exploding_ticks, twoPlayerLinked, twoPlayerMode,
		       linkGunDirec, player[1].shield, player[0].shield);
}

// Player 2's mouse for the bot's tick t, in the 300-tick cycle: steer toward player 1 until the two
// are stopped within 8 pixels (they link), then circle with fire held (turns the linked gun), then
// move without firing (breaks the link). Mirrored by botTick2 in tests/sim/bot.ts.
static void bot2Mouse(long t, int *dx, int *dy, bool *fire)
{
	long phase = t % 300;
	int ddx = player[0].x - player[1].x, ddy = player[0].y - player[1].y;
	*dx = *dy = 0;
	*fire = true;
	if (phase < 150)
	{
		if (abs(ddx) >= 6 || abs(ddy) >= 6)
		{
			*dx = ddx > 12 ? 12 : ddx < -12 ? -12 : ddx;
			*dy = ddy > 12 ? 12 : ddy < -12 ? -12 : ddy;
		}
	}
	else if (phase < 250)
	{
		static const int circle[4][2] = { { 8, 0 }, { 0, 8 }, { -8, 0 }, { 0, -8 } };
		*dx = circle[(phase / 10) % 4][0];
		*dy = circle[(phase / 10) % 4][1];
	}
	else
	{
		*fire = false;
		*dx = phase < 275 ? -10 : 10;
		*dy = -6;
	}
}

void bot_level_loaded(void)
{
	if (botTick >= 0)
		return;
	printf("LEVEL '%s' main %u next %u file %u galaga %d onePlayerAction %d superTyrian %d ship %u weapon %u\n", levelName,
	       mainLevel, nextLevel, lvlFileNum, galagaMode, onePlayerAction, superTyrian, player[0].items.ship,
	       player[0].items.weapon[FRONT_WEAPON].id);
	if (strcmp(gameMode, "full") == 0)  // [arcade] in arcade games the front weapon's power is the lives
		player[0].items.weapon[FRONT_WEAPON].power = 11;
	if (twoPlayers)
	{
		printf("PLAYERS twoPlayerMode %d difficulty %d input %u %u ship2 %u rear2 %u\n", twoPlayerMode, difficultyLevel,
		       inputDevice[0], inputDevice[1], player[1].items.ship, player[1].items.weapon[REAR_WEAPON].id);
		player[1].items.weapon[REAR_WEAPON].power = 3;
	}
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
	bot_mouse_x = bot_mouse_y = 0;
	mouseButtonsDown = 0;
	if (twoPlayers && botTick > 0)
	{
		bool fire;
		bot2Mouse(botTick - 1, &bot_mouse_x, &bot_mouse_y, &fire);
		mouseButtonsDown = fire ? SDL_BUTTON_LMASK : 0;
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
		fprintf(stderr, "usage: driver route|play|play2 <data> <episode> <section> [ticks] [every] [mode]\n");
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

	twoPlayers = strcmp(mode, "play2") == 0;

	// opentyr.c's main loop and newGame() for "1 Player Full Game", normal difficulty (what
	// newOnePlayerGame in src/sim/newgame.ts follows); for play2, newGame()'s "2 Player Arcade"
	// (tyrian2.c L3533-3575, what newTwoPlayerGame in src/sim/twoplayer.ts follows).
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
	if (twoPlayers)
	{
		twoPlayerMode = true;
		for (uint i = 0; i < COUNTOF(player); ++i)
			player[i].cash = 0;
		player[0].items.ship = 11;  // Silver Ship
		difficultyLevel++;  // Make it one step harder for 2-player mode!
		inputDevice[0] = 1;
		inputDevice[1] = 2;
	}

	// [arcade] the other kinds of game (see the usage above)
	if (argc > 7)
		gameMode = argv[7];
	if (strcmp(gameMode, "arcade") == 0)
	{
		onePlayerAction = true;  // gameplaySelect
		player[0].cash = 0;      // newGame()
		player[0].items.ship = 8;  // Stalker
	}
	else if (strncmp(gameMode, "sa", 2) == 0)
	{
		unsigned int i = atoi(gameMode + 2) - 1;  // newSuperArcadeGame(i)
		player[0].items.ship = SAShip[i];
		twoPlayerMode = false;
		onePlayerAction = true;
		superArcadeMode = i + 1;
		gameLoaded = true;
		initialDifficulty = ++difficultyLevel;
		player[0].cash = 0;
		player[0].items.weapon[FRONT_WEAPON].id = SAWeapon[i][0];
		player[0].items.special = SASpecialWeapon[i];
		if (superArcadeMode == SA_NORTSHIPZ)
		{
			for (uint j = 0; j < COUNTOF(player[0].items.sidekick); ++j)
				player[0].items.sidekick[j] = 24;  // Companion Ship Quicksilver
		}
	}
	else if (strcmp(gameMode, "supertyrian") == 0)
	{
		initialDifficulty = DIFFICULTY_ZINGLON;  // newSuperTyrianGame()
		JE_initEpisode(1);
		constantDie = false;
		superTyrian = true;
		onePlayerAction = true;
		gameLoaded = true;
		difficultyLevel = initialDifficulty;
		player[0].cash = 0;
		player[0].items.ship = 13;                     // The Stalker 21.126
		player[0].items.weapon[FRONT_WEAPON].id = 39;  // Atomic RailGun
	}

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
