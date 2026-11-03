# Asset and dependency notices

The project's MIT licence applies to eligible original PictoPlus code and documentation. It does not replace third-party licences or grant rights to Nintendo resources. AI-generated artwork is supplied to the extent the project has rights to do so; no exclusive copyright or legal clearance is claimed.

| Material | Origin and licence | Release handling |
|---|---|---|
| PictoPlus code and documentation | PictoPlus contributors, MIT | LICENSE included |
| Cube mascot, ICO and PNG sizes | User-supplied ChatGPT-generated artwork | Same mascot across app, window and documentation; no Nintendo image used |
| Ten built-in modernist covers | Project image-generation assets; prompts retained | Original project artwork; redistribution under the project's grant to the extent rights are held |
| UI icons | Project inline SVG/text controls | Original code; no external icon font |
| Desktop typography | System font stack | No Windows font file distributed |
| Loader glyph atlas | Noto Sans Bold, SIL OFL 1.1 | Font, licence and generation source in source archive; atlas and licence in loader distribution |
| three.js 0.180.0 | MIT, three.js contributors | Transitive runtime files and licence retained |
| SPICA | Unlicense, gdkchan and contributors | Source pin and declaration-order compatibility patch supplied |
| Python 3.14.10 embedded x64 | PSF and bundled library notices | Official runtime and its complete licence file retained |
| WebView2 SDK / bootstrapper | Microsoft redistribution terms | Official SDK libraries and signed bootstrapper; licence retained |
| Roslyn 4.8.0 build tools | MIT and package notices | Build dependency only; pinned files in curated source archive |
| libctru | zlib-style licence | Notice retained; external devkitPro build dependency |
| newlib and GCC runtime | Component notices and GCC runtime exception | Notices retained; source/toolchain references documented |
| Modified ArticBase startup | MPL 2.0 | Complete modified file supplied with licence; not relicensed MIT |
| csvc.s / csvc.h | Original permissive three-clause notice in files | Notices preserved |
| ArticBase linker script | ArticBase MIT | Upstream notice retained |
| Game-specific layout recipe and patch metadata | Project-generated compatibility edits | Contains format fields, patch instructions, resource names and checksums; requires manual legal review, not a legal clearance |

The public ZIP is not a blanket MIT relicensing of its contents. Licence copies are in LICENSES in binary downloads and in the source archive. The Noto font provenance and exact file hashes are in tools/branding/fonts/provenance.json.

Primary references: [Mozilla's MPL guidance](https://www.mozilla.org/en-US/MPL/2.0/FAQ/), [Microsoft's font redistribution guidance](https://learn.microsoft.com/en-us/typography/fonts/font-faq), and the licence texts supplied with each dependency. The loader atlas uses an openly licensed font rather than relying on Windows-font conversion rights.
