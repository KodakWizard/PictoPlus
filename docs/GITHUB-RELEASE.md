# GitHub release draft

## Repository description

Create and share custom Picross 3D: Round 2 puzzle books, with a Windows designer and a USA 3DS loader.

## Topics

pictoplus, picross, picross-3d, puzzle-editor, voxel-editor, nintendo-3ds, homebrew, luma3ds, windows, python

## Release title

PictoPlus 0.8.0 - first public release

## Release notes

PictoPlus is ready for its first public outing. Draw a puzzle with blocks and shapes, collect your designs into books, then play them in Picross 3D: Round 2 on your 3DS.

This release includes the Windows editor, shareable `.pictobook` exports, custom covers and artwork, and the USA loader. 3D model conversion is available as an experimental starting point; it's worth checking the block design before exporting.

### Getting started

Download **PictoPlus-Windows-USA.zip**, extract the whole folder and open **PictoPlus.exe**. Follow the welcome screen's **Download USA SD Setup** instructions. The app uses a private setup file prepared from your installed USA game. No ROM dump or manual save editing is required.

For an existing installation, **PictoPlus-USA-SD-Setup.zip** installs or updates the USA loader. Preserve your Books, registry, progress and caches. For first-time desktop resource preparation, use the app's download button, which also requests your private setup file.

The source archive includes the curated source tree, build dependencies and the USA loader source. No game resources, user books or setup profiles are included.

### Before installing

- The desktop app targets Windows 10 22H2 / Windows 11 x64.
- This package is for the supported USA game. EUR is separate.
- The loader supports 210 puzzles per book and 71 persistent custom-book identities.
- Back up your SD card. Keep only one plugin for the USA title.
- The Windows executables are unsigned. See the checksums and security notes; don't disable antivirus protection.

Automated checks cover clean setup, export, native reconstruction, caching and progress preservation. Players have also tested the USA workflow on physical hardware. This is not a claim that every console, game update, model or library has been tested. The final release font-atlas change still needs an on-console visual confirmation.

Thank you to everyone who has helped test and refine it. If something goes wrong, a clear set of steps and a redacted log will help us fix it.

PictoPlus is unofficial and is not affiliated with or endorsed by Nintendo.

## Maintainer checklist before publishing

- Confirm repository URL, copyright attribution and release date.
- Review docs/RELEASE-AUDIT.md and any outstanding manual-review items.
- Confirm screenshots contain only project-owned sample designs.
- Perform the final on-console font/loader smoke test.
- Publish the curated source tree, never the private workspace.
- Attach the Windows ZIP, USA loader ZIP, source ZIP and SHA256SUMS.txt.
- Keep dependency licences and corresponding modified MPL source available with the release.
- Don't reuse an old antivirus result as proof that a new release is safe.


## Optional Animals puzzle pack

Attach PictoPlus-Animals-Puzzle-Pack.zip as a separate release download. It contains the owner's unchanged Animals.pictobook (15 puzzles), model credits, licence/source links and installation instructions. Extract it and copy Animals.pictobook to PictoPlus/Books/ on the SD card. Keep CREDITS.md with redistributions. The model-derived content retains its CC BY 3.0 attribution requirements; it is separate from the app code's MIT licence.
