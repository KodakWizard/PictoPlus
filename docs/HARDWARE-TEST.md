# Final USA release smoke test

Earlier USA functionality was verified by the owner. Repeat this clean-install checklist for the final release candidate, including the newly licensed loading font; automated reconstruction is not physical hardware verification.

Use a spare/backed-up SD copy. Keep the working SD unchanged. Record hashes/backups of the original save (Checkpoint backup for comparison only), registry, progress files and existing books. No restore/edit is needed.

1. Extract the public desktop ZIP to a fresh writable directory, without the development workspace. Start PictoPlus.exe: the one-time setup page must appear. The package must contain no game resources or `work` directory.
2. Download USA SD Setup from that page. Extract it to the test SD root, leaving exactly one .3gx in `luma/plugins/0004000000187D00/`. Keep the existing books/registry/progress. On this test copy only, ensure no `PictoPlus/base`, `generated-base-USA-v1`, or `Books/.prepared` exists.
3. Launch the installed USA game. Confirm the preparation graphics stay visible, game-file preparation finishes, and first-time setup finishes. Record elapsed times. Confirm `PictoPlus/PictoPlus-Setup.pictosetup` appears (approximately 47 MB). Check existing books/puzzles and reveal rendering.
4. Return the SD to the PC. In the fresh app, Import setup file and select that file. Wait for validation and shape preparation. The editor should open without any other extraction/tool installation. Keep the profile private.
5. Create a NEW book and a NEW design containing blue and yellow blocks. Save/export from the app. Also import a simple self-created 3D model and export a puzzle with its reveal. Copy the exported .pictobook files into `PictoPlus/Books`.
6. Restart the game. Open both new and old books; check thumbnails, covers, numbers, reveal colours and shapes. For paging, export a book with at least 16 puzzles and check both directions, labels and bounds. Solve one new puzzle on Easy and another on Hard.
7. Exit normally and restart. Confirm completion, score, selected difficulty and time persist. Check previous progress has not changed except for intentional gameplay. First-time setup must not repeat after its request is consumed; game/menu preparation should reuse valid local files.
8. Reopen the desktop app: setup must remain ready. Export another book without the profile file or SD attached. Existing books and saves should still work after adding it.

Collect `native-loader-status.txt`, `startup-progress.txt`, `startup-display.txt`, app `data/error.log`/`host.log` if a step fails. Keep the original SD backup. Do not publish the private setup file, generated resource folders, prepared native books or developer workspace. Share the app's normal exported `.pictobook` files only, with permission for their user-supplied models/artwork.

Automated ARM/host-backed filesystem tests do not establish physical FS/GSP timing or rendered appearance. These steps require an actual console. EUR is separate and unmodified.
