# Brand assets

Keep the smiling cream cube, orange cheek, brown markings and teal interface accents. The mascot is user-supplied ChatGPT-generated artwork. Use the existing mark rather than a different cube illustration.

app/assets/pictoplus.ico contains the actual executable/window icon frames at 16, 24, 32, 48, 64, 128 and 256 pixels. docs/images/icon-*.png are exact PNG frame extractions from that ICO, not independently resampled variants. tools/branding/export_icons.py reproduces them and checks the PNG dimensions.

The browser favicon uses that same ICO. Windows shortcuts inherit it from the executable; the window loads the same file. The larger original mascot remains in the sidebar and welcome screen. Do not stretch it or place it on a busy background.

Typography in the desktop app uses system fonts. The loader atlas uses the included OFL-licensed Noto Sans Bold. No proprietary font file is redistributed.
