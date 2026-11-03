# Release security review

The reviewed launcher SHA-256 is:

```text
d11d0843153e9e4e15bbdee26b4b2cd88cb693e89cef61d8d2a5e6298d95d501
```

Its historical [VirusTotal report](https://www.virustotal.com/gui/file/d11d0843153e9e4e15bbdee26b4b2cd88cb693e89cef61d8d2a5e6298d95d501/detection) showed two detections: McAfee Scanner's generic Ti!D11D0843153E and SecureAge's Malicious. This records the previous investigation, not a newly obtained scan or vendor clearance.

The original small launcher was compared with a source rebuild. It was a normal .NET launcher with an embedded icon, not a packed or obfuscated application. After normalising build metadata, the original matched the source rebuild. Its small size was explained by launching the separate desktop host and bundled Python backend. Generic heuristics and unsigned executable metadata were the strongest supported false-positive explanation; no vendor-confirmed cause was obtained.

The existing build uses pinned dependencies, deterministic .NET compilation and explicit packaging allowlists. The official Microsoft installer is checked against its pinned hash before launch. The backend binds to loopback and uses a per-run token, origin checks and anti-framing headers. Setup/book parsing checks paths, sizes, ranges and checksums. Import staging avoids replacing working data with incomplete output. These measures do not prove the absence of every vulnerability.

This release preparation does not modify the Windows launcher merely to change detection counts. Its icon and source remain consistent with the reviewed binary. Recheck the final hash before relying on that identity. The ZIP, native loader and other executables have their own hashes; results for one file do not clear another.

For vendor review, submit only the public executable, its SHA-256, the public source/build instructions and a short explanation of the local launcher/server workflow. Never submit a private setup profile, user library, save or game dump. No vendor submission or public upload has been performed automatically.

The app is unsigned. Code signing is a separate release decision; there is no signing certificate in the source tree. Follow SECURITY.md for private reporting.
