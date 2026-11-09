/* Store Finder logic inside Rig Hub.
   Storage keys are namespaced so they do not collide with other Rig Hub tabs
   or with the standalone Store Finder. */
var StoreFinder = (function () {
  var KEY_CUSTOM = "righub_stores_custom";
  var KEY_EDITS = "righub_stores_edits";
  var KEY_DELETED = "righub_stores_deleted";
  var CUSTOM_BASE = 100000;
  var USPS = {
    AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California",
    CO: "Colorado", CT: "Connecticut", DE: "Delaware", DC: "District of Columbia",
    FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois",
    IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana",
    ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
    MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada",
    NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
    NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon",
    PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota",
    TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont", VA: "Virginia",
    WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming", PR: "Puerto Rico"
  };
  var NAME_TO_USPS = {};
  Object.keys(USPS).forEach(function (code) { NAME_TO_USPS[USPS[code].toLowerCase()] = code; });
  NAME_TO_USPS["washington dc"] = "DC";
  NAME_TO_USPS["district of columbia"] = "DC";

  function readJSON(storage, key, fallback) {
    try {
      var raw = storage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  }
  function writeJSON(storage, key, value) {
    storage.setItem(key, JSON.stringify(value));
  }
  function assign(target) {
    for (var i = 1; i < arguments.length; i++) {
      var src = arguments[i] || {};
      for (var key in src) {
        if (Object.prototype.hasOwnProperty.call(src, key)) target[key] = src[key];
      }
    }
    return target;
  }
  function loadUser(storage) {
    return {
      custom: readJSON(storage, KEY_CUSTOM, []),
      edits: readJSON(storage, KEY_EDITS, {}),
      deleted: readJSON(storage, KEY_DELETED, [])
    };
  }
  function deletedHas(deleted, id) {
    for (var i = 0; i < deleted.length; i++) {
      if (Number(deleted[i]) === Number(id)) return true;
    }
    return false;
  }
  function myList(seed, extras, user) {
    var out = [];
    var base = (seed || []).concat(extras || []);
    var edits = user.edits || {};
    var deleted = user.deleted || [];
    for (var i = 0; i < base.length; i++) {
      var item = base[i];
      if (deletedHas(deleted, item.id)) continue;
      var edit = edits[item.id];
      if (!edit) edit = edits[String(item.id)];
      out.push(edit ? assign({}, item, edit) : item);
    }
    return out.concat(user.custom || []);
  }
  function nextId(custom) {
    var maxId = CUSTOM_BASE - 1;
    for (var i = 0; i < custom.length; i++) {
      if (Number(custom[i].id) > maxId) maxId = Number(custom[i].id);
    }
    return maxId + 1;
  }
  function normNum(value) {
    var digits = String(value == null ? "" : value).replace(/\D/g, "");
    if (!digits) return "";
    return String(parseInt(digits, 10));
  }
  function normalizeState(value) {
    var text = String(value == null ? "" : value).trim().replace(/\./g, "");
    if (!text) return "";
    if (USPS[text.toUpperCase()]) return text.toUpperCase();
    return NAME_TO_USPS[text.toLowerCase()] || "";
  }
  function parseQuery(query) {
    var text = String(query == null ? "" : query).trim();
    if (!text) return null;
    var number = text.match(/^(?:#|no\.?|store\s*#?\s*)(\d{1,5})$/i);
    if (number) return { kind: "number", number: String(parseInt(number[1], 10)) };
    if (/^\d{1,4}$/.test(text)) return { kind: "number", number: String(parseInt(text, 10)) };
    var zip = text.match(/^(\d{5})(?:-\d{4})?$/);
    if (zip) return { kind: "zip", zip: zip[1] };
    var comma = text.match(/^(.+?)\s*,\s*([A-Za-z][A-Za-z .]*)$/);
    if (comma && normalizeState(comma[2])) {
      return { kind: "citystate", city: comma[1].trim(), state: normalizeState(comma[2]) };
    }
    var parts = text.split(/\s+/);
    if (parts.length >= 2 && normalizeState(parts[parts.length - 1])) {
      return {
        kind: "citystate",
        city: parts.slice(0, -1).join(" "),
        state: normalizeState(parts[parts.length - 1])
      };
    }
    if (normalizeState(text) && (text.length === 2 || NAME_TO_USPS[text.toLowerCase().replace(/\./g, "")] || USPS[text.toUpperCase()])) {
      return { kind: "state", state: normalizeState(text) };
    }
    return { kind: "text", text: text.toLowerCase() };
  }
  function cityMatch(city, query) {
    city = String(city || "").toLowerCase().trim();
    query = String(query || "").toLowerCase().trim();
    if (!city || !query) return false;
    if (city === query) return true;
    if (city.indexOf(query) === 0) return true;
    return query.length >= 4 && city.indexOf(query) !== -1;
  }
  function matches(record, parsed) {
    if (!parsed) return false;
    if (parsed.kind === "number") return normNum(record.storeNumber) === parsed.number;
    if (parsed.kind === "zip") return record.zip === parsed.zip || String(record.storeNumber || "") === parsed.zip;
    if (parsed.kind === "state") return String(record.state || "").toUpperCase() === parsed.state;
    if (parsed.kind === "citystate") {
      return String(record.state || "").toUpperCase() === parsed.state && cityMatch(record.city, parsed.city);
    }
    if (parsed.kind === "text") {
      if (parsed.text === "walmart" || parsed.text === "wal-mart" || parsed.text === "wal mart") return false;
      if (cityMatch(record.city, parsed.text)) return true;
      if (parsed.text.length >= 6 && String(record.address || "").toLowerCase().indexOf(parsed.text) !== -1) return true;
    }
    return false;
  }
  function searchCatalog(catalog, query) {
    var parsed = parseQuery(query);
    var out = [];
    if (!parsed) return out;
    for (var i = 0; i < catalog.length; i++) {
      if (matches(catalog[i], parsed)) out.push(catalog[i]);
    }
    out.sort(function (a, b) {
      var state = String(a.state || "").localeCompare(String(b.state || ""));
      if (state) return state;
      var city = String(a.city || "").localeCompare(String(b.city || ""));
      if (city) return city;
      return String(a.name || "").localeCompare(String(b.name || ""));
    });
    return out;
  }
  function isSaved(list, result) {
    var key = result && result.catalogKey || "";
    var number = normNum(result && result.storeNumber);
    for (var i = 0; i < list.length; i++) {
      var item = list[i];
      if (key && item.catalogKey && item.catalogKey === key) return item;
      if (number && normNum(item.storeNumber) === number) return item;
    }
    return null;
  }
  function asCustom(result, id) {
    return {
      id: id,
      catalogKey: result.catalogKey || "",
      name: result.name || "",
      type: result.type || "Store",
      storeNumber: result.storeNumber || "",
      address: result.address || "",
      city: result.city || "",
      state: result.state || "",
      zip: result.zip || "",
      county: result.county || "",
      phone: result.phone || "",
      metroArea: result.metroArea || "Saved",
      officialUrl: result.officialUrl || "",
      notes: result.notes || "",
      gateNotes: result.gateNotes || "",
      lat: result.lat || "",
      lon: result.lon || "",
      source: result.source || "",
      sourceNote: result.sourceNote || "Saved from search"
    };
  }
  function saveResult(storage, result, existingList) {
    var user = loadUser(storage);
    var existing = isSaved(existingList || user.custom, result);
    if (existing) return existing;
    var record = asCustom(result, nextId(user.custom));
    if (!record.sourceNote) record.sourceNote = "Saved from search";
    user.custom.push(record);
    writeJSON(storage, KEY_CUSTOM, user.custom);
    return record;
  }
  function addCustom(storage, fields) {
    var user = loadUser(storage);
    var record = asCustom(fields || {}, nextId(user.custom));
    record.sourceNote = (fields && fields.sourceNote) || "Added by you";
    record.metroArea = (fields && fields.metroArea) || (record.type === "DC" ? "Distribution" : "Saved");
    user.custom.push(record);
    writeJSON(storage, KEY_CUSTOM, user.custom);
    return record;
  }
  function updateEntry(storage, id, fields) {
    var user = loadUser(storage);
    id = Number(id);
    if (id >= CUSTOM_BASE) {
      for (var i = 0; i < user.custom.length; i++) {
        if (Number(user.custom[i].id) === id) {
          var prev = user.custom[i];
          user.custom[i] = assign({}, prev, fields, {
            id: id,
            sourceNote: (fields && fields.sourceNote) || prev.sourceNote || "Added by you"
          });
        }
      }
      writeJSON(storage, KEY_CUSTOM, user.custom);
    } else {
      user.edits[id] = fields;
      writeJSON(storage, KEY_EDITS, user.edits);
    }
    return loadUser(storage);
  }
  function deleteEntry(storage, id) {
    var user = loadUser(storage);
    id = Number(id);
    if (id >= CUSTOM_BASE) {
      user.custom = user.custom.filter(function (item) { return Number(item.id) !== id; });
      writeJSON(storage, KEY_CUSTOM, user.custom);
    } else {
      delete user.edits[id];
      delete user.edits[String(id)];
      if (!deletedHas(user.deleted, id)) user.deleted.push(id);
      writeJSON(storage, KEY_EDITS, user.edits);
      writeJSON(storage, KEY_DELETED, user.deleted);
    }
    return loadUser(storage);
  }
  function phoneOf(value) {
    var text = String(value == null ? "" : value).trim();
    if (!text) return "";
    var low = text.toLowerCase();
    if (low === "n/a" || low === "na" || low === "none" || low === "unknown" || low === "null") return "";
    var digits = text.replace(/\D/g, "");
    if (digits.length < 7) return "";
    return text;
  }
  function numberOf(ref) {
    var match = String(ref == null ? "" : ref).trim().match(/^#?\s*(\d{1,5})$/);
    return match ? String(parseInt(match[1], 10)) : "";
  }
  function normalizeOsmElement(el) {
    var tags = (el && el.tags) || {};
    var name = tags.name || tags.brand || "";
    var shop = tags.shop || "";
    var low = name.toLowerCase();
    if (/pharmacy|garden|photo center|vision|optical/.test(low)) return null;
    if (shop === "pharmacy" || shop === "garden_centre" || shop === "optician" || shop === "photo") return null;
    var state = normalizeState(tags["addr:state"] || "");
    var country = String(tags["addr:country"] || "").toLowerCase();
    if (country && country !== "us" && country !== "usa" && country !== "united states" && country !== "pr" && country !== "puerto rico") return null;
    if ((tags["addr:state"] || "") && !state) return null;
    var city = tags["addr:city"] || "";
    var street = [tags["addr:housenumber"], tags["addr:street"]].filter(Boolean).join(" ");
    var zip = String(tags["addr:postcode"] || "").match(/\d{5}/);
    zip = zip ? zip[0] : "";
    var tail = [state, zip].filter(Boolean).join(" ");
    var address = [street, city, tail].filter(Boolean).join(", ");
    if (!street && !city) address = "";
    var lat = el.lat;
    var lon = el.lon;
    if (el.center) { lat = el.center.lat; lon = el.center.lon; }
    var type = "Store";
    if (/neighborhood market|neighbourhood market/.test(low)) type = "Neighborhood Market";
    else if (/supercenter|super center/.test(low)) type = "Supercenter";
    else if (/distribution|fulfillment|fulfilment/.test(low)) type = "DC";
    var label = name || "Walmart";
    if (/^walmart( supercenter| neighborhood market)?$/i.test(label) && city && state) label = label + " — " + city + ", " + state;
    var website = tags.website || "";
    if (website && website.indexOf("http://") !== 0 && website.indexOf("https://") !== 0) website = "";
    return {
      catalogKey: el.type && el.id ? el.type + "/" + el.id : "",
      name: label,
      type: type,
      storeNumber: numberOf(tags.ref),
      address: address,
      city: city,
      state: state,
      zip: zip,
      county: tags["addr:county"] || "",
      phone: phoneOf(tags.phone || tags["contact:phone"] || ""),
      officialUrl: website,
      lat: lat || "",
      lon: lon || "",
      notes: "",
      gateNotes: "",
      source: "OpenStreetMap",
      sourceNote: "OpenStreetMap online lookup (ODbL). Blank fields were not in the response."
    };
  }
  function onlineQuery(query) {
    var parsed = parseQuery(query);
    if (!parsed) return "";
    if (parsed.kind === "number") {
      return '[out:json][timeout:25];nwr["brand:wikidata"="Q483551"]["ref"="' + parsed.number + '"];out tags center;';
    }
    if (parsed.kind === "zip") {
      return '[out:json][timeout:25];nwr["brand:wikidata"="Q483551"]["addr:postcode"~"^' + parsed.zip + '"];out tags center;';
    }
    var city = parsed.kind === "citystate" ? parsed.city : (parsed.kind === "text" ? parsed.text : "");
    city = String(city || "").replace(/[^A-Za-z .'-]/g, "").trim();
    if (city.length < 3) return "";
    var safe = city.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var stateFilter = "";
    if (parsed.state) {
      var full = USPS[parsed.state] || parsed.state;
      stateFilter = '["addr:state"~"^(' + parsed.state + "|" + full + ')$",i]';
    }
    return '[out:json][timeout:25];nwr["brand:wikidata"="Q483551"]["addr:city"~"^' + safe + '$",i]' + stateFilter + ';out tags center;';
  }
  function lookupOnline(query, fetchFn) {
    var q = onlineQuery(query);
    if (!q) return Promise.resolve([]);
    var urls = [
      "https://overpass-api.de/api/interpreter?data=" + encodeURIComponent(q),
      "https://overpass.kumi.systems/api/interpreter?data=" + encodeURIComponent(q)
    ];
    function attempt(index) {
      if (index >= urls.length) return Promise.resolve([]);
      return Promise.resolve(fetchFn(urls[index])).then(function (body) {
        var data = typeof body === "string" ? JSON.parse(body) : body;
        var out = [];
        ((data && data.elements) || []).forEach(function (el) {
          var record = normalizeOsmElement(el);
          if (record) out.push(record);
        });
        return out;
      }).catch(function () { return attempt(index + 1); });
    }
    return attempt(0);
  }

  return {
    KEY_CUSTOM: KEY_CUSTOM,
    KEY_EDITS: KEY_EDITS,
    KEY_DELETED: KEY_DELETED,
    loadUser: loadUser,
    myList: myList,
    searchCatalog: searchCatalog,
    parseQuery: parseQuery,
    saveResult: saveResult,
    addCustom: addCustom,
    updateEntry: updateEntry,
    deleteEntry: deleteEntry,
    isSaved: isSaved,
    normalizeOsmElement: normalizeOsmElement,
    lookupOnline: lookupOnline,
    onlineQuery: onlineQuery
  };
})();
if (typeof module !== "undefined" && module.exports) module.exports = StoreFinder;
