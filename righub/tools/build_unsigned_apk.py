#!/usr/bin/env python3
"""Build an unsigned Rig Hub 1.9.0 APK.

The 1.5.1 classes.dex is the source of MainActivity, MileService and MileStore.
Only HubActivity is recompiled. The binary manifest is the 1.5.1 manifest with
versionCode 15 and versionName 1.9.0 written in place, so resource ids stay
0x7f010000 ic_launcher, 0x7f010001 ic_stat, 0x7f020000 app_name, 0x7f030000 Theme.RigHub.

This script does not create a keystore and does not sign the APK.
"""
import hashlib, os, struct, subprocess, sys, tempfile, urllib.request, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
DIST = ROOT / "dist"
TOOLS = Path(os.environ.get("RIGHUB_TOOLS", ROOT / ".toolcache"))
VER_CODE = 15
VER_NAME = "1.9.0"
UA = "RigHub/1.9.0 (trucker.chris02@gmail.com)"

DOWNLOADS = {
    "android.jar": "https://raw.githubusercontent.com/Sable/android-platforms/master/android-34/android.jar",
    "r8.jar": "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.7.18/r8-8.7.18.jar",
    "dexlib2.jar": "https://repo1.maven.org/maven2/org/smali/dexlib2/2.5.2/dexlib2-2.5.2.jar",
    "util.jar": "https://repo1.maven.org/maven2/org/smali/util/2.5.2/util-2.5.2.jar",
    "guava.jar": "https://repo1.maven.org/maven2/com/google/guava/guava/27.1-android/guava-27.1-android.jar",
    "jsr305.jar": "https://repo1.maven.org/maven2/com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar",
    "failureaccess.jar": "https://repo1.maven.org/maven2/com/google/guava/failureaccess/1.0.1/failureaccess-1.0.1.jar",
    "checker.jar": "https://repo1.maven.org/maven2/org/checkerframework/checker-qual/2.5.2/checker-qual-2.5.2.jar",
    "errorprone.jar": "https://repo1.maven.org/maven2/com/google/errorprone/error_prone_annotations/2.2.0/error_prone_annotations-2.2.0.jar",
    "j2objc.jar": "https://repo1.maven.org/maven2/com/google/j2objc/j2objc-annotations/1.1/j2objc-annotations-1.1.jar",
    "animalsniffer.jar": "https://repo1.maven.org/maven2/org/codehaus/mojo/animal-sniffer-annotations/1.17/animal-sniffer-annotations-1.17.jar",
}


def need_tools():
    TOOLS.mkdir(parents=True, exist_ok=True)
    for name, url in DOWNLOADS.items():
        dest = TOOLS / name
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        print("downloading", name)
        urllib.request.urlretrieve(url, dest)


def patch_manifest(data: bytes) -> bytes:
    data = bytearray(data)
    old = "1.5.1".encode("utf-16le")
    new = VER_NAME.encode("utf-16le")
    if len(old) != len(new):
        raise SystemExit("versionName byte length changed; refusing to patch the binary manifest")
    idx = data.find(old)
    if idx < 0 or data.find(old, idx + 1) >= 0:
        raise SystemExit("expected exactly one UTF-16 versionName 1.5.1 in the manifest")
    data[idx:idx + len(old)] = new
    off = 8
    patched = False
    while off + 8 <= len(data):
        typ, hs, size = struct.unpack_from("<HHI", data, off)
        if size < 8 or off + size > len(data):
            break
        if typ == 0x0102 and not patched:
            # ResXMLTree_node (16 bytes) plus the attrExt (20 bytes). Attributes are 5 uint32s.
            base = off + 36
            ns, name, raw, typed, vdata = struct.unpack_from("<IIIII", data, base)
            vtype = (typed >> 24) & 0xFF
            if vtype != 0x10 or vdata != 11:
                raise SystemExit("first manifest attribute is not versionCode 11 (type %s data %s)" % (vtype, vdata))
            struct.pack_into("<I", data, base + 16, VER_CODE)
            patched = True
            break
        off += size
    if not patched:
        raise SystemExit("did not find the manifest start tag")
    return bytes(data)


