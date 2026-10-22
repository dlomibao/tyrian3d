// Cross-check harness: runs the world half of JE_main's level loop with the real OpenTyrian code
// and prints a per-tick trace. Mirrors tests/sim/worldDriver.ts and the trace format of
// tests/sim/crosscheck.test.ts; built and run by run.sh. Links against all of OpenTyrian's
// src/*.c (GPL-2.0-or-later, like this repo), with opentyr.c's main renamed.
//
// Usage: harness <data dir> <mainLevel> <ticks> <episode> <constantPlay>
#include "backgrnd.h"
#include "config.h"
#include "episodes.h"
#include "file.h"
#include "helptext.h"
#include "lvllib.h"
#include "mtrand.h"
#include "palette.h"
#include "player.h"
#include "sprite.h"
#include "tyrian2.h"
#include "varz.h"
#include "video.h"
#include "nortsong.h"
#include "mainint.h"
#include "params.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern struct JE_EventRecType eventRec[];
extern JE_word levelEnemyMax, levelEnemyFrequency, levelEnemy[40];

static Uint8 lives0 = 0, lives1 = 0;

static void parallax(void)
{
	JE_word tempX = player[0].x;
	tempW = floorf((float)(260 - (tempX - 36)) / (260 - 36) * (24 * 3) - 1);
	mapX3Ofs   = tempW;
	mapX3Pos   = mapX3Ofs % 24;
	mapX3bpPos = 1 - (mapX3Ofs / 24);

	mapX2Ofs   = (tempW * 2) / 3;
	mapX2Pos   = mapX2Ofs % 24;
	mapX2bpPos = 1 - (mapX2Ofs / 24);

	oldMapXOfs = mapXOfs;
	mapXOfs    = mapX2Ofs / 2;
	mapXPos    = mapXOfs % 24;
	mapXbpPos  = 1 - (mapXOfs / 24);

	if (background3x1)
	{
		mapX3Ofs = mapXOfs;
		mapX3Pos = mapXPos;
		mapX3bpPos = mapXbpPos - 1;
	}
}

static void drawBackground2(void)
{
	if (wild && !background2notTransparent)
		draw_background_2_blend(VGAScreen);
	else
		draw_background_2(VGAScreen);
}

