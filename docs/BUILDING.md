# Building PictoPlus

Use the curated source archive. The private development workspace is not a source release and contains game files that must not be published.

## Desktop release

On Windows 10/11 x64 with Python 3.11+ and .NET Framework 4.x:

```powershell
python tools/package_public_app.py
```

The curated archive includes the hash-pinned Roslyn build files, WebView2 SDK libraries, SPICA source, three.js runtime modules, official embedded Python archive and official WebView2 bootstrapper. These are redistributable build/runtime dependencies, not private game templates. The package script verifies them before compiling. It writes both download ZIPs into build/public-release.

To run from source after building, extract the resulting Windows ZIP and run PictoPlus.exe. Setup still requires the private file generated from your own installed USA or EUR game. No prepared profile or extracted resource is included in the checkout.

## USA and EUR loader

Install devkitARM and libctru from devkitPro and set DEVKITPRO to the SDK directory, then run:

```powershell
python tools/build_public_loader.py
```

The tested toolchain is devkitARM GCC 16.1.0 with the locally pinned libctru headers/library. Different SDK versions may produce different binaries and require testing. Both targets use native/usa and native/vendor directly. The game_region.h header selects the revision-specific hooks and state paths. The build writes the combined loader archive under app/distribution. It does not read a ROM, extracted game code, generated base folder or private build tree. The native source snapshot includes the complete combined runtime source and generated compatibility headers. Edit those source files for public loader changes; the older private development generators are not required.

Re-run the desktop package step after rebuilding the loader. The release ZIPs include notices and the complete modified MPL startup source. The loader's font atlas can be regenerated with tools/build_picto_loading_assets.ps1 using the included Noto Sans Bold font; copy the resulting headers into native/usa when changing it and test the graphics.

## Checks

```powershell
python tools/audit_public_release.py
python tools/test_native_model_import.py build/public-release/host/modeltool
node --test app/designer-orbit.test.mjs app/editor-model.test.mjs app/model-positioning.test.mjs app/placement.test.mjs app/puzzle-numbers.test.mjs app/setup-import.test.mjs app/startup.test.mjs
```

The public audit checks package contents, hashes, licences, documentation links and icon frames. Resource-dependent end-to-end and ARM game-code tests use private local fixtures and are not falsely presented as runnable without them. Their recorded results and the physical verification limits are in docs/RELEASE-AUDIT.md. New contributors can run end-to-end export tests after legitimately preparing their own local setup, but must not commit those resources.

Use current official [devkitPro installation instructions](https://devkitpro.org/wiki/Getting_Started). SPICA source pin: bd29a7828595d7839cda2ac61c76bb63f9071250. No toolchain, ROM or game asset should be downloaded from an untrusted mirror to reproduce a build.
