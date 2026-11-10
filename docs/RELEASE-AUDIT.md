# Release audit - 3 November 2026

This is a technical provenance and packaging review, not legal clearance.

## Scope and history

The development workspace contains ROM/CCI/CIA files, extracted RomFS/code, private setup resources, native templates, user books, saves, logs, reference screenshots, emulator installations and old test builds. None belongs in a public repository. The public source archive is assembled by an explicit allowlist into a new directory, without deleting or moving private content.

There is no top-level project Git repository in the supplied workspace or its parents. No project commit history was available to inspect. The curated archive contains no .git directories. No history was deleted or rewritten. If an existing remote repository is used, its full history still needs a separate object/content audit before publication; checking this archive does not certify an unseen remote history. A new repository should start from the curated tree, not this workspace.

## Distribution findings

- Desktop runtime resources come from the user's installed game through the private PictoPlus-Setup.pictosetup file. Clean-package tests verify no private developer fallback is needed.
- Public book exports use changed-byte recipes. No game models, textures, original books/puzzles, game text archives, ROMs or prepared setup profiles are in the curated packages.
- The USA and EUR source snapshot contains the complete runtime code plus game-specific identifiers, resource filenames, CRC/SHA manifests, patch instructions and layout edit metadata. The layout recipe has 7,427 literal bytes, with original arrow imagery read from the installed game rather than embedded. These reverse-engineering/compatibility edits remain a manual legal-review item; this audit does not establish that every instruction or metadata fragment is legally cleared in every jurisdiction.
- The previous loader font atlas came from rasterised Segoe UI glyphs. It was replaced with Noto Sans Bold under SIL OFL 1.1, with font, licence, hashes and generation source supplied. Desktop fonts remain system fonts; no Windows font file is bundled.
- The current cube mascot is confirmed by the owner as ChatGPT-generated. The ten built-in covers are project image-generation assets with retained prompts. Rights are granted only to the extent held; AI provenance does not establish exclusive copyright or guarantee clearance.
- Original PictoPlus code is MIT by the owner's explicit approval. Dependency licences remain separate. The modified ArticBase startup remains MPL 2.0, with complete modified source and notice; csvc files keep their original permissive notice.
- Unused visual-preview experiment files are excluded from public packages, while private originals are preserved. Old launchers, model test executables, emulator files and experimental assets are not distributed.
- No absolute private development paths, setup files, private keys or obvious token patterns were found by the current allowlist/content checks. This is a focused scan, not a guarantee against every possible secret format.

## Reproducibility and verification

The new public loader build uses native/usa and native/vendor plus an external devkitARM/libctru SDK. It does not require a ROM, extracted code, private base folder or the private prototype build chain. With the tested SDK, it produces a byte-identical plugin to the established builder using the same updated sources. The release source archive includes the public build script, pinned desktop dependencies, SPICA source and all required notices.

Current release-preparation reruns passed 98 app tests, seven JavaScript suites, clean first-time setup and export tests, actual ARM reconstruction of a 210-puzzle book, cached restart/repair, malformed recipe rejection and progress-preservation tests. Tests that execute original game instructions use private local fixtures; those fixtures are not included or falsely described as available from a clean public checkout. Public source checks cover build reproducibility, package integrity, documentation/icon consistency and the asset-independent JavaScript suites. A clean curated source tree built the desktop package successfully and reproduced the reviewed launcher hash and the new native plugin byte-for-byte. Three focused release checks also passed, including rejection of private/nested assets and valid branding text encoding.

The user confirmed physical USA setup, puzzle solving, saved progress, paging, artwork, front-facing reveals and the buffered import optimization during development. Not every console, game update or model was tested. The final Noto font atlas is visually checked in the real ARM renderer with host GPU stubs, not yet on physical hardware. USA and EUR startup and save-folder creation passed in Azahar. A full interactive EUR run on a physical console remains open.

The desktop launcher remains unsigned. Its historical two-detection VirusTotal result and investigated hash are documented in SECURITY-REVIEW.md. No fresh antivirus scan or vendor clearance is claimed for the archive or native loader. No arbitrary anti-detection changes were made.

## Release contents

- PictoPlus-Windows.zip: launcher and desktop host, app code/assets, required runtime libraries, embedded Python, compiler helpers, WebView2 bootstrapper, combined USA and EUR loader download, documentation, notices and corresponding modified startup/font generation source. No user data or game resources.
- PictoPlus-SD-Loader.zip: both plugins, empty Books directory, optional setup markers, instructions and licence/source notices. The installed game generates a profile when one is missing.
- PictoPlus-Source.zip: curated app/compiler source, native USA and EUR source snapshot, build scripts, pinned redistributable build dependencies, original artwork, documentation, tests and notices. No project Git history or private fixtures.
- SHA256SUMS.txt: hashes of the three release archives.

## Decisions and remaining approvals

MIT and ChatGPT mascot provenance have been confirmed. The audited packages target the public PictoPlus repository. Compatibility patch metadata remains subject to the review notes above. Physical EUR gameplay and the updated font on console remain open.
