/* Rig Hub only. Turns a Store Finder record into a Rig Nav destination.
   The standalone Store Finder does not load this file. */
var RigHubStoreNav = (function () {
  function digits(value) {
    var d = String(value == null ? "" : value).replace(/\D/g, "");
    return d ? String(parseInt(d, 10)) : "";
  }
  function wantsDc(query) {
    var text = String(query || "");
    return /\b(dc|distribution(?:\s+center)?)\b/i.test(text) && !/\bwal[\s-]*mart\b/i.test(text);
  }
  function numberFrom(query) {
    var text = String(query || "").trim();
    var patterns = [
      /^(?:wal[\s-]*mart|wm)\s+(?:dc\s*)?#?\s*(\d{1,5})$/i,
      /^(?:dc|distribution(?:\s+center)?)\s*#?\s*(\d{1,5})$/i,
      /^(?:store|supercenter|neighborhood market)\s*#?\s*(\d{1,5})$/i,
      /^#\s*(\d{1,5})$/
    ];
    for (var i = 0; i < patterns.length; i++) {
      var match = text.match(patterns[i]);
      if (match) return String(parseInt(match[1], 10));
    }
    return "";
  }
  function catalogHits(catalog, query, searchCatalog) {
    var q = String(query || "").trim();
    var rows = [];
    if (!q) return rows;
    var number = numberFrom(q);
    var dcOnly = wantsDc(q);
    if (number) {
      for (var i = 0; i < catalog.length; i++) {
        var rec = catalog[i];
        if (digits(rec.storeNumber) !== number) continue;
        if (dcOnly && rec.type !== "DC") continue;
        rows.push(rec);
      }
      if (rows.length) return rows;
    }
    if (typeof searchCatalog === "function") return searchCatalog(catalog, q);
    return rows;
  }
  function labelOf(record) {
    if (!record) return null;
    var title = record.name || (record.type === "DC" ? "Walmart DC" : "Walmart");
    var address = record.address || "";
    var name = title;
    if (address && title.indexOf(address) === -1) name = title + " — " + address;
    var rawLat = record.lat;
    var rawLon = record.lon;
    var lat = Number(rawLat);
    var lon = Number(rawLon);
    var has = String(rawLat == null ? "" : rawLat) !== "" && String(rawLon == null ? "" : rawLon) !== "" && isFinite(lat) && isFinite(lon);
    return {
      title: title,
      address: address,
      name: name,
      lat: has ? lat : null,
      lng: has ? lon : null,
      lon: has ? lon : null,
      storeNumber: record.storeNumber || "",
      type: record.type || ""
    };
  }
  function payload(record) {
    var body = labelOf(record);
    if (!body || body.lat == null || body.lng == null) return null;
    return body;
  }
  function enrich(record, catalog) {
    if (!record) return record;
    var current = labelOf(record);
    if (current && current.lat != null) return record;
    var number = digits(record.storeNumber);
    if (!number || !catalog) return record;
    for (var i = 0; i < catalog.length; i++) {
      var other = catalog[i];
      if (digits(other.storeNumber) !== number) continue;
      if (record.type === "DC" && other.type !== "DC") continue;
      if (record.type && record.type !== "DC" && other.type === "DC") continue;
      var point = labelOf(other);
      if (!point || point.lat == null) continue;
      var copy = {};
      for (var key in record) copy[key] = record[key];
      copy.lat = point.lat;
      copy.lon = point.lon;
      if (!copy.address) copy.address = other.address;
      return copy;
    }
    return record;
  }
  function handoff(record) {
    var body = labelOf(record);
    if (!body) return { ok: false, reason: "no-record" };
    if (body.lat != null && body.lng != null) {
      return { ok: true, mode: "point", tab: "nav", destination: body };
    }
    if (body.address) {
      return { ok: true, mode: "address", tab: "nav", destination: body };
    }
    return { ok: false, reason: "no-location", destination: body };
  }
  /* Switches the fake or real nav shell onto this place.
     A mapped store uses lat/lon. A saved DC that only has a street address
     uses Rig Nav's existing geocoder, with the Walmart name as the label. */
  function applyToNav(nav, record) {
    var hop = handoff(record);
    if (!hop.ok) return hop;
    nav.tab = hop.tab;
    var dest = hop.destination;
    if (hop.mode === "point") nav.setDestination(dest.lat, dest.lng, dest.name);
    else nav.geocodeDestination(dest.address, dest.name);
    return hop;
  }
  return {
    digits: digits,
    numberFrom: numberFrom,
    catalogHits: catalogHits,
    labelOf: labelOf,
    payload: payload,
    enrich: enrich,
    handoff: handoff,
    applyToNav: applyToNav
  };
})();
if (typeof module !== "undefined" && module.exports) module.exports = RigHubStoreNav;