static void worldTick(void)
{
	int lastEnemyOnScreen;

	if (mapYPos <= BKwrap1)
		mapYPos = BKwrap1to;
	if (mapY2Pos <= BKwrap2)
		mapY2Pos = BKwrap2to;
	if (mapY3Pos <= BKwrap3)
		mapY3Pos = BKwrap3to;

	if (!endLevel)
	{
		oldMapX3Ofs = mapX3Ofs;
		enemyOnScreen = 0;
	}

	while (eventRec[eventLoc-1].eventtime <= curLoc && eventLoc <= maxEvent)
		JE_eventSystem();

	JE_checkSmoothies();

	if (forceEvents && !backMove)
		curLoc++;

	if (map1YDelayMax > 1 && backMove < 2)
		backMove = (map1YDelay == 1) ? 1 : 0;

	if (astralDuration == 0)
		draw_background_1(VGAScreen);

	if (--map1YDelay == 0)
	{
		map1YDelay = map1YDelayMax;
		curLoc += backMove;
		backPos += backMove;
		if (backPos > 27)
		{
			backPos -= 28;
			mapY--;
			mapYPos -= 14;
		}
	}

	if (starActive || astralDuration > 0)
		update_and_draw_starfield(VGAScreen, starfield_speed);

	if (background2over == 3)
	{
		draw_background_2(VGAScreen);
		background2 = true;
	}
	if (background2over == 0)
		drawBackground2();

	lastEnemyOnScreen = enemyOnScreen;
	tempMapXOfs = mapXOfs;
	tempBackMove = backMove;
	JE_drawEnemy(50);
	JE_drawEnemy(100);

	if (enemyOnScreen == 0 || enemyOnScreen == lastEnemyOnScreen)
	{
		if (stopBackgroundNum == 1)
			stopBackgroundNum = 9;
	}

	if (background2over == 1)
		drawBackground2();

	if (background3over == 2)
		draw_background_3(VGAScreen);

	if (enemiesActive && mt_rand() % 100 > levelEnemyFrequency)
	{
		tempW = levelEnemy[mt_rand() % levelEnemyMax];
		b = JE_newEnemy(0, tempW, 0);
	}

	if (!skyEnemyOverAll)
	{
		lastEnemyOnScreen = enemyOnScreen;
		tempMapXOfs = mapX2Ofs;
		tempBackMove = 0;
		JE_drawEnemy(25);
		if (enemyOnScreen == lastEnemyOnScreen && stopBackgroundNum == 2)
			stopBackgroundNum = 9;
	}

	if (background3over == 0)
		draw_background_3(VGAScreen);

	if (!topEnemyOver)
	{
		tempMapXOfs = (background3x1 == 0) ? oldMapX3Ofs : mapXOfs;
		tempBackMove = backMove3;
		JE_drawEnemy(75);
	}

	parallax();

	for (int z = 0; z < ENEMY_SHOT_MAX; z++)
	{
		if (enemyShotAvail[z] == 0)
		{
			enemyShot[z].sxm += enemyShot[z].sxc;
			enemyShot[z].sx += enemyShot[z].sxm;

			if (enemyShot[z].tx != 0)
			{
				if (enemyShot[z].sx > player[0].x)
				{
					if (enemyShot[z].sxm > -enemyShot[z].tx)
						enemyShot[z].sxm--;
				}
				else
				{
					if (enemyShot[z].sxm < enemyShot[z].tx)
						enemyShot[z].sxm++;
				}
			}

			enemyShot[z].sym += enemyShot[z].syc;
			enemyShot[z].sy += enemyShot[z].sym;

			if (enemyShot[z].ty != 0)
			{
				if (enemyShot[z].sy > player[0].y)
				{
					if (enemyShot[z].sym > -enemyShot[z].ty)
						enemyShot[z].sym--;
				}
				else
				{
					if (enemyShot[z].sym < enemyShot[z].ty)
						enemyShot[z].sym++;
				}
			}

			if (enemyShot[z].duration-- == 0 || enemyShot[z].sy > 190 || enemyShot[z].sy <= -14 || enemyShot[z].sx > 275 || enemyShot[z].sx <= 0)
				enemyShotAvail[z] = true;
		}
	}

	if (background3over == 1)
		draw_background_3(VGAScreen);

	if (topEnemyOver)
	{
		tempMapXOfs = (background3x1 == 0) ? oldMapX3Ofs : oldMapXOfs;
		tempBackMove = backMove3;
		JE_drawEnemy(75);
	}

	if (skyEnemyOverAll)
	{
		lastEnemyOnScreen = enemyOnScreen;
		tempMapXOfs = mapX2Ofs;
		tempBackMove = 0;
		JE_drawEnemy(25);
		if (enemyOnScreen == lastEnemyOnScreen && stopBackgroundNum == 2)
			stopBackgroundNum = 9;
	}

	if (background2over == 2)
		drawBackground2();

	JE_drawSP();

	if (filterActive)
		JE_filterScreen(levelFilter, levelBrightness);

	draw_boss_bar();

	if (stopBackgroundNum == 9 && backMove == 0 && !enemyStillExploding)
	{
		backMove = 1;
		backMove2 = 2;
		backMove3 = 3;
		explodeMove = 2;
		stopBackgroundNum = 0;
		stopBackgrounds = false;
		if (waitToEndLevel)
		{
			endLevel = true;
			levelEnd = 40;
		}
	}

	if (!endLevel && enemyOnScreen == 0)
	{
		if (readyToEndLevel && !enemyStillExploding)
		{
			if (levelTimerCountdown > 0)
				levelTimer = false;
			readyToEndLevel = false;
			endLevel = true;
			levelEnd = 40;
		}
		if (stopBackgrounds)
		{
			stopBackgrounds = false;
			backMove = 1;
			backMove2 = 2;
			backMove3 = 3;
			explodeMove = 2;
		}
	}
}

