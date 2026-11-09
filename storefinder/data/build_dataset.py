#!/usr/bin/env python3
"""Build the bundled US Walmart store list and the DC starter list.

Stores come from the public OpenStreetMap planet via the QLever mirror
(brand:wikidata=Q483551). Distribution centers are OSM features whose names
say distribution or fulfillment, plus street addresses copied from the
ABFBA 2026 public warehouse list. Fields that are not in the source stay blank.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from normalize import RETRIEVED, StateLocator, address_of, classify, clean, dc_number, normalize_state, zip_of

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WWW = ROOT / "www"
RAW = DATA / "raw"
QLEVER = "https://qlever.dev/api/osm-planet"
ABFBA_URL = "https://www.abfba.com/walmart-warehouse-master-list"
UA = "StoreFinderData/1.2 (truckerchris store list; OSM ODbL research)"
STATES_URL = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"

STORE_QUERY = r'''
PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?osm ?name ?brand ?ref ?shop ?amenity ?office ?phone ?contact_phone ?website ?housenumber ?street ?city ?state ?postcode ?country ?county ?industrial ?building ?geom WHERE {
  ?osm osmkey:brand:wikidata "Q483551" .
  OPTIONAL { ?osm osmkey:name ?name }
  OPTIONAL { ?osm osmkey:brand ?brand }
  OPTIONAL { ?osm osmkey:ref ?ref }
  OPTIONAL { ?osm osmkey:shop ?shop }
  OPTIONAL { ?osm osmkey:amenity ?amenity }
  OPTIONAL { ?osm osmkey:office ?office }
  OPTIONAL { ?osm osmkey:phone ?phone }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:contact:phone> ?contact_phone }
  OPTIONAL { ?osm osmkey:website ?website }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:housenumber> ?housenumber }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:street> ?street }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:city> ?city }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:state> ?state }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:postcode> ?postcode }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:country> ?country }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:county> ?county }
  OPTIONAL { ?osm osmkey:industrial ?industrial }
  OPTIONAL { ?osm osmkey:building ?building }
  OPTIONAL { ?osm geo:hasGeometry/geo:asWKT ?geom }
}
'''

DC_QUERY = r'''
PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?osm ?name ?ref ?phone ?website ?housenumber ?street ?city ?state ?postcode ?country ?geom WHERE {
  ?osm osmkey:name ?name .
  FILTER(REGEX(?name, "[Ww]al[- ]?[Mm]art", "i") && REGEX(?name, "Distribution|Fulfillment|Fulfilment", "i"))
  OPTIONAL { ?osm osmkey:ref ?ref }
  OPTIONAL { ?osm osmkey:phone ?phone }
  OPTIONAL { ?osm osmkey:website ?website }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:housenumber> ?housenumber }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:street> ?street }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:city> ?city }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:state> ?state }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:postcode> ?postcode }
  OPTIONAL { ?osm <https://www.openstreetmap.org/wiki/Key:addr:country> ?country }
  OPTIONAL { ?osm geo:hasGeometry/geo:asWKT ?geom }
}
'''


def fetch(url: str, data: bytes | None = None, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def qlever(query: str) -> list:
    payload = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        QLEVER,
        data=payload,
        headers={
            "User-Agent": UA,
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=240) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["results"]["bindings"]


def grouped(bindings: list) -> list:
    rows = {}
    order = []
    for binding in bindings:
        osm = (binding.get("osm") or {}).get("value") or ""
        if osm not in rows:
            rows[osm] = {"catalog_key": osm_key(osm), "geoms": []}
            order.append(osm)
        dest = rows[osm]
        for key, cell in binding.items():
            value = clean((cell or {}).get("value"))
            if not value:
                continue
            if key == "geom":
                dest["geoms"].append(value)
            elif key == "osm":
                continue
            elif not dest.get(key):
                dest[key] = value
    out = []
    for osm in order:
        raw = rows[osm]
        lat, lon = centroid(raw.get("geoms") or [])
        raw["lat"] = lat
        raw["lon"] = lon
        out.append(raw)
    return out


def osm_key(uri: str) -> str:
    marker = "https://www.openstreetmap.org/"
    if uri.startswith(marker):
        return uri[len(marker):]
    return uri


def centroid(geoms: list):
    text = " ".join(geoms)
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    if len(nums) < 2:
        return None, None
    lons = []
    lats = []
    for index in range(0, len(nums) - 1, 2):
        lons.append(float(nums[index]))
        lats.append(float(nums[index + 1]))
    if not lons:
        return None, None
    return sum(lats) / len(lats), sum(lons) / len(lons)


def load_states() -> StateLocator:
    RAW.mkdir(parents=True, exist_ok=True)
    path = Path(os.environ.get("SF_STATES", RAW / "us-states.json"))
    if not path.exists():
        path.write_bytes(fetch(STATES_URL, timeout=60))
    return StateLocator(json.loads(path.read_text(encoding="utf-8")))


def dedupe(records: list) -> list:
    chosen = {}
    order = []
    for record in records:
        key = dedupe_key(record)
        previous = chosen.get(key)
        if previous is None:
            chosen[key] = record
            order.append(key)
            continue
        fill_blanks(previous, record)
    return [chosen[key] for key in order]


def dedupe_key(record: dict):
    number = record.get("storeNumber") or ""
    postal = record.get("zip") or ""
    city = (record.get("city") or "").lower()
    state = record.get("state") or ""
    if number and (postal or city):
        return ("num", number, postal or city, state)
    lat, lon = record.get("lat"), record.get("lon")
    if lat != "" and lon != "":
        return ("geo", record.get("type"), round(float(lat), 3), round(float(lon), 3))
    return ("id", record.get("catalogKey") or record.get("name"))


def fill_blanks(dest: dict, src: dict) -> None:
    for key, value in src.items():
        if value in ("", None, []):
            continue
        if dest.get(key) in ("", None, []):
            dest[key] = value


def street_num(address: str) -> str:
    match = re.match(r"\s*(\d+)", address or "")
    return match.group(1) if match else ""


def same_dc(left: dict, right: dict) -> bool:
    if left.get("storeNumber") and left["storeNumber"] == right.get("storeNumber"):
        return True
    if (left.get("state"), (left.get("city") or "").lower()) != (right.get("state"), (right.get("city") or "").lower()):
        return False
    if not left.get("city"):
        return False
    left_num, right_num = street_num(left.get("address") or ""), street_num(right.get("address") or "")
    if left_num and right_num:
        return left_num == right_num and (not left.get("zip") or not right.get("zip") or left["zip"] == right["zip"])
    return True


def merge_dc(base: list, extra: list) -> list:
    for record in extra:
        match = next((item for item in base if same_dc(item, record)), None)
        if match is None:
            base.append(record)
            continue
        if match.get("address") and record.get("address") and street_num(match["address"]) != street_num(record["address"]):
            base.append(record)
            continue
        fill_blanks(match, record)
        if record.get("source") and record["source"] not in (match.get("source") or ""):
            match["source"] = (match.get("source") or "") + " + " + record["source"]
        if record.get("sourceNote") and record["sourceNote"] not in (match.get("sourceNote") or ""):
            match["sourceNote"] = (match.get("sourceNote") or "") + " Also: " + record["sourceNote"]
    return base


def parse_abfba(html: str) -> list:
    rows = []
    sections = (
        ("Regional Distribution Center", "Part 1"),
        ("Import Distribution Center", "Part 3"),
        ("Fulfillment Center", "Part 4"),
    )
    # Split on h2 so each table stays with its heading.
    parts = re.split(r"<h2[^>]*>", html, flags=re.I)
    for part in parts[1:]:
        title = re.sub(r"<[^>]+>", "", part.split("</h2>", 1)[0])
        title = clean(title)
        kind = ""
        section = ""
        low = title.lower()
        if "regional" in low:
            kind, section = "Walmart Regional Distribution Center", "Part 1 Regional Distribution Centers"
        elif "import" in low:
            kind, section = "Walmart Import Distribution Center", "Part 3 Import Distribution Centers"
        elif "ecommerce" in low or "fulfillment" in low:
            kind, section = "Walmart Fulfillment Center", "Part 4 eCommerce Fulfillment Centers"
        if not kind:
            continue
        for cells in re.findall(r"<tr>(.*?)</tr>", part, flags=re.I | re.S):
            values = [clean(re.sub(r"<[^>]+>", " ", cell)) for cell in re.findall(r"<td>(.*?)</td>", cells, flags=re.I | re.S)]
            if len(values) < 4:
                continue
            if "regional" in low:
                number, city, state, address = values[0], values[1], values[2], values[3]
            elif "import" in low:
                number, city, state, address = "", values[1], values[2], values[3]
            else:
                number, city, state, address = "", values[0], values[1], values[2]
            if "public address" in address.lower() or "limited" == address.lower():
                continue
            note_extra = ""
            paren = re.search(r"\(([^)]+)\)\s*$", address)
            if paren:
                note_extra = paren.group(1)
                address = clean(address[:paren.start()])
            state_code = normalize_state(state)
            if not state_code or not city or not address:
                continue
            digits = ""
            match = re.search(r"(\d{3,5})", number or "")
            if match:
                digits = str(int(match.group(1)))
            label = kind
            if digits:
                label += " " + digits
            label += " — %s, %s" % (city, state_code)
            rows.append({
                "catalogKey": "abfba:%s:%s" % (state_code, re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")),
                "name": label,
                "type": "DC",
                "storeNumber": digits,
                "address": address,
                "city": city,
                "state": state_code,
                "zip": zip_of(address),
                "county": "",
                "phone": "",
                "officialUrl": "",
                "lat": "",
                "lon": "",
                "notes": note_extra,
                "gateNotes": "",
                "metroArea": "Distribution",
                "source": "ABFBA public list",
                "sourceNote": "ABFBA 2026 public warehouse list, %s, %s, retrieved %s. Not an official Walmart directory. %s" % (
                    section, ABFBA_URL, RETRIEVED, "Phones are not in that list."),
            })
    return rows


def write_js(path: Path, var_name: str, records: list, blurb: str) -> None:
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    path.write_text("/* %s */\nvar %s = %s;\n" % (blurb, var_name, payload), encoding="utf-8")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    print("loading state shapes", flush=True)
    locator = load_states()
    store_cache = RAW / "osm-stores.json"
    dc_cache = RAW / "osm-dcs.json"
    if os.environ.get("SF_REUSE") == "1" and store_cache.exists() and dc_cache.exists():
        print("reusing cached OSM rows", flush=True)
        store_rows = json.loads(store_cache.read_text(encoding="utf-8"))
        dc_rows = json.loads(dc_cache.read_text(encoding="utf-8"))
    else:
        print("querying OSM stores", flush=True)
        store_rows = grouped(qlever(STORE_QUERY))
        store_cache.write_text(json.dumps(store_rows), encoding="utf-8")
        print("store rows", len(store_rows), flush=True)
        print("querying OSM distribution centers", flush=True)
        dc_rows = grouped(qlever(DC_QUERY))
        dc_cache.write_text(json.dumps(dc_rows), encoding="utf-8")
    print("store rows", len(store_rows), "dc rows", len(dc_rows), flush=True)

    stores = []
    osm_dcs = []
    for raw in store_rows:
        record = classify(raw, locator.state_at)
        if not record:
            continue
        if record["type"] == "DC":
            osm_dcs.append(record)
        else:
            stores.append(record)
    for raw in dc_rows:
        raw["industrial"] = raw.get("industrial") or "distribution"
        record = classify(raw, locator.state_at)
        if record and record["type"] == "DC":
            osm_dcs.append(record)

    stores = dedupe(stores)
    osm_dcs = dedupe(osm_dcs)
    stores.sort(key=lambda item: (item["state"], item["city"], item["name"], item["catalogKey"]))
    osm_dcs.sort(key=lambda item: (item["state"], item["city"], item["name"], item["catalogKey"]))

    html_path = Path(os.environ.get("SF_ABFBA", "/tmp/osm/abfba.html"))
    if not html_path.exists():
        html_path.write_bytes(fetch(ABFBA_URL, timeout=60))
    abfba = parse_abfba(html_path.read_text(encoding="utf-8", errors="replace"))
    dcs = merge_dc(osm_dcs, abfba)
    dcs.sort(key=lambda item: (item["state"], item["city"], item["storeNumber"], item["name"]))
    for index, record in enumerate(dcs):
        record["id"] = 1000 + index
        record["metroArea"] = "Distribution"
        record.setdefault("county", "")
        record.setdefault("officialUrl", "")
        record.setdefault("notes", "")
        record.setdefault("gateNotes", "")

    (DATA / "us-walmart.json").write_text(json.dumps(stores, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (DATA / "distribution-centers.json").write_text(json.dumps(dcs, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_js(
        WWW / "us-stores.js",
        "US_STORES",
        stores,
        "US Walmart stores from OpenStreetMap contributors, ODbL. Built %s by storefinder/data/build_dataset.py. Unknown numbers, streets, and phones are blank." % RETRIEVED,
    )
    write_js(
        WWW / "dcs.js",
        "DC_SEED",
        dcs,
        "Walmart distribution-center starter list. OpenStreetMap (ODbL) plus the ABFBA 2026 public list. Built %s. Unknown phones are blank." % RETRIEVED,
    )
    counts = {
        "retrieved": RETRIEVED,
        "osm_store_rows": len(store_rows),
        "osm_dc_rows": len(dc_rows),
        "us_stores": len(stores),
        "stores_with_number": sum(1 for item in stores if item["storeNumber"]),
        "stores_with_phone": sum(1 for item in stores if item["phone"]),
        "stores_with_street": sum(1 for item in stores if re.match(r"\s*\d", item["address"] or "")),
        "stores_with_zip": sum(1 for item in stores if item["zip"]),
        "distribution_centers": len(dcs),
        "dcs_from_abfba_included": sum(1 for item in dcs if "ABFBA" in (item.get("source") or "") or "ABFBA" in (item.get("sourceNote") or "")),
        "dcs_with_number": sum(1 for item in dcs if item["storeNumber"]),
        "dcs_with_phone": sum(1 for item in dcs if item["phone"]),
    }
    (DATA / "COUNTS.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
