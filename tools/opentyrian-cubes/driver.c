// Data cube cross-check driver: runs OpenTyrian's real load_cube (game_menu.c L1739-1846) on every
// cube of every episode's cubetxt<episode>.dat and prints a digest of what it produced, in the
// format tests/sim/cubes.test.ts produces from the TypeScript port (src/sim/cubes.ts). The digest
// holds hashes instead of the text, so the fixture carries none of the game's text (D3). Built by
// build.sh against an OpenTyrian checkout; includes game_menu.c so it can see the cube[] static.
//
// Usage: driver <data dir>
#include "episodes.h"
#include "file.h"
#include "helptext.h"
#include "mainint.h"
#include "palette.h"
#include "sprite.h"
#include "video.h"

#include <SDL.h>
#include <stdio.h>
#include <string.h>

#include "game_menu.c"

/** FNV-1a over a string, continuing from h. */
static Uint32 fnv(Uint32 h, const char *s)
{
	for (; *s != '\0'; ++s)
	{
		h ^= (Uint8)*s;
		h *= 16777619u;
	}
	return h;
}

/** How many cubes a cubetxt file holds: the '*' lines that start one, less the closing one. */
static int count_cubes(void)
{
	File file = dataFileOpen(cubeFilename, "rb");
	char buf[256];
	int stars = 0;
	for (; ; )
	{
		readEncryptedString(&file, buf, sizeof(buf));
		if (file.error)
			break;
		if (buf[0] == '*')
			++stars;
	}
	fileClose(&file);
	return stars - 1;
}

int main(int argc, char **argv)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	customDataDirPath = argv[1];

	SDL_Init(0);
	if (!findDataFiles())
		return 1;
	init_video();
	JE_loadMainShapeTables("tyrian.shp");

	for (int episode = 1; episode <= 4; ++episode)
	{
		snprintf(cubeFilename, sizeof cubeFilename, "cubetxt%d.dat", episode);  // JE_initEpisode
		const int count = count_cubes();
		printf("N episode=%d cubes=%d\n", episode, count);

		// One slot, loaded in order, as load_cubes leaves last_line from the slot's previous cube.
		for (int index = 1; index <= count; ++index)
		{
			memset(cube[0].text, 0, sizeof(cube->text));
			load_cube(0, index);

			Uint32 text = 2166136261u;
			for (size_t line = 0; line < COUNTOF(cube->text); ++line)
				text = fnv(fnv(text, cube[0].text[line]), "\n");

			printf("C episode=%d cube=%d face=%d last_line=%d title=%08x header=%08x text=%08x\n",
			       episode, index, cube[0].face_sprite, cube[0].last_line,
			       fnv(2166136261u, cube[0].title), fnv(2166136261u, cube[0].header), text);
		}
	}
	return 0;
}
