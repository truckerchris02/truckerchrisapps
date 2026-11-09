#!/usr/bin/env python3
"""Build an unsigned Store Finder 1.2.0 APK.

Package stays com.truckerchris.storefinder. versionCode is 11 (1.1.8 was 10)
and versionName is 1.2.0. The launcher icon is the v1.1.8 ic_launcher.png.

This script does not create a keystore and does not sign the APK.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
WWW = ROOT / "www"
DIST = ROOT / "dist"
TOOLS = Path(os.environ.get("STOREFINDER_TOOLS", ROOT / ".toolcache"))
VER_CODE = 11
VER_NAME = "1.2.0"
# Fixed DOS timestamp so the unsigned APK does not carry an invalid 1980-00-00 date.
DOS_TIME = (12 << 11) | (0 << 5) | 0
DOS_DATE = ((2026 - 1980) << 9) | (11 << 5) | 9
AAPT2 = Path(os.environ.get("AAPT2", ""))
ANDROID_JAR = Path(os.environ.get("ANDROID_JAR", TOOLS / "android.jar"))
DOWNLOADS = {
    "android.jar": "https://raw.githubusercontent.com/Sable/android-platforms/master/android-34/android.jar",
    "r8.jar": "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.7.18/r8-8.7.18.jar",
}
BUILD_TOOLS_ZIP = "https://dl.google.com/android/repository/build-tools_r34-linux.zip"


def need_tools() -> Path:
    TOOLS.mkdir(parents=True, exist_ok=True)
    for name, url in DOWNLOADS.items():
        dest = TOOLS / name
        if not dest.exists() or dest.stat().st_size < 1000:
            print("downloading", name)
            urllib.request.urlretrieve(url, dest)
    aapt2 = AAPT2 if AAPT2 and AAPT2.exists() else TOOLS / "android-14" / "aapt2"
    if not aapt2.exists():
        zpath = TOOLS / "build-tools.zip"
        if not zpath.exists() or zpath.stat().st_size < 1000:
            print("downloading build-tools")
            urllib.request.urlretrieve(BUILD_TOOLS_ZIP, zpath)
        subprocess.check_call(["unzip", "-q", "-o", str(zpath), "-d", str(TOOLS)])
        found = list(TOOLS.glob("*/aapt2"))
        if not found:
            raise SystemExit("aapt2 was not in the build-tools zip")
        aapt2 = found[0]
    return aapt2


def write_apk(path: Path, items) -> None:
    """items: (name, data, method). method 0 stored, 8 deflated. Stored entries are 4-byte aligned."""
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = bytearray()
    central = []
    for name, data, method in items:
        name_b = name.encode("utf-8")
        crc = zlib.crc32(data) & 0xFFFFFFFF
        extra = b""
        if method == 0:
            comp = data
            header_len = 30 + len(name_b)
            pad = (4 - ((len(blob) + header_len) % 4)) % 4
            extra = b"\x00" * pad
        elif method == 8:
            comp = zlib.compress(data, 9)[2:-4]
        else:
            raise SystemExit("bad method %s" % method)
        local_off = len(blob)
        blob += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, method, DOS_TIME, DOS_DATE, crc, len(comp), len(data), len(name_b), len(extra))
        blob += name_b + extra + comp
        central.append((name_b, method, crc, len(comp), len(data), extra, local_off))
    cd_off = len(blob)
    for name_b, method, crc, csz, usz, extra, local_off in central:
        blob += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, method, DOS_TIME, DOS_DATE, crc, csz, usz, len(name_b), len(extra), 0, 0, 0, 0, local_off)
        blob += name_b + extra
    cd_size = len(blob) - cd_off
    blob += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(central), len(central), cd_size, cd_off, 0)
    path.write_bytes(blob)


def build() -> Path:
    aapt2 = need_tools()
    missing = [name for name in ("index.html", "app.js", "stores.js", "us-stores.js", "dcs.js") if not (WWW / name).exists()]
    if missing:
        raise SystemExit("missing web files (run data/build_dataset.py first): " + ", ".join(missing))
    with tempfile.TemporaryDirectory(prefix="storefinder-apk-") as tmp:
        td = Path(tmp)
        compiled = td / "compiled.zip"
        linked = td / "linked.apk"
        gen = td / "gen"
        gen.mkdir()
        subprocess.check_call([str(aapt2), "compile", "--dir", str(ANDROID / "res"), "-o", str(compiled)])
        subprocess.check_call([
            str(aapt2), "link", "-o", str(linked),
            "--manifest", str(ANDROID / "AndroidManifest.xml"),
            "-I", str(ANDROID_JAR),
            "--java", str(gen),
            "--min-sdk-version", "29",
            "--target-sdk-version", "34",
            str(compiled),
        ])
        classes = td / "classes"
        classes.mkdir()
        sources = [str(p) for p in gen.rglob("*.java")]
        sources.append(str(ANDROID / "src/com/truckerchris/storefinder/MainActivity.java"))
        subprocess.check_call([
            "javac", "-encoding", "UTF-8", "-source", "8", "-target", "8",
            "-classpath", str(ANDROID_JAR), "-d", str(classes), *sources,
        ])
        class_files = [str(p) for p in classes.rglob("*.class")]
        if not class_files:
            raise SystemExit("javac produced no classes")
        dex_dir = td / "dex"
        dex_dir.mkdir()
        subprocess.check_call([
            "java", "-cp", str(TOOLS / "r8.jar"), "com.android.tools.r8.D8",
            "--release", "--min-api", "29",
            "--lib", str(ANDROID_JAR),
            "--output", str(dex_dir),
            *class_files,
        ])
        dex = (dex_dir / "classes.dex").read_bytes()
        if b"file:///android_asset/www/index.html" not in dex:
            raise SystemExit("dex is missing the start url")
        if b"Lcom/truckerchris/storefinder/MainActivity;" not in dex:
            raise SystemExit("dex is missing MainActivity")
        packed = zipfile.ZipFile(linked)
        manifest = packed.read("AndroidManifest.xml")
        arsc = packed.read("resources.arsc")
        resources = [(info.filename, packed.read(info.filename)) for info in packed.infolist() if info.filename.startswith("res/")]
        items = [
            ("AndroidManifest.xml", manifest, zipfile.ZIP_STORED),
            ("classes.dex", dex, zipfile.ZIP_STORED),
            ("resources.arsc", arsc, zipfile.ZIP_STORED),
        ]
        for name, data in resources:
            method = zipfile.ZIP_STORED if name.endswith(".png") else zipfile.ZIP_DEFLATED
            items.append((name, data, method))
        for path in sorted(WWW.iterdir()):
            if path.is_file():
                items.append(("assets/www/" + path.name, path.read_bytes(), zipfile.ZIP_DEFLATED))
        out = DIST / "StoreFinder-v1.2.0-unsigned.apk"
        write_apk(out, items)
    verify(out)
    print(out)
    return out


def verify(path: Path) -> None:
    blob = path.read_bytes()
    zf = zipfile.ZipFile(path)
    names = zf.namelist()
    if any(name.startswith("META-INF/") for name in names):
        raise SystemExit("unsigned apk still has META-INF")
    for required in (
        "AndroidManifest.xml", "classes.dex", "resources.arsc", "res/drawable/ic_launcher.png",
        "assets/www/index.html", "assets/www/app.js", "assets/www/stores.js",
        "assets/www/us-stores.js", "assets/www/dcs.js",
    ):
        if required not in names:
            raise SystemExit("missing " + required)
    info = zf.getinfo("resources.arsc")
    if info.compress_type != 0:
        raise SystemExit("resources.arsc is compressed")
    off = info.header_offset
    name_len, extra_len = struct.unpack_from("<HH", blob, off + 26)
    data_off = off + 30 + name_len + extra_len
    if data_off % 4 != 0:
        raise SystemExit("resources.arsc is not 4-byte aligned (%s)" % data_off)
    man = zf.read("AndroidManifest.xml")
    if VER_NAME.encode("utf-16le") not in man:
        raise SystemExit("manifest missing versionName")
    if "1.1.8".encode("utf-16le") in man:
        raise SystemExit("manifest still says 1.1.8")
    if "com.truckerchris.storefinder".encode("utf-16le") not in man:
        raise SystemExit("manifest missing package")
    if "android.permission.INTERNET".encode("utf-16le") not in man:
        raise SystemExit("manifest missing INTERNET")
    found = None
    # The file is one XML chunk. Walk the chunks inside it; the manifest
    # element's first integer attribute is versionCode.
    pos = 8
    while pos + 8 <= len(man):
        typ, hs, size = struct.unpack_from("<HHI", man, pos)
        if size < 8 or pos + size > len(man):
            break
        if typ == 0x0102 and hs >= 16:
            attr_start, _attr_size, attr_count = struct.unpack_from("<HHH", man, pos + 24)
            base = pos + 16 + attr_start
            for index in range(attr_count):
                if base + (index + 1) * 20 > len(man):
                    break
                _ns, _name, _raw, typed, vdata = struct.unpack_from("<IIIII", man, base + index * 20)
                if ((typed >> 24) & 0xFF) == 0x10:
                    found = vdata
                    break
            if found is not None:
                break
        pos += size
    if found != VER_CODE:
        raise SystemExit("manifest versionCode is %s, expected %s" % (found, VER_CODE))
    page = zf.read("assets/www/index.html")
    if b"Version 1.2.0" not in page or b"wsf_custom" not in zf.read("assets/www/app.js"):
        raise SystemExit("packaged page lost 1.2.0 or the v1.1.8 storage keys")
    icon = zf.read("res/drawable/ic_launcher.png")
    original = (ANDROID / "res/drawable/ic_launcher.png").read_bytes()
    if icon != original:
        # aapt may store the same bytes under that path; if it rewrote them, the source file is still the artwork.
        if not icon.startswith(b"\x89PNG"):
            raise SystemExit("launcher icon is not a png")
    print("verified", path, "bytes", path.stat().st_size)


if __name__ == "__main__":
    build()