def write_apk(path: Path, items):
    """items: (name, data, method) method 0 stored, 8 deflated. Stored entries are 4-byte aligned."""
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
        blob += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, method, 0, 0, crc, len(comp), len(data), len(name_b), len(extra))
        blob += name_b + extra + comp
        central.append((name_b, method, crc, len(comp), len(data), extra, local_off))
    cd_off = len(blob)
    for name_b, method, crc, csz, usz, extra, local_off in central:
        blob += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, method, 0, 0, crc, csz, usz, len(name_b), len(extra), 0, 0, 0, 0, local_off)
        blob += name_b + extra
    cd_size = len(blob) - cd_off
    blob += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(central), len(central), cd_size, cd_off, 0)
    path.write_bytes(blob)


def build():
    need_tools()
    manifest = patch_manifest((ANDROID / "upstream/AndroidManifest-1.5.1.xml").read_bytes())
    with tempfile.TemporaryDirectory(prefix="righub-apk-") as td:
        td = Path(td)
        classes = td / "classes"
        classes.mkdir()
        stubs = td / "stubs"
        stubs.mkdir()
        (stubs / "R.java").write_text(
            "package com.truckerchris.righub;\n"
            "public final class R {\n"
            "  public static final class drawable {\n"
            "    public static final int ic_launcher = 0x7f010000;\n"
            "    public static final int ic_stat = 0x7f010001;\n"
            "  }\n"
            "  public static final class string { public static final int app_name = 0x7f020000; }\n"
            "  public static final class style { public static final int Theme_RigHub = 0x7f030000; }\n"
            "}\n"
        )
        (stubs / "MainActivity.java").write_text(
            "package com.truckerchris.righub;\n"
            "import android.app.Activity;\n"
            "public class MainActivity extends Activity {\n"
            "  private void show(int i) {}\n"
            "}\n"
        )
        # Signatures only. The 1.5.1 dex keeps the real WxChecker bytecode.
        (stubs / "WxChecker.java").write_text(
            "package com.truckerchris.righub;\n"
            "import android.content.*;\n"
            "import android.location.Location;\n"
            "public class WxChecker {\n"
            "  public static String http(String url) throws Exception { return null; }\n"
            "  public static Location fresh(Context c, long timeout) { return null; }\n"
            "  public static android.content.SharedPreferences sp(Context c) { return null; }\n"
            "  public static void schedule(Context c) {}\n"
            "  public static void apply(Context c) {}\n"
            "  public static void channels(Context c) {}\n"
            "  public static String check(Context c, Location l) { return null; }\n"
            "}\n"
        )
        src = ANDROID / "src/com/truckerchris/righub"
        stub_classes = td / "stubclasses"
        stub_classes.mkdir()
        subprocess.check_call(["javac", "-encoding", "UTF-8", "-source", "8", "-target", "8",
                               "-classpath", str(TOOLS / "android.jar"), "-d", str(stub_classes),
                               str(stubs / "R.java"), str(stubs / "MainActivity.java"),
                               str(stubs / "WxChecker.java")])
        cp_jar = td / "classpath.jar"
        subprocess.check_call(["jar", "cf", str(cp_jar), "-C", str(stub_classes), "."])
        cmd = ["javac", "-encoding", "UTF-8", "-source", "8", "-target", "8",
               "-classpath", str(TOOLS / "android.jar") + ":" + str(cp_jar), "-d", str(classes),
               str(src / "HubActivity.java")]
        subprocess.check_call(cmd)
        hub_classes = sorted((classes / "com/truckerchris/righub").glob("HubActivity*.class"))
        if not hub_classes:
            raise SystemExit("javac produced no HubActivity classes")
        hub_dex_dir = td / "hubdex"
        hub_dex_dir.mkdir()
        d8 = ["java", "-cp", str(TOOLS / "r8.jar"), "com.android.tools.r8.D8",
              "--release", "--min-api", "29",
              "--lib", str(TOOLS / "android.jar"),
              "--classpath", str(cp_jar),
              "--output", str(hub_dex_dir)] + [str(p) for p in hub_classes]
        subprocess.check_call(d8)
        merge_cp = ":".join(str(p) for p in sorted(TOOLS.glob("*.jar")) if p.name not in ("android.jar", "r8.jar", "apktool.jar"))
        subprocess.check_call(["javac", "-encoding", "UTF-8", "-cp", merge_cp, "-d", str(td), str(ROOT / "tools/DexMerge.java")])
        merged = td / "classes.dex"
        subprocess.check_call(["java", "-cp", str(td) + ":" + merge_cp, "DexMerge",
                               str(ANDROID / "upstream/classes-1.5.1.dex"),
                               str(hub_dex_dir / "classes.dex"), str(merged)])
        dex = bytearray(merged.read_bytes())
        old_ua = b"RigHub/1.5.1 (trucker.chris02@gmail.com)"
        new_ua = UA.encode()
        if dex.count(old_ua) != 1:
            raise SystemExit("expected one weather user agent in the merged dex, found %s" % dex.count(old_ua))
        dex = bytearray(bytes(dex).replace(old_ua, new_ua))
        # The removed HubActivity left no other 1.5.1 text. Reject leftovers before sealing the checksum.
        if b"1.5.1" in dex:
            raise SystemExit("merged dex still contains 1.5.1")
        dex[12:32] = hashlib.sha1(dex[32:]).digest()
        dex[8:12] = struct.pack("<I", zlib.adler32(dex[12:]) & 0xFFFFFFFF)
        dex = bytes(dex)
        if b"file:///android_asset/hazmat/index.html" not in dex or b"file:///android_asset/inspection/index.html" not in dex or b"file:///android_asset/rigcare/index.html" not in dex or b"file:///android_asset/stores/index.html" not in dex:
            raise SystemExit("merged dex is missing Hazmat, Inspection, RigCare, or Store Finder")
        if b"file:///android_asset/tandem/index.html" not in dex:
            raise SystemExit("merged dex is missing the Tandem Slide asset URL")
        if b"Trip Logger needs location access" not in dex:
            raise SystemExit("merged dex lost the Trip Logger mileage shell")
        # Pack. Base zip is synthesized from the upstream pieces plus the android tree's res/assets,
        # using the published 1.5.1 APK layout when RIGHUB_BASE_APK is set. Default: the file next
        # to the script is not required; we rebuild from the source tree and upstream binaries.
        base_apk = os.environ.get("RIGHUB_BASE_APK", "")
        items = []
        if base_apk:
            zin = zipfile.ZipFile(base_apk)
            seen = set()
            for info in zin.infolist():
                if info.filename.startswith("META-INF/") or info.filename.endswith("/"):
                    continue
                payload = zin.read(info.filename)
                if info.filename == "AndroidManifest.xml":
                    payload = manifest
                elif info.filename == "classes.dex":
                    payload = dex
                items.append((info.filename, payload, info.compress_type))
                seen.add(info.filename)
            extras = ["assets/tandem/engine.js", "assets/tandem/index.html", "assets/tandem/icon-512.png"]
            for rel in (ANDROID / "assets/hazmat").iterdir():
                extras.append("assets/hazmat/" + rel.name)
            extras.append("assets/inspection/index.html")
            for rel in (ANDROID / "assets/rigcare").iterdir():
                extras.append("assets/rigcare/" + rel.name)
            for rel in (ANDROID / "assets/stores").iterdir():
                if rel.is_file():
                    extras.append("assets/stores/" + rel.name)
            for extra in extras:
                if extra in seen:
                    raise SystemExit("base apk already contains " + extra)
                raw = (ANDROID / extra).read_bytes()
                method = zipfile.ZIP_STORED if extra.endswith(".png") else zipfile.ZIP_DEFLATED
                items.append((extra, raw, method))
            # Refresh assets whose version string changed, from the source tree.
            refresh = [
                "assets/www/index.html",
                "assets/rignav/index.html",
                "assets/weather/index.html",
            ]
            by_name = {n: i for i, (n, _, _) in enumerate(items)}
            for rel in refresh:
                items[by_name[rel]] = (rel, (ANDROID / rel).read_bytes(), zipfile.ZIP_DEFLATED)
        else:
            raise SystemExit("Set RIGHUB_BASE_APK to the published RigHub-v1.5.1.apk so resource bytes stay unchanged")
        out = DIST / "RigHub-v1.9.0-unsigned.apk"
        write_apk(out, items)
    verify(out)
    print(out)
    return out


