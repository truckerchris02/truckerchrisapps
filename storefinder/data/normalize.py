"""Normalize public Walmart records.

Unknown store numbers, street addresses, and phone numbers stay blank.
Nothing in this module fabricates a number or a phone.
"""
from __future__ import annotations

import re

RETRIEVED = "2026-11-09"

USPS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}
NAME_TO_USPS = {name.lower(): code for code, name in USPS.items()}
NAME_TO_USPS["washington dc"] = "DC"
NAME_TO_USPS["d.c."] = "DC"
NAME_TO_USPS["district of columbia"] = "DC"

NON_US_COUNTRY = {
    "ca", "can", "canada", "mx", "mex", "mexico", "cn", "china", "gb", "uk",
    "united kingdom", "gt", "guatemala", "sv", "el salvador", "hn", "honduras",
    "ni", "nicaragua", "cr", "costa rica", "pa", "panama", "cl", "chile",
    "ar", "argentina", "br", "brazil", "jp", "japan", "in", "india",
}
US_COUNTRY = {"us", "usa", "u.s.", "u.s.a.", "united states", "united states of america", "pr", "puerto rico"}

SHOP_SKIP = {
    "garden_centre", "car_repair", "optician", "photo", "mobile_phone",
    "alcohol", "pharmacy", "hairdresser", "beauty", "car", "car_parts",
    "tyres", "clothes",
}
AMENITY_SKIP = {"fuel", "pharmacy", "car_wash", "atm", "bank", "fast_food", "cafe", "restaurant"}
DEPT_NAME = re.compile(
    r"pharmacy|pharma|garden|photo center|vision center|optical|auto care|"
    r"tire\s*&|tire and lube|fuel|gas station|money\s*center|connection center|"
    r"pickup|garden centre|accès pharma|acces pharma",
    re.I,
)
DC_NAME = re.compile(r"distribution|fulfillment|fulfilment", re.I)
DC_SKIP = re.compile(
    r"entrance|exit|parking|driveway|front entry|truck\b|dock door|"
    r"\b(drive|road|rd|street|st|avenue|ave|boulevard|blvd|lane|ln|parkway|pkwy)\s*$",
    re.I,
)
SAMS = re.compile(r"sam'?s\s+club", re.I)
NUM_ONLY = re.compile(r"^\s*#?\s*(\d{1,5})\s*$")
DC_NUM = re.compile(r"(?:#|no\.?|dc\s*)\s*(\d{3,5})\b|(?:center|centre|idc)\s*#?\s*(\d{3,5})\s*$", re.I)
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
BAD_PHONE = {"n/a", "na", "none", "unknown", "null", "-", "not available", "yes", "no"}


