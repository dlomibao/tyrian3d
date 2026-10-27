# Data parsers

Parsers for the Tyrian 2.1 data files, ported from [OpenTyrian](https://github.com/opentyrian/opentyrian).
They're pure functions over `ArrayBuffer`/`Uint8Array`, so they run in the browser; fetching the
files is up to the caller.

Values keep the original's raw units: pixels, logic frames, 6-bit VGA palette components.
Nothing is rescaled here, so a 60 Hz logic mode or a high-resolution renderer converts
explicitly where it needs to.

| File | Parser | Ported from |
| --- | --- | --- |
| `palette.dat` | `parsePalettes` (`palette.ts`) | `loadPals`, `src/palette.c` |
| `tyrian.hdt` (item data block) | `loadItemDat`, `parseItemDat` (`items.ts`) | `JE_loadItemDat`, `src/episodes.c` |
| enemy table (same block) | `readEnemyDat` (`enemies.ts`) | `JE_loadItemDat`, `src/episodes.c` |
| `tyrian1.lvl`..`tyrian4.lvl` | `parseLevelFile`, `parseLevel`, `readLevelPositions` (`levels.ts`) | `analyzeLevel`, `src/lvllib.c`; `JE_loadMap`, `src/tyrian2.c` |
| `shapes).dat`, `shapesw.dat`..`shapesz.dat` (map tiles) | `parseShapes`, `levelTiles` (`levels.ts`) | `JE_loadMap`, `src/tyrian2.c` |
| `levels1.dat`..`levels4.dat` (episode scripts) | `parseEpisodeScript`, `episodeLevels`, `parsePlayLevel` (`episodeScript.ts`) | `JE_loadMap`, `src/tyrian2.c` |
| encrypted strings | `decryptString`, `readEncryptedString` (`crypt.ts`) | `decrypt_string`, `readEncryptedString`, `src/helptext.c` |
| `tyrian.pic`, `tshp2.pcx` (full-screen pictures) | `decodePicture`, `decodePcxFile` (`pictures.ts`) | `JE_loadPic`, `src/picload.c`; `JE_loadPCX`, `src/pcxload.c` |

Episode 4 keeps its item and enemy data at the end of `tyrian4.lvl` instead of `tyrian.hdt`;
`loadItemDat(4, hdt, lvl)` handles that the way `JE_loadItemDat` does.

Not ported yet: the help and menu text in `tyrian.hdt` (`JE_loadHelpText`), `tyrian.cdt`,
`cubetxt*.dat`, and sprite (`*.shp`), sound and music files.

Tests in `tests/data/` read the files from `$TYRIAN_DATA` (default `data/`) and skip when
they're missing:

    TYRIAN_DATA=/path/to/tyrian21 npm test
