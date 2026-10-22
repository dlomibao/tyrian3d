// Shop cross-check driver: runs OpenTyrian's real item screen (JE_itemScreen, via JE_loadMap and
// the episode script's `]I[`) on scripted key presses and prints the screen's state each time it
// reads a key, in the format tests/sim/shop.test.ts produces from the TypeScript port
// (src/sim/game_menu.ts). Built by build.sh against an OpenTyrian checkout; links all of
// OpenTyrian's src/*.c except game_menu.c, which it includes so it can see that file's statics.
//
// Script lines: <section> <cash> [item=value ...] <key> <key> ...
//   items: ship front fpow rear rpow shield gen sk0 sk1 (set in both items and last_items)
//   keys: up down left right enter esc slash
// The keys must end the item screen by choosing a destination.
//
// Usage: driver <data dir> <script>
#include "config.h"
#include "demo.h"
#include "joystick.h"
#include "episodes.h"
#include "file.h"
#include "helptext.h"
#include "keyboard.h"
#include "mainint.h"
#include "mtrand.h"
#include "nortsong.h"
#include "palette.h"
#include "params.h"
#include "player.h"
#include "sprite.h"
#include "tyrian2.h"
#include "varz.h"
#include "video.h"

#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Every key the item screen reads goes through hook_keyboardGetInput, which prints the state
// first; hook_hasInput feeds the scripted keys one at a time as the screen waits for input.
bool hook_keyboardGetInput(KeyboardInput *out_input);
bool hook_hasInput(InputFlags flags);
#define keyboardGetInput hook_keyboardGetInput
#define hasInput hook_hasInput
#include "game_menu.c"
#undef keyboardGetInput
#undef hasInput

static SDL_Scancode keys[1024];
static int keyCount, nextKey;

static void print_state(void)
{
	const PlayerItems *it = &player[0].items;
	printf("K menu=%d sel=%d cash=%lu", curMenu, curSel[curMenu], player[0].cash);
	if (curMenu == MENU_UPGRADE_SUB)
		printf(" left=%d upg=%d", JE_cashLeft(), upgradeCost);
	printf(" items=%d,%d:%d,%d:%d,%d,%d,%d,%d mode=%d power=%d%d%d\n",
	       it->ship, it->weapon[0].id, it->weapon[0].power, it->weapon[1].id, it->weapon[1].power,
	       it->shield, it->generator, it->sidekick[0], it->sidekick[1], player[0].weapon_mode,
	       leftPower, rightPower, rightPower && rightPowerAfford);
}

static bool printedAvail;

bool hook_keyboardGetInput(KeyboardInput *out_input)
{
	if (!printedAvail)
	{
		printedAvail = true;
		for (int i = 0; i < 9; i++)
		{
			printf("A %d", i);
			for (int j = 0; j < itemAvailMax[i]; j++)
				printf(" %d", itemAvail[i][j]);
			printf("\n");
		}
	}
	if (keyboardHasInput())
		print_state();
	return keyboardGetInput(out_input);
}

bool hook_hasInput(InputFlags flags)
{
	if (!keyboardHasInput())
	{
		if (nextKey >= keyCount)
		{
			fprintf(stderr, "script ran out of keys\n");
			exit(2);
		}
		push_key(keys[nextKey++]);
		handleSdlEvents();
	}
	return hasInput(flags);
}

static Uint8 *item_field(PlayerItems *it, const char *name)
{
	if (!strcmp(name, "ship")) return &it->ship;
	if (!strcmp(name, "front")) return &it->weapon[0].id;
	if (!strcmp(name, "fpow")) return &it->weapon[0].power;
	if (!strcmp(name, "rear")) return &it->weapon[1].id;
	if (!strcmp(name, "rpow")) return &it->weapon[1].power;
	if (!strcmp(name, "shield")) return &it->shield;
	if (!strcmp(name, "gen")) return &it->generator;
	if (!strcmp(name, "sk0")) return &it->sidekick[0];
	if (!strcmp(name, "sk1")) return &it->sidekick[1];
	return NULL;
}

int main(int argc, char **argv)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	customDataDirPath = argv[1];
	FILE *script = fopen(argv[2], "r");

	SDL_Init(0);
	if (!findDataFiles())
		return 1;
	init_video();
	loadPals();
	JE_loadMainShapeTables("tyrian.shp");
	JE_loadHelpText();
	episodeNum = 0;
	JE_initEpisode(1);

	char line[4096];
	while (fgets(line, sizeof line, script))
	{
		if (line[0] == '#' || line[0] == '\n')
			continue;
		printf("S %s", line);

		mt_srand(1);
		JE_initPlayerData();
		playDemo = false;
		jumpSection = false;
		onePlayerAction = false;
		twoPlayerMode = false;
		difficultyLevel = DIFFICULTY_NORMAL;
		initialDifficulty = difficultyLevel;
		gameLoaded = true;
		printedAvail = false;
		keyboardClearInput();
		keyCount = nextKey = 0;
		upgradeCost = downgradeCost = 0;

		char *tok = strtok(line, " \n");
		mainLevel = atoi(tok);
		player[0].cash = atol(strtok(NULL, " \n"));

		while ((tok = strtok(NULL, " \n")))
		{
			char *eq = strchr(tok, '=');
			if (eq)
			{
				*eq = '\0';
				*item_field(&player[0].items, tok) = atoi(eq + 1);
				*item_field(&player[0].last_items, tok) = atoi(eq + 1);
				continue;
			}
			SDL_Scancode sc =
				!strcmp(tok, "up") ? SDL_SCANCODE_UP :
				!strcmp(tok, "down") ? SDL_SCANCODE_DOWN :
				!strcmp(tok, "left") ? SDL_SCANCODE_LEFT :
				!strcmp(tok, "right") ? SDL_SCANCODE_RIGHT :
				!strcmp(tok, "enter") ? SDL_SCANCODE_RETURN :
				!strcmp(tok, "esc") ? SDL_SCANCODE_ESCAPE :
				SDL_SCANCODE_SLASH;
			keys[keyCount++] = sc;
		}

		JE_loadMap();

		print_state();
		printf("E mainLevel=%d level=%s\n", mainLevel, levelName);
	}
	return 0;
}