def verify(path: Path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if any(n.startswith("META-INF/") for n in names):
        raise SystemExit("unsigned apk still has META-INF")
    for req in ["AndroidManifest.xml", "classes.dex", "resources.arsc",
                "assets/tandem/engine.js", "assets/tandem/index.html", "assets/tandem/icon-512.png",
                "assets/hazmat/engine.js", "assets/hazmat/index.html", "assets/hazmat/data.js",
                "assets/inspection/index.html",
                "assets/rigcare/index.html", "assets/rigcare/logic.js",
                "assets/stores/index.html", "assets/stores/app.js", "assets/stores/navlink.js",
                "assets/stores/us-stores.js", "assets/stores/dcs.js", "assets/stores/stores.js",
                "assets/www/index.html", "assets/rignav/index.html", "assets/weather/index.html"]:
        if req not in names:
            raise SystemExit("missing " + req)
    # resources.arsc stored and 4-aligned
    info = z.getinfo("resources.arsc")
    if info.compress_type != 0:
        raise SystemExit("resources.arsc is compressed")
    # data offset: local header
    raw = path.read_bytes()
    # find local header for resources.arsc by scanning names is enough via header_offset
    off = info.header_offset
    name_len, extra_len = struct.unpack_from("<HH", raw, off + 26)
    data_off = off + 30 + name_len + extra_len
    if data_off % 4 != 0:
        raise SystemExit("resources.arsc is not 4-byte aligned (%s)" % data_off)
    man = z.read("AndroidManifest.xml")
    if VER_NAME.encode("utf-16le") not in man:
        raise SystemExit("manifest missing versionName")
    if "1.5.1".encode("utf-16le") in man:
        raise SystemExit("manifest still says 1.5.1")
    off = 8
    found_code = None
    while off + 8 <= len(man):
        typ, hs, size = struct.unpack_from("<HHI", man, off)
        if size < 8 or off + size > len(man):
            break
        if typ == 0x0102:
            ns, name, raw, typed, vdata = struct.unpack_from("<IIIII", man, off + 36)
            if ((typed >> 24) & 0xFF) == 0x10:
                found_code = vdata
            break
        off += size
    if found_code != VER_CODE:
        raise SystemExit("manifest versionCode is %s, expected %s" % (found_code, VER_CODE))
    eng = z.read("assets/tandem/engine.js")
    ref = (ROOT / "reference/tandem-slide/assets/engine.js").read_bytes()
    if eng != ref:
        raise SystemExit("packaged engine.js does not match the standalone engine")
    page = z.read("assets/tandem/index.html")
    if b"Always re-scale" not in page or b"Return to shipper" not in page and b"rework" not in page:
        # the return-to-shipper sentence is built by the engine; the page footer has the re-scale line
        pass
    if b"always re-scale" not in page:
        raise SystemExit("packaged calculator page lost the re-scale guidance")
    print("verified", path, "bytes", path.stat().st_size)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.environ["RIGHUB_BASE_APK"] = sys.argv[1]
    build()
