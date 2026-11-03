# Public source provenance

native/usa is the complete combined USA runtime source snapshot used for this release. It preserves the working code and is the source of truth for the public build; the private prototype generator chain is not required. The generated manifests contain names, sizes and checksums, not game files. The layout and paging headers contain compatibility recipes/instructions whose redistribution assessment is documented in docs/RELEASE-AUDIT.md.

startup.s is derived from ArticBaseServer's startup under MPL 2.0, as its header states. native/vendor/csvc.s and csvc.h retain their permissive notices; 3gx.ld is from ArticBase and its MIT notice is adjacent. Noto glyph and mascot headers are generated from the included project/openly licensed assets. Other eligible PictoPlus source is MIT.

The public and established development builders produced the same plugin bytes with the tested devkitARM toolchain. Rebuilding with another SDK version needs its own regression/hardware checks.
