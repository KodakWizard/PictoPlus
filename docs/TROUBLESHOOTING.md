# Troubleshooting

## The app won't open

Extract the entire ZIP and keep its folders together. Use a writable folder rather than opening the executable from inside the ZIP. If WebView2 is missing, allow PictoPlus to open the official Microsoft installer. It needs an internet connection.

## Antivirus warns about PictoPlus

The Windows executables are currently unsigned. Earlier builds triggered generic antivirus detections; the reviewed launcher later received two detections on VirusTotal. That is neither proof of malware nor proof of safety. See [security notes](SECURITY-REVIEW.md) for the exact reviewed hash and what was checked.

Do not disable antivirus protection. Verify the release checksum and report a detection with the executable hash and vendor name. A new binary or release needs its own scan; the previous result does not clear it automatically.

## The game doesn't show PictoPlus or my books

Check the game region, enable Luma's plugin loader, and confirm that exactly one plugin is in `luma/plugins/0004000000187D00/`. Books belong in `SD:/PictoPlus/Books/`, not inside a nested ZIP. Restart the game after adding files.

For Azahar, check its configured virtual SD root and 3GX support. See [installation](INSTALLATION.md).

## First-time setup fails

Wait for the current preparation stage to finish. Then check `PictoPlus/native-loader-status.txt`, `startup-progress.txt` and `startup-display.txt` if present. Keep your registry and progress files. Don't restore a save or delete everything as a first troubleshooting step.

The import file is `PictoPlus/PictoPlus-Setup.pictosetup`. Don't share it in a public issue. A truncated or mismatched setup file should be rejected rather than replacing a working configuration.

## A book takes time to import

New or revised books need local preparation. Large model files take more work than simple block designs. The loader reports per-book preparation milliseconds and asset counts in `native-loader-status.txt`. Unchanged books should use the cache; a cached launch is not an import-speed test.

If every launch prepares the same book again, include the relevant log and say whether the file changed. Avoid duplicate files with the same book identity.

## A model or preview looks wrong

3D conversion is experimental. Thin details and complex shapes can be lost at the game's puzzle resolution. Compare the source model, block design and puzzle preview, then adjust the result. Attaching a model for the reveal does not make the block conversion identical to the source.

## Reporting a crash or lost progress

Stop replacing files and make a backup of the SD contents. Note the app/loader version, region, console or emulator, and exact steps. Logs can help, but remove personal paths and other private data before posting. Do not attach ROMs, extracted resources, setup files or saves publicly.