static void initLevelWorld(void)
{
	endLevel = false;
	reallyEndLevel = false;
	playerEndLevel = false;

	oldDifficultyLevel = difficultyLevel;
	if (episodeNum == EPISODE_AVAILABLE)
		difficultyLevel--;
	if (difficultyLevel < DIFFICULTY_EASY)
		difficultyLevel = DIFFICULTY_EASY;

	mapY = 300 - 8;
	mapY2 = 600 - 8;
	mapY3 = 600 - 8;
	mapYPos = &megaData1.mainmap[mapY][0] - 1;
	mapY2Pos = &megaData2.mainmap[mapY2][0] - 1;
	mapY3Pos = &megaData3.mainmap[mapY3][0] - 1;
	mapXPos = 0;
	mapXOfs = 0;
	mapX2Pos = 0;
	mapX3Pos = 0;
	mapX3Ofs = 0;
	mapXbpPos = 0;
	mapX2bpPos = 0;
	mapX3bpPos = 0;

	map1YDelay = 1;
	map1YDelayMax = 1;
	map2YDelay = 1;
	map2YDelayMax = 1;

	backPos = 0;
	backPos2 = 0;
	backPos3 = 0;
	power = 0;
	starfield_speed = 1;

	levelEnd = 255;
	levelEndWarp = -4;
	levelEndFxWait = 0;

	bonusLevel = false;
	readyToEndLevel = false;
	firstGameOver = true;
	eventLoc = 1;
	curLoc = 0;
	backMove = 1;
	backMove2 = 2;
	backMove3 = 3;
	explodeMove = 2;
	enemiesActive = true;
	stopBackgrounds = false;
	stopBackgroundNum = 0;
	background3x1   = false;
	background3x1b  = false;
	background3over = 0;
	background2over = 1;
	topEnemyOver = false;
	skyEnemyOverAll = false;
	smallEnemyAdjust = false;
	starActive = true;
	enemyContinualDamage = false;
	levelEnemyFrequency = 96;
	quitRequested = false;

	for (unsigned int i = 0; i < COUNTOF(boss_bar); i++)
		boss_bar[i].link_num = 0;

	forceEvents = false;
	superEnemy254Jump = 0;

	filterActive = true;
	filterFade = true;
	filterFadeStart = false;
	levelFilter = -99;
	levelBrightness = -14;
	levelBrightnessChg = 1;

	background2notTransparent = false;

	cubeMax = 0;
	flash = 0;
	flashChange = 1;
	displayTime = 0;

	initialize_starfield();

	damageRate = 2;
	totalEnemy = 0;
	enemyKilled = 0;
	astralDuration = 0;

	memset(enemyAvail,       1, sizeof(enemyAvail));
	for (uint i = 0; i < COUNTOF(enemyShotAvail); i++)
		enemyShotAvail[i] = 1;
	memset(globalFlags,      0, sizeof(globalFlags));
	memset(explosions,       0, sizeof(explosions));
	memset(rep_explosions,   0, sizeof(rep_explosions));
	memset(soundQueue,       0, sizeof(soundQueue));
	soundQueue[3] = 33;  // V_GOOD_LUCK
	memset(enemySpriteSheetIds, 0, sizeof(enemySpriteSheetIds));
	memset(enemy,               0, sizeof(enemy));
	memset(smoothies, 0, sizeof(smoothies));
	levelTimer = false;
	randomExplosions = false;
	last_superpixel = 0;
	memset(superpixels, 0, sizeof(superpixels));
	returnActive = false;
	galagaShotFreq = 0;
	if (galagaMode)
		difficultyLevel = DIFFICULTY_NORMAL;
	galagaLife = 10000;

	BKwrap1 = BKwrap1to = &megaData1.mainmap[1][0];
	BKwrap2 = BKwrap2to = &megaData2.mainmap[1][0];
	BKwrap3 = BKwrap3to = &megaData3.mainmap[1][0];
}

static void dump(int tick)
{
	printf("T %d %d %d %d %d %d %ld %ld %ld %d %d %d %d %d %d\n", tick, curLoc, eventLoc, backPos, backPos2, backPos3,
	       (long)(mapYPos - &megaData1.mainmap[0][0]), (long)(mapY2Pos - &megaData2.mainmap[0][0]), (long)(mapY3Pos - &megaData3.mainmap[0][0]),
	       backMove, backMove2, backMove3, enemyOnScreen, levelBrightness, levelFilter);
	for (int i = 0; i < 100; i++)
		if (enemyAvail[i] != 1)
			printf("E %d %d %d %d %d %d %d %d %d %d %d %d\n", i, enemy[i].enemytype, enemy[i].ex, enemy[i].ey, enemy[i].exc, enemy[i].eyc,
			       enemy[i].armorleft, enemy[i].enemycycle, enemy[i].linknum, enemyAvail[i], enemy[i].filter, enemy[i].mapoffset);
	for (int z = 0; z < ENEMY_SHOT_MAX; z++)
		if (!enemyShotAvail[z])
			printf("S %d %d %d %d %d %d\n", z, enemyShot[z].sx, enemyShot[z].sy, enemyShot[z].sxm, enemyShot[z].sym, enemyShot[z].sgr);
	for (int i = 0; i < 8; i++)
		if (soundQueue[i])
		{
			printf("Q %d %d\n", i, soundQueue[i]);
			soundQueue[i] = 0;
		}
}

int main(int argc, char *argv[])
{
	int mainLevelArg = argc > 2 ? atoi(argv[2]) : 3;
	int ticks = argc > 3 ? atoi(argv[3]) : 3000;
	int ep = argc > 4 ? atoi(argv[4]) : 1;
	constantPlay = argc > 5 ? atoi(argv[5]) : 0;
	customDataDirPath = argv[1];
	SDL_Init(0);
	if (!findDataFiles())
	{
		fprintf(stderr, "no data\n");
		return 1;
	}
	init_video();
	loadPals();
	JE_loadMainShapeTables("tyrian.shp");
	JE_loadHelpText();

	processorType = 4;
	wild = false;
	superWild = false;
	background2 = true;
	filtrationAvail = false;
	explosionTransparent = true;
	difficultyLevel = DIFFICULTY_NORMAL;
	initialDifficulty = DIFFICULTY_NORMAL;
	player[0].lives = &lives0;
	player[1].lives = &lives1;

	episodeNum = 0;
	JE_initEpisode(ep);

	mt_srand(1);
	mainLevel = mainLevelArg;
	JE_loadMap();
	initLevelWorld();
	player[0].x = 100;
	player[0].y = 180;
	player[0].is_alive = true;

	for (int tick = 0; tick < ticks; tick++)
	{
		worldTick();
		dump(tick);
	}
	printf("R %lu\n", mt_rand());
	return 0;
}
