# PictoPlus v1.0 - USA & EUR Support

PictoPlus v1.0.0 brings custom puzzle books to the USA and EUR versions of Picross 3D: Round 2. Use your own legally obtained copy of the game.

- One **SD Loader ZIP** installs both region-specific plugins. USA and EUR share the same books and Windows setup profile, with separate progress and caches.
- The Windows editor adds interface scaling, Compact Layout, and textured BCH and BCRES/CGFX imports. Raw Pokémon GFModel and GFTexture import is experimental.
- The optional **Animals Puzzle Pack** contains 15 puzzles and includes model credits and licence details.

## Install or update

1. Extract **PictoPlus-Windows.zip** and open **PictoPlus.exe**. When updating, keep your existing `app/data` folder.
2. Extract **PictoPlus-SD-Loader.zip** to the SD card root. Keep one `.3gx` per title folder. USA uses `0004000000187D00` and EUR uses `0004000000187E00`. Enable Plugin Loader in Luma3DS's Rosalina menu, then launch your game.
3. If you are setting up the editor for the first time, import `PictoPlus/PictoPlus-Setup.pictosetup` from your SD card. Keep the file private. Existing compatible profiles still work.
4. Copy `.pictobook` files to `PictoPlus/Books`. Keep existing registry and progress files. EUR stores its regional data in `PictoPlus/EUR`.

For Azahar, use a build with 3GX plugin support. Enable its plugin loader and extract the same ZIP to its virtual SD root. On Windows, a short path for the portable emulator helps Azahar create its game save folders.

## Verification

USA and EUR loader builds passed ARM tests for 210-puzzle books, paging, slicers, setup and progress. Both games booted with the loader in Azahar. Earlier USA gameplay was tested on physical hardware. **EUR physical 3DS compatibility has not yet been verified.**

The release includes the Windows app, combined SD Loader, Animals pack, curated source and SHA-256 checksums. It contains no Nintendo game files or private setup profiles. The Windows executables are unsigned.
