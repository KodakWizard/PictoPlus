# USA and EUR hardware smoke test

Earlier USA functionality was verified by the owner. Run this clean-install checklist separately for USA and EUR. Physical EUR verification is pending.

Use a spare/backed-up SD copy. Keep the working SD unchanged. Record hashes/backups of the original save (Checkpoint backup for comparison only), registry, progress files and existing books. No restore/edit is needed.

1. Extract the public desktop ZIP to a fresh writable directory, without the development workspace. Start PictoPlus.exe: the one-time setup page must appear. The package must contain no game resources or `work` directory.
2. Download SD Loader from that page. Extract it to the test SD root. Keep one .3gx under each title folder, `0004000000187D00` for USA and `0004000000187E00` for EUR. Keep existing books and progress. Use a fresh test SD copy for the clean-generation check.
3. Launch the installed game for the region under test. Confirm the preparation graphics stay visible, game-file preparation finishes, and first-time setup finishes. Record elapsed times. Confirm `PictoPlus/PictoPlus-Setup.pictosetup` appears (approximately 47 MB). Check existing books/puzzles and reveal rendering.
4. Return the SD to the PC. In the fresh app, Import setup file and select that file. Wait for validation and shape preparation. The editor should open without any other extraction/tool installation. Keep the profile private.
5. Create a NEW book and a NEW design containing blue and yellow blocks. Save/export from the app. Also import a simple self-created 3D model and export a puzzle with its reveal. Copy the exported .pictobook files into `PictoPlus/Books`.
6. Restart the game. Open both new and old books; check thumbnails, covers, numbers, reveal colours and shapes. For paging, export a book with at least 16 puzzles and check both directions, labels and bounds. Solve one new puzzle on Easy and another on Hard.
7. Exit normally and restart. Confirm completion, score, selected difficulty and time persist. Check previous progress has not changed except for intentional gameplay. First-time setup must not repeat after its request is consumed; game/menu preparation should reuse valid local files.
8. Reopen the desktop app: setup must remain ready. Export another book without the profile file or SD attached. Existing books and saves should still work after adding it.

Collect `native-loader-status.txt`, `startup-progress.txt`, `startup-display.txt`, app `data/error.log`/`host.log` if a step fails. Keep the original SD backup. Do not publish the private setup file, generated resource folders, prepared native books or developer workspace. Share the app's normal exported `.pictobook` files only, with permission for their user-supplied models/artwork.

On a card used for both regions, boot the other title with the same books and setup profile. Confirm it uses its own progress. EUR logs and state are under `PictoPlus/EUR/`, while USA retains its existing locations.

ARM and emulator checks cover the loader and content path. Repeat the visual and touch checks above on a physical 3DS.
