// Cross-check driver for tests/sim/playerTrace.test.ts: runs OpenTyrian's real player code for a
// scripted input sequence and prints a per-tick trace. Built and run by build.sh in this directory.
// Usage: driver <datadir> <script> > trace.txt
#include "backgrnd.h"
#include "config.h"
#include "episodes.h"
#include "file.h"
#include "demo.h"
#include "helptext.h"
#include "keyboard.h"
#include "mainint.h"
#include "mtrand.h"
#include "opentyr.h"
#include "player.h"
#include "shots.h"
#include "sprite.h"
#include "tyrian2.h"
#include "varz.h"
#include "video.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

extern const char *customDataDirPath;

static void place_enemy(int evalue, bool scoreitem, int armorleft, int type)
{
	memset(&enemy[0], 0, sizeof(enemy[0]));
	enemy[0].ex = player[0].x;
	enemy[0].ey = player[0].y;
	enemy[0].mapoffset = 0;
	enemy[0].evalue = evalue;
	enemy[0].scoreitem = scoreitem;
	enemy[0].armorleft = armorleft;
	enemy[0].enemytype = type;
	enemyAvail[0] = 0;
}

int main(int argc, char **argv)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	customDataDirPath = argv[1];
	FILE *script = fopen(argv[2], "r");

	VGAScreen = VGAScreenSeg = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);
	game_screen = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);
	VGAScreen2 = SDL_CreateRGBSurface(0, 320, 200, 8, 0, 0, 0, 0);

	JE_loadHelpText();
	JE_loadMainShapeTables("tyrian.shp");
	JE_initEpisode(1);
	memcpy(keySettings, defaultKeySettings, sizeof(keySettings));

	mt_srand(1);

	// opentyr.c main loop + newGame() for "1 player full game", episode 1, normal
	JE_initPlayerData();
	playDemo = false;
	gameLoaded = false;
	jumpSection = false;
	onePlayerAction = false;
	twoPlayerMode = false;
	difficultyLevel = DIFFICULTY_NORMAL;
	gameLoaded = true;
	initialDifficulty = difficultyLevel;
	player[0].cash = 10000;

	// start_level_first, player/shot statements (same subset as startLevelPlayerSetup)
	for (uint i = 0; i < COUNTOF(player); ++i)
		player[i].is_alive = true;
	player[0].x = 100;
	player[0].y = 180;
	player[1].x = 190;
	player[1].y = 180;
	for (uint i = 0; i < COUNTOF(player); ++i)
	{
		for (uint j = 0; j < COUNTOF(player->old_x); ++j)
		{
			player[i].old_x[j] = player[i].x - (19 - j);
			player[i].old_y[j] = player[i].y - 18;
		}
		player[i].last_x_shot_move = player[i].x;
		player[i].last_y_shot_move = player[i].y;
	}
	JE_drawOptions();
	power = 0;
	JE_getShipInfo();
	for (uint i = 0; i < COUNTOF(player); ++i)
	{
		player[i].x_velocity = 0;
		player[i].y_velocity = 0;
		player[i].invulnerable_ticks = 100;
	}
	levelEnd = 255;
	levelEndWarp = -4;
	levelEndFxWait = 0;
	for (temp = 0; temp < 3; temp++)
		button[temp] = false;
	JE_drawTextWindow(miscText[20]);
	shieldWait = 1;
	shieldT = shields[player[0].items.shield].tpwr * 20;
	for (uint i = 0; i < COUNTOF(player); ++i)
	{
		player[i].shield = shields[player[i].items.shield].mpwr;
		player[i].shield_max = player[i].shield * 2;
	}
	for (uint i = 0; i < COUNTOF(player); ++i)
		player[i].superbombs = 0;
	twoPlayerLinked = false;
	linkGunDirec = M_PI;
	for (uint i = 0; i < COUNTOF(player); ++i)
		calc_purple_balls_needed(&player[i]);
	damageRate = 2;
	chargeWait = 5;
	chargeLevel = 0;
	chargeMax = 5;
	chargeGr = 0;
	chargeGrWait = 3;
	portConfigChange = false;
	constantLastX = -1;
	for (uint i = 0; i < COUNTOF(player); ++i)
		player[i].exploding_ticks = 0;
	memset(enemyAvail, 1, sizeof(enemyAvail));
	memset(playerShotData, 0, sizeof(playerShotData));
	memset(shotAvail, 0, sizeof(shotAvail));
	memset(shotMultiPos, 0, sizeof(shotMultiPos));
	memset(shotRepeat, 1, sizeof(shotRepeat));
	memset(button, 0, sizeof(button));
	memset(SFCurrentCode, 0, sizeof(SFCurrentCode));
	memset(SFExecuted, 0, sizeof(SFExecuted));
	zinglonDuration = 0;
	specialWait = 0;
	nextSpecialWait = 0;
	optionAttachmentMove = 0;
	optionAttachmentLinked = true;
	background2 = true;
	firstGameOver = true;
	portConfigDone = false;

	int air_enemy = 1;
	while ((enemyDat[air_enemy].explosiontype & 1) != 0)
		air_enemy++;

	char line[256];
	int t = 0;
	while (fgets(line, sizeof line, script))
	{
		if (line[0] == '#' || line[0] == '\n')
			continue;
		if (line[0] == '!')
		{
			int f, r, l, rt, pw;
			sscanf(line, "!loadout %d %d %d %d %d", &f, &r, &l, &rt, &pw);
			player[0].items.weapon[0].id = f;
			player[0].items.weapon[1].id = r;
			player[0].items.sidekick[0] = l;
			player[0].items.sidekick[1] = rt;
			player[0].items.weapon[0].power = pw;
			player[0].items.weapon[1].power = pw;
			calc_purple_balls_needed(&player[0]);
			JE_drawOptions();
			continue;
		}
		int count;
		char keys[32], event[32] = "";
		if (sscanf(line, "%d %31s %31s", &count, keys, event) < 2)
			continue;

		for (int n = 0; n < count; n++)
		{
			memset(keysactive, 0, sizeof(keysactive));
			keysactive[keySettings[KEY_SETTING_UP]] = strchr(keys, 'U') != NULL;
			keysactive[keySettings[KEY_SETTING_DOWN]] = strchr(keys, 'D') != NULL;
			keysactive[keySettings[KEY_SETTING_LEFT]] = strchr(keys, 'L') != NULL;
			keysactive[keySettings[KEY_SETTING_RIGHT]] = strchr(keys, 'R') != NULL;
			keysactive[keySettings[KEY_SETTING_FIRE]] = strchr(keys, 'F') != NULL;
			keysactive[keySettings[KEY_SETTING_CHANGE_FIRE]] = strchr(keys, 'C') != NULL;
			keysactive[keySettings[KEY_SETTING_LEFT_SIDEKICK]] = strchr(keys, 'l') != NULL;
			keysactive[keySettings[KEY_SETTING_RIGHT_SIDEKICK]] = strchr(keys, 'r') != NULL;

			if (n == 0)
			{
				if (strcmp(event, "P") == 0)
					place_enemy(-1, true, 0, 1);
				else if (strcmp(event, "B") == 0)
					place_enemy(30000, false, 0, 1);
				else if (strcmp(event, "$") == 0)
					place_enemy(100, true, 0, 1);
				else if (strcmp(event, "E") == 0)
					place_enemy(0, false, 10, air_enemy);
				else if (strcmp(event, "X") == 0)
				{
					player[0].shield = 0;
					player[0].armor = 1;
					player[0].invulnerable_ticks = 0;
					place_enemy(0, false, 10, air_enemy);
				}
				else if (strcmp(event, "T") == 0)
				{
					place_enemy(0, false, 50, air_enemy);
					enemy[0].ex = 150;
					enemy[0].ey = 30;
				}
				else if (strcmp(event, "W") == 0)
				{
					endLevel = true;
					levelEnd = 40;
				}
			}

			++t;
			memset(soundQueue, 0, sizeof(soundQueue));

			// --- JE_main tick, player parts ---
			if (!endLevel && textErase > 0)
				--textErase;
			power += powerAdd;
			if (power > 900)
				power = 900;

			for (int z = 0; z < MAX_PWEAPON; z++)
			{
				if (shotAvail[z] != 0)
				{
					bool is_special = false;
					int sx = 0, sy = 0;
					JE_byte chain, playerNum, blast;
					JE_word rw, rh;
					JE_integer damage;
					player_shot_move_and_draw(z, &is_special, &sx, &sy, &damage, &blast, &chain, &playerNum, &rw, &rh);
				}
			}
			for (uint i = 0; i < COUNTOF(player); ++i)
			{
				player[i].last_x_shot_move = player[i].x;
				player[i].last_y_shot_move = player[i].y;
			}
			for (uint i = 0; i < (twoPlayerMode ? 2 : 1); ++i)
				if (player[i].is_alive && !endLevel)
					JE_playerCollide(&player[i], i + 1);
			if (firstGameOver)
				JE_mainGamePlayerFunctions();
			if (!portConfigChange)
				portConfigDone = true;

			// --- trace ---
			Player *p = &player[0];
			printf("%d p %d %d %d %d %u %u pw %u sh %u ar %u cash %lu wp %u pb %u sf %u %u %u %u rep %u te %u map %u %u %u inv %u mode %u sound %u %u",
			       t, p->x, p->y, p->x_velocity, p->y_velocity, p->mouseX, p->mouseY,
			       power, p->shield, p->armor, p->cash, p->items.weapon[0].power, p->purple_balls_needed,
			       SFCurrentCode[0][0], SFCurrentCode[0][1], SFCurrentCode[0][2], SFExecuted[0],
			       shotRepeat[0], textErase, mapXOfs, mapX2Ofs, mapX3Ofs, p->invulnerable_ticks, p->weapon_mode,
			       soundQueue[0], soundQueue[7]);
			printf(" alive %d ex %u le %u fx %u rel %d warp %d", p->is_alive, p->exploding_ticks, levelEnd, levelEndFxWait, reallyEndLevel, levelEndWarp);
			for (int i = 0; i < 2; i++)
				printf(" sk%d %d %d %d %u %u %u %u %u", i, p->sidekick[i].x, p->sidekick[i].y, p->sidekick[i].ammo, p->sidekick[i].ammo_refill_ticks,
				       p->sidekick[i].animation_frame, p->sidekick[i].animation_enabled, p->sidekick[i].charge, p->sidekick[i].charge_ticks);
			printf(" rot %d att %d %d %d rep %u %u %u", (int)roundf(optionSatelliteRotate * 1000), optionAttachmentMove, optionAttachmentLinked, optionAttachmentReturn,
			       shotRepeat[1], shotRepeat[2], shotRepeat[3]);
			printf(" shots");
			for (int z = 0; z < MAX_PWEAPON; z++)
				if (shotAvail[z] != 0)
					printf(" %d:%d:%d:%d:%d:%u:%u:%u:%u:%u", z, playerShotData[z].shotX, playerShotData[z].shotY,
					       playerShotData[z].shotXM, playerShotData[z].shotYM, shotAvail[z], playerShotData[z].shotGr, playerShotData[z].shotDmg,
					       playerShotData[z].shotAni, playerShotData[z].aimAtEnemy);
			printf("\n");
		}
	}
	return 0;
}