def clean(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def normalize_state(value) -> str:
    text = clean(value).replace(".", "")
    if not text:
        return ""
    up = text.upper()
    if up in USPS:
        return up
    return NAME_TO_USPS.get(text.lower(), "")


def store_number(ref: str) -> str:
    match = NUM_ONLY.match(clean(ref))
    if not match:
        return ""
    return str(int(match.group(1)))


def dc_number(ref: str, name: str) -> str:
    from_ref = store_number(ref)
    if from_ref and len(from_ref) >= 3:
        return from_ref
    if from_ref:
        return ""
    found = DC_NUM.search(clean(name))
    if not found:
        return ""
    digits = found.group(1) or found.group(2) or ""
    return str(int(digits)) if digits else ""


def phone_of(*values) -> str:
    for value in values:
        text = clean(value)
        if not text:
            continue
        if text.lower() in BAD_PHONE:
            continue
        digits = re.sub(r"\D", "", text)
        if len(digits) < 7:
            continue
        return text
    return ""


def website_of(value: str) -> str:
    text = clean(value)
    if text.lower().startswith("http://") or text.lower().startswith("https://"):
        return text
    return ""


def zip_of(value: str) -> str:
    match = ZIP_RE.search(clean(value))
    return match.group(1) if match else ""


def address_piece(value) -> str:
    return clean(value).strip(" ,;")


def address_of(housenumber, street, city, state, postcode) -> str:
    street_line = " ".join(part for part in (address_piece(housenumber), address_piece(street)) if part)
    locality = address_piece(city)
    region = address_piece(state)
    postal = zip_of(postcode)
    tail = " ".join(part for part in (region, postal) if part)
    pieces = [piece for piece in (street_line, locality, tail) if piece]
    if not street_line and not locality:
        return ""
    return ", ".join(pieces)


def retail_type(name: str) -> str:
    low = clean(name).lower()
    if "neighborhood market" in low or "neighbourhood market" in low:
        return "Neighborhood Market"
    if "supercenter" in low or "super center" in low:
        return "Supercenter"
    return "Store"


def display_name(name: str, city: str, state: str, fallback: str) -> str:
    label = clean(name) or fallback
    generic = {
        "walmart", "wal-mart", "wal mart", "walmart supercenter", "wal-mart supercenter",
        "walmart neighborhood market", "walmart neighbourhood market",
        "walmart distribution center", "wal-mart distribution center",
        "walmart fulfillment center", "walmart fulfilment center",
    }
    if label.lower() in generic and city and state:
        return "%s — %s, %s" % (label, city, state)
    if label.lower() in generic and city:
        return "%s — %s" % (label, city)
    return label


def is_department(name: str, shop: str, amenity: str) -> bool:
    if clean(shop) in SHOP_SKIP or clean(amenity) in AMENITY_SKIP:
        return True
    if DEPT_NAME.search(clean(name) or ""):
        return True
    return False


def classify(raw: dict, state_lookup=None) -> dict | None:
    """Turn one tagged place into a store or DC record, or None to drop it."""
    name = clean(raw.get("name"))
    shop = clean(raw.get("shop"))
    amenity = clean(raw.get("amenity"))
    office = clean(raw.get("office"))
    country = clean(raw.get("country")).lower()
    if country in NON_US_COUNTRY:
        return None
    if SAMS.search(name) and not DC_NAME.search(name):
        return None
    retail_shop = shop in {"supermarket", "department_store", "convenience", "outpost", "general", "variety", "wholesale"}
    dc = bool(DC_NAME.search(name)) or (
        clean(raw.get("industrial")).lower() in {"warehouse", "distribution", "logistics"} and not retail_shop
    )
    if dc and (DC_SKIP.search(name) or not re.search(r"center|centre|warehouse|fulfillment|fulfilment", name, re.I)):
        return None
    if office and not dc:
        return None
    if not dc and is_department(name, shop, amenity):
        return None
    if not dc and shop and shop not in {"supermarket", "department_store", "convenience", "outpost", "general", "variety", "wholesale"}:
        return None

    lat = raw.get("lat")
    lon = raw.get("lon")
    tagged_state = normalize_state(raw.get("state"))
    located = ""
    if not tagged_state and state_lookup and lat is not None and lon is not None:
        located = state_lookup(lat, lon) or ""
    state = tagged_state or located
    if country and country not in US_COUNTRY and not state:
        return None
    if not state and country not in US_COUNTRY:
        return None
    if not state:
        return None

    city = clean(raw.get("city"))
    number = dc_number(raw.get("ref") or "", name) if dc else store_number(raw.get("ref") or "")
    phone = phone_of(raw.get("phone"), raw.get("contact_phone"))
    url = website_of(raw.get("website"))
    postal = zip_of(raw.get("postcode"))
    state_for_address = tagged_state or located
    address = address_of(raw.get("housenumber"), raw.get("street"), city, state_for_address, raw.get("postcode"))
    kind = "DC" if dc else retail_type(name)
    fallback = "Walmart Distribution Center" if dc else "Walmart"
    if dc and not any((address, city, number, lat not in (None, ""))):
        return None
    label = display_name(name, city, state, fallback)
    key = clean(raw.get("catalog_key"))
    note = "OpenStreetMap %s (ODbL), retrieved %s" % (key or "feature", RETRIEVED)
    if located and not tagged_state:
        note += ". State taken from the mapped location; addr:state was blank"
    record = {
        "catalogKey": key,
        "name": label,
        "type": kind,
        "storeNumber": number,
        "address": address,
        "city": city,
        "state": state,
        "zip": postal,
        "county": clean(raw.get("county")),
        "phone": phone,
        "officialUrl": url,
        "lat": round(float(lat), 5) if lat not in (None, "") else "",
        "lon": round(float(lon), 5) if lon not in (None, "") else "",
        "notes": "",
        "gateNotes": "",
        "source": "OpenStreetMap",
        "sourceNote": note,
    }
    return record


class StateLocator:
    def __init__(self, geojson: dict):
        self.shapes = []
        for feature in geojson.get("features", []):
            code = NAME_TO_USPS.get(clean(feature.get("properties", {}).get("name")).lower(), "")
            if not code:
                continue
            geometry = feature.get("geometry") or {}
            polygons = []
            kind = geometry.get("type")
            coords = geometry.get("coordinates") or []
            if kind == "Polygon":
                polygons.append(coords)
            elif kind == "MultiPolygon":
                polygons.extend(coords)
            boxes = []
            for poly in polygons:
                if not poly or not poly[0]:
                    continue
                lons = [pt[0] for pt in poly[0]]
                lats = [pt[1] for pt in poly[0]]
                boxes.append((min(lons), min(lats), max(lons), max(lats), poly))
            self.shapes.append((code, boxes))

    def state_at(self, lat, lon) -> str:
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return ""
        for code, boxes in self.shapes:
            for min_lon, min_lat, max_lon, max_lat, poly in boxes:
                if lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat:
                    continue
                if _in_polygon(lon, lat, poly):
                    return code
        if 17.5 <= lat <= 18.6 and -67.5 <= lon <= -65.2:
            return "PR"
        return ""


def _in_ring(lon, lat, ring) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            denom = (yj - yi) or 1e-12
            x_cross = (xj - xi) * (lat - yi) / denom + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def _in_polygon(lon, lat, polygon) -> bool:
    if not polygon or not _in_ring(lon, lat, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _in_ring(lon, lat, hole):
            return False
    return True
