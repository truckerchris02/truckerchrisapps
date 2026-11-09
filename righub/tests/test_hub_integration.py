#!/usr/bin/env python3
"""Rig Hub keeps its earlier tools and adds Walmart Store Finder wired to Rig Nav."""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HUB = ROOT / "righub"

def fail(msg):
    raise SystemExit(msg)

def read(path):
    return (HUB / path).read_text(encoding="utf-8")

def need(path, *bits):
    text = read(path)
    for bit in bits:
        if bit not in text:
            fail("%s is missing %r" % (path, bit))
    return text

def main():
    manifest = need(
        "android/AndroidManifest.xml",
        'package="com.truckerchris.righub"',
        'android:versionCode="15"',
        'android:versionName="1.9.0"',
        'android:name=".HubActivity"',
        'android:name=".MileService"',
        'android:name=".WxWatchService"',
    )
    if "tandemslide" in manifest:
        fail("Rig Hub package must stay com.truckerchris.righub")
    hub = need(
        "android/src/com/truckerchris/righub/HubActivity.java",
        'static final String VER="1.9.0"',
        'file:///android_asset/tandem/index.html',
        'file:///android_asset/hazmat/index.html',
        'file:///android_asset/inspection/index.html',
        'file:///android_asset/weather/index.html',
        'setText("\\u2696  Tandem")',
        'setContentDescription("Tandem Slide")',
        'setText("\\u2622  Hazmat")',
        'setContentDescription("Hazmat Helper")',
        'setText("\\u2611  Inspect")',
        'setContentDescription("Truck and Trailer Inspection")',
        'setText("\\uD83D\\uDD27  Care")',
        'setContentDescription("RigCare")',
        'file:///android_asset/rigcare/index.html',
        "showCare()",
        'setText("Stores")',
        'setContentDescription("Walmart Store Finder")',
        'file:///android_asset/stores/index.html',
        "showStores()",
        "StoreNavBridge",
        "__righubSetDestination",
        'putBoolean("stores"',
        'putBoolean("care"',
        "showOrig(0)",
        "showOrig(1)",
        "showWx(",
        "showSlide()",
        "showHaz()",
        "showInsp()",
        "INSP_DOWNLOAD",
        "Saved to Downloads:",
        'putBoolean("wx"',
        'putBoolean("slide"',
        'putBoolean("haz"',
        'putBoolean("insp"',
        'getStringExtra("tab")',
    )
    for banned in ["deleteAllData", "clearCache", "removeAll", "WebStorage"]:
        if banned in hub:
            fail("HubActivity clears saved web data via " + banned)
    need(
        "android/src/com/truckerchris/righub/WxChecker.java",
        'UA="RigHub/1.9.0 (trucker.chris02@gmail.com)"',
        'getSharedPreferences("righub_wx"',
        'putExtra("tab","alerts")',
    )
    trip = need(
        "android/assets/www/index.html",
        "trip-logger-shared-v1",
        "trip-logger-rates-v1",
        "trip-logger-mile-rates-v1",
        "trip-logger-pay-period-v1",
        "trip-logger-weeks-v1",
        "Rig Hub v1.9.0",
        "Trip Logger v1.5.0",
    )
    if "tandemslide.v1" in trip:
        fail("Trip Logger storage collided with the tandem key")
    nav = need("android/assets/rignav/index.html", "rn_favs", "rn_gates", "Rig Hub v1.9.0", "__righubSetDestination", "walmartHits", "Walmart 59")
    if "tandemslide.v1" in nav:
        fail("Rig Nav storage collided with the tandem key")
    wx = need("android/assets/weather/index.html", "st_", "Rig Hub v1.9.0", "Not a replacement for official warnings")
    if "tandemslide.v1" in wx:
        fail("Weather storage collided with the tandem key")
    need("android/assets/tandem/index.html", "tandemslide.v1", "always re-scale", "Calculate slide")
    need("android/assets/hazmat/index.html", "hz_", "Hazmat Helper v1.0", "not legal advice")
    need("android/assets/inspection/index.html", "btnSaveJson", "Nothing is kept in this browser", "Load a saved inspection")
    desk = need(
        "flatpak/righub.py",
        "VER='1.9.0'",
        "('slide','Tandem Slide','object-flip-horizontal-symbolic','tandem/index.html','Tandem Slide v1.0')",
        "('haz','Hazmat','dialog-warning-symbolic','hazmat/index.html','Hazmat Helper v1.0')",
        "('insp','Inspection','checkbox-checked-symbolic','inspection/index.html','Inspection v1.1')",
        "('care','RigCare','preferences-system-symbolic','rigcare/index.html','RigCare v1.2')",
        "('stores','Stores','system-search-symbolic','stores/index.html','Store Finder v1.2.0')",
        "on_store_nav",
        "('nav','Rig Nav'",
        "('log','Trip Logger'",
        "('wx','Weather'",
        "last-tab",
    )
    home = need(
        "flatpak/app/index.html",
        "Rig Hub v1.9.0 desktop",
        'href="stores/index.html"',
        'href="tandem/index.html"',
        'href="hazmat/index.html"',
        'href="inspection/index.html"',
        'href="rigcare/index.html"',
        'href="rignav/index.html"',
        'href="trip.html"',
        'href="weather.html"',
        "Always re-scale after pinning.",
        "Everything you save stays on this computer.",
    )
    if home.count('class="card"') != 8:
        fail("desktop home should have eight tool cards")
    need("flatpak/app/trip.html", "trip-logger-shared-v1", "Rig Hub v1.9.0", "Trip Logger v1.5.0")
    need("android/assets/rigcare/index.html", "rigcare_db", "RigCare v", "+ Service")
    need("android/assets/rigcare/logic.js", "Oil change", "function addLog")
    need("flatpak/com.truckerchris.RigHub.metainfo.xml", 'version="1.9.0"', 'version="1.8.0"', 'version="1.7.0"', 'version="1.6.0"', 'version="1.5.1"', "Always re-scale after pinning")
    need("flatpak/com.truckerchris.RigHub.desktop", "Tandem Slide", "Hazmat", "Inspection", "Store Finder", "com.truckerchris.RigHub")
    stores = need(
        "android/assets/stores/index.html",
        "Navigate in Rig Nav",
        "Rig Hub v1.9.0",
        "Store Finder v1.2.0",
        "righub_nav_dest",
    )
    if "wsf_custom" in stores:
        fail("hub Store Finder page uses the standalone storage key")
    hub_app = need("android/assets/stores/app.js", "righub_stores_custom", "righub_stores_edits", "righub_stores_deleted")
    if "wsf_" in hub_app:
        fail("hub Store Finder keys collide with the standalone app")
    standalone = (ROOT / "storefinder/www/app.js").read_text(encoding="utf-8")
    if 'var KEY_CUSTOM = "wsf_custom"' not in standalone or "righub_stores_" in standalone:
        fail("standalone Store Finder storage keys were changed")
    if "Navigate in Rig Nav" in (ROOT / "storefinder/www/index.html").read_text(encoding="utf-8"):
        fail("standalone Store Finder page was given the hub navigation button")
    for name in ("us-stores.js", "dcs.js", "stores.js", "navlink.js", "app.js", "index.html"):
        android_copy = (HUB / "android/assets/stores" / name).read_bytes()
        desktop_copy = (HUB / "flatpak/app/stores" / name).read_bytes()
        if android_copy != desktop_copy:
            fail("android and desktop Store Finder copies differ: " + name)
    catalog = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for blob, name in ((catalog, "index.html"), (readme, "README.md")):
        if "rig-hub-v1.9.0" not in blob or "RigHub-v1.9.0.apk" not in blob:
            fail(name + " does not point at Rig Hub 1.9.0")
        if 'data-section="all-in-one"' not in blob and name == "index.html":
            fail(name + " lost the All-in-One Hub Apps section")
        if "Hazmat Helper" not in blob or "Inspection" not in blob:
            fail(name + " does not describe Hazmat Helper and Inspection")
        if "tandem-slide-v1.0" not in blob:
            fail(name + " dropped the standalone Tandem Slide download")
        if "hazmat-helper-v1.0" not in blob or "trucker-inspection-report-v1.1" not in blob:
            fail(name + " dropped a standalone Hazmat or Inspection download")
        if "rigcare-v1.2" not in blob:
            fail(name + " dropped the standalone RigCare download")
    if "com.truckerchris.righub" not in readme:
        fail("README lost the Rig Hub package name")
    apk = HUB / "dist" / "RigHub-v1.9.0-unsigned.apk"
    if apk.exists():
        sys.path.insert(0, str(HUB / "tools"))
        import build_unsigned_apk
        build_unsigned_apk.verify(apk)
        print("ok unsigned apk", apk)
    subprocess.check_call(["node", str(HUB / "tests" / "test_store_nav.js")])
    print("ok hub integration")

if __name__ == "__main__":
    main()
