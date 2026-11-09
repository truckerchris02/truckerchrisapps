# Store Finder 1.2.0 build

Package stays `com.truckerchris.storefinder`. Version name is `1.2.0`. Version code is `11` (1.1.8 was version code `10`), so an update signed with the same key keeps the WebView `localStorage` data.

Your list still uses the v1.1.8 keys `wsf_custom`, `wsf_edits`, and `wsf_deleted`. The baked-in Joplin-area seed is the v1.1.8 `stores.js`, unchanged. Nationwide search reads `us-stores.js`. The starter distribution centers are `dcs.js` (ids 1000 and up) and can be edited or deleted with those same keys.

Location sources and the ODbL notice are in `data/SOURCE.md`.

## Tests

From the repo root:

```bash
python3 storefinder/tests/test_normalize.py
node --test storefinder/tests/test_storefinder.js
```

The node tests cover search by store number, city, state, and ZIP, one-tap save, a custom distribution center, persistence after a fresh read of the same storage, and a v1.1.8 `wsf_*` migration. They also check that the bundled list does not fill phones or numbers with placeholders.

## Dataset

`www/us-stores.js` and `www/dcs.js` are generated files. Refresh them (needs network) with:

```bash
python3 storefinder/data/build_dataset.py
```

That reads OpenStreetMap through the QLever OSM planet endpoint and the ABFBA public warehouse page. It does not invent store numbers, street addresses, or phone numbers.

## Unsigned APK

From the repo root. Java 8+ is required (`javac`, `java`). The script downloads `android.jar`, R8/d8, and Android build-tools into `storefinder/.toolcache` (gitignored). Set `STOREFINDER_TOOLS` to a directory that already has `android.jar` and `r8.jar`, and `AAPT2` to an `aapt2` binary, to skip those downloads.

```bash
python3 storefinder/tools/build_unsigned_apk.py
```

Output: `storefinder/dist/StoreFinder-v1.2.0-unsigned.apk`.

The script does not create a keystore and does not sign the APK. This APK is not installable until it is signed. Android will reject a different key, and installing over 1.1.8 with a different key forces an uninstall, which deletes saved stores. Do not run `keytool -genkeypair` and do not commit a keystore.

## Sign with the original key

The 1.1.8 APK signature files are `META-INF/STOREFIN.SF` and `META-INF/STOREFIN.RSA`. That is the name jarsigner uses for an alias whose first eight characters are `STOREFIN`. The certificate subject is `CN=TruckerChris Store Finder (Hark)`. Its SHA-256 is:

```text
B3:5E:69:7D:F8:80:6D:37:BB:A3:EE:96:2F:3C:C0:8C:A8:7E:40:27:4B:A4:26:71:D3:6C:96:F5:26:05:38:1D
```

Confirm the keystore on your computer matches before signing. If your alias is longer than `STOREFIN`, use the alias that produced that certificate. Do not create a replacement key.

```bash
keytool -list -v -keystore /PATH/TO/YOUR/EXISTING.keystore

apksigner sign \
  --ks /PATH/TO/YOUR/EXISTING.keystore \
  --ks-key-alias YOUR_ALIAS \
  --out StoreFinder-v1.2.0.apk \
  storefinder/dist/StoreFinder-v1.2.0-unsigned.apk

apksigner verify --print-certs StoreFinder-v1.2.0.apk
```

`resources.arsc` in the unsigned APK is stored and 4-byte aligned. If `apksigner` asks for alignment, run `zipalign -p -f 4` on a copy and sign that copy.

## Desktop Flatpak

The wrapper is `storefinder/flatpak`. App id `com.truckerchris.StoreFinder`. Runtime `org.gnome.Platform//51` and SDK `org.gnome.Sdk//51`. This does not use the Android signing key. Saved stores stay in the WebKit network session under the user data directory.

```bash
flatpak install --user flathub org.gnome.Platform//51 org.gnome.Sdk//51
cd storefinder/flatpak
flatpak-builder --user --force-clean --repo=repo build com.truckerchris.StoreFinder.yml
flatpak build-bundle repo ../dist/StoreFinder-v1.2.0.flatpak com.truckerchris.StoreFinder
```

Install check:

```bash
flatpak install --user -y ../dist/StoreFinder-v1.2.0.flatpak
flatpak run com.truckerchris.StoreFinder
```

## Publishing

Do not upload the unsigned APK as the release file. After the APK is signed with the original key and the Flatpak bundle is built, create GitHub release `store-finder-v1.2.0` and attach:

- `StoreFinder-v1.2.0.apk`
- `StoreFinder-v1.2.0.flatpak`

Leave every older release where it is. The download page links to those two file names. The links 404 until that release exists.
