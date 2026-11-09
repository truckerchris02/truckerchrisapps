# Rig Hub 1.8.0 build

Package stays `com.truckerchris.righub`. Version name is `1.8.0`. Version code is `14` (1.5.1 was version code `11`), so an update signed with the same key keeps Rig Nav, Trip Logger, Weather, and Tandem Slide data.

Tandem Slide in this app is the standalone calculator: `android/assets/tandem/` and `flatpak/app/tandem/` are copies of that engine and page. The phone tab and the desktop switcher only open that page. They do not contain a second axle formula.

The unsigned APK reuses the 1.5.1 `classes.dex` for `MainActivity`, `MileService` and `MileStore`, and reuses the 1.5.1 `resources.arsc`. Only `HubActivity` is recompiled. That keeps the trip-mileage shell and the resource ids (`ic_stat` is `0x7f010001`).

## Tests

```bash
python3 righub/tests/test_tandem_parity.py
python3 righub/tests/test_hub_integration.py
```

The parity test runs the original Python calculator against the engine packed into Rig Hub, including slide direction, hole count, pin spacing, rejected input, and the return-to-shipper stop.

## Unsigned APK

From the repo root, pass the published `RigHub-v1.5.1.apk` (GitHub release `rig-hub-v1.5.1`). The script reads its stored resource bytes and does not sign anything.

```bash
python3 righub/tools/build_unsigned_apk.py /path/to/RigHub-v1.5.1.apk
```

Output: `righub/dist/RigHub-v1.8.0-unsigned.apk`.

The script downloads `android.jar`, R8/d8 and dexlib2 into `righub/.toolcache` (gitignored). Set `RIGHUB_TOOLS` to a directory that already has those jars to skip the download. Java 8+ is required (`javac`, `jar`, `java`).

This APK is not installable until it is signed. Android will reject a different key, and installing over 1.5.1 with a different key would force an uninstall. Do not run `keytool -genkeypair` and do not commit a keystore.

## Sign with the original key

The 1.5.1 APK signature files are `META-INF/RIGHUB.SF` and `META-INF/RIGHUB.RSA`. That is the name jarsigner uses for alias `RIGHUB`. The certificate subject is `CN=Rig Hub, O=Trucker Chris`. Its SHA-256 is:

```text
A9:AE:49:07:5D:B0:07:11:00:B8:CF:A9:73:5F:74:59:76:71:6F:18:BD:0A:B8:1B:7A:22:93:E4:CB:4D:57:5E
```

Confirm the keystore on your computer matches before signing. If your alias is not `RIGHUB`, use the alias that produced that certificate. Do not create a replacement key.

```bash
keytool -list -v -keystore /PATH/TO/YOUR/EXISTING.keystore -alias RIGHUB

apksigner sign \
  --ks /PATH/TO/YOUR/EXISTING.keystore \
  --ks-key-alias RIGHUB \
  --out RigHub-v1.8.0.apk \
  righub/dist/RigHub-v1.8.0-unsigned.apk

apksigner verify --print-certs RigHub-v1.8.0.apk
```

`resources.arsc` in the unsigned APK is already stored and 4-byte aligned. If `apksigner` asks for alignment, run `zipalign -p -f 4` on a copy and sign that copy.

## Desktop Flatpak

The wrapper is `righub/flatpak`. It needs `org.gnome.Platform//51` and `org.gnome.Sdk//51`. This does not use the Android signing key.

```bash
flatpak install --user flathub org.gnome.Platform//51 org.gnome.Sdk//51
cd righub/flatpak
flatpak-builder --user --force-clean --repo=repo build com.truckerchris.RigHub.yml
flatpak build-bundle repo RigHub-v1.8.0.flatpak com.truckerchris.RigHub
```

## Publishing

Do not upload the unsigned APK as the release file. After the APK is signed with the original key and the Flatpak bundle is built, create GitHub release `rig-hub-v1.8.0` and attach:

- `RigHub-v1.8.0.apk`
- `RigHub-v1.8.0.flatpak`

Leave every older release, including `rig-hub-v1.5.1` and `tandem-slide-v1.0`, where it is. The download page in this repo now links to the 1.6.0 asset names. Those links 404 until that release exists.

## iPhone web

This repo does not contain the iPhone Rig Hub site. That site is https://github.com/truckerchris02/truckerchriswebapps (`rig-hub/`). It still shows Rig Nav, Trip Logger and Weather at v1.5, and its service worker cache is `rig-hub-v1.5`. Standalone Tandem Slide is already at `tandemslide/` in that repo. A follow-up there should add a Tandem Slide card on `rig-hub/index.html`, copy this same `engine.js` and `index.html` into `rig-hub/tandem/` (so it stays inside the Rig Hub cache scope), and add those files to `rig-hub/sw.js` under a new cache name. Do not change Trip Logger pay logic in that follow-up.
