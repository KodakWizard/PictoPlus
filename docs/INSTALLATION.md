# Installing PictoPlus

## Windows app

Extract all of `PictoPlus-Windows-USA.zip` into a writable folder. Keep its folders together and run `PictoPlus.exe`; moving the executable out of that folder will prevent it finding its included runtime.

The app needs Windows 10 22H2 or Windows 11 x64, .NET Framework 4.x and Microsoft WebView2. The supported Windows installations normally include .NET Framework. Python and compiler helpers are bundled. The optional Microsoft WebView2 installer needs internet; puzzle editing otherwise runs locally.

## USA 3DS setup

1. In the welcome screen, choose **Download USA SD Setup**. Use the app button for first-time setup: it also requests the private setup file. The separate release SD ZIP installs or updates the loader only.
2. Extract it onto the SD card root. The plugin belongs at `luma/plugins/0004000000187D00/PictoPlus.3gx`. Keep only one plugin for this title. Enable Luma's plugin loader.
3. Launch the installed USA game. First-time preparation reads the required resources locally from that game.
4. When preparation finishes, return the card to your PC. Import `PictoPlus/PictoPlus-Setup.pictosetup` in the desktop app. Older `.pictoauthoring` setup files are still accepted.

Keep the setup file private. It contains local game resources, not a book to share. No ROM dump or external save editing is needed for this workflow.

## Books and updates

Export selected books from Book Library, then copy the `.pictobook` files into `SD:/PictoPlus/Books/`. Extract a multi-book ZIP first. Keep one current file per book identity; don't leave two conflicting revisions in that folder.

To update the loader, extract the newer USA setup over the existing SD contents. Preserve the Books folder, registry, progress and caches. There is no need to delete them or repeat a completed desktop setup. A new or revised book is prepared on the next game launch; an unchanged library stays cached.

Back up your SD card before updating. Books support 210 puzzles each. The loader reserves up to 71 persistent book identities, retaining progress when books are removed. That is a persistent-slot limit, not a promise of unlimited new books after deleting old ones.

## Azahar

Use a compatible Azahar build with 3GX plugin support and your own legitimate USA game. Install the matching plugin under the emulator's SD root at `luma/plugins/0004000000187D00/PictoPlus.3gx`, enable plugin support, and put books in `PictoPlus/Books/` on that same virtual SD card.

The desktop first-time setup instructions describe the physical 3DS route. Existing Azahar loading, solving and persistence have been tested during development, but every emulator version and first-time setup combination has not been verified. The virtual SD root depends on your emulator configuration; do not copy books into an unrelated ROM folder.

## Regions

The public download targets the tested USA game. EUR development is separate; no EUR or Japanese compatibility is implied by this package. Don't use the USA plugin for another region or assume every game update has the same executable layout.
