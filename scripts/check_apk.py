#!/usr/bin/env python3
"""Fail if a built Android APK lacks an ARM64 native emulator library."""
import hashlib
import pathlib
import sys
import zipfile

def check(apk_name: str):
    path = pathlib.Path(apk_name)
    if not path.is_file() or path.suffix.lower() != ".apk":
        raise RuntimeError(f"APK not found: {path}")
    if path.stat().st_size < 1024 * 1024:
        raise RuntimeError("APK is unexpectedly small")
    with zipfile.ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise RuntimeError(f"Corrupt APK entry: {corrupt}")
        names = set(archive.namelist())
        if not {"AndroidManifest.xml", "classes.dex"} <= names:
            raise RuntimeError("Missing Android manifest or DEX")
        native = sorted(n for n in names if n.startswith("lib/arm64-v8a/") and n.endswith(".so"))
        if not native:
            raise RuntimeError("Missing arm64-v8a native library")
    with path.open("rb") as f:
        sha256 = hashlib.file_digest(f, "sha256").hexdigest()
    print(f"Verified: {path} | {path.stat().st_size:,} bytes | arm64 libraries: {len(native)}")
    print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: check_apk.py path/to/app.apk")
    for name in sys.argv[1:]:
        check(name)
