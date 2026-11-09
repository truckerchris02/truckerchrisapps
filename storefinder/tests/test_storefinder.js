"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const www = path.join(__dirname, "..", "www");

function loadScripts() {
  const sandbox = {};
  for (const name of ["stores.js", "app.js"]) {
    vm.runInNewContext(fs.readFileSync(path.join(www, name), "utf8"), sandbox, { filename: name });
  }
  return sandbox;
}

function memory(initial) {
  const data = Object.assign({}, initial || {});
  return {
    getItem(key) { return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null; },
    setItem(key, value) { data[key] = String(value); },
    dump() { return JSON.parse(JSON.stringify(data)); }
  };
}

const catalog = [
  { catalogKey: "node/59", name: "Joplin Supercenter", type: "Supercenter", storeNumber: "59", city: "Joplin", state: "MO", zip: "64804", address: "1501 S Range Line Rd, Joplin, MO 64804", phone: "417-781-0100" },
  { catalogKey: "node/159", name: "Other Supercenter", type: "Supercenter", storeNumber: "159", city: "Springfield", state: "MO", zip: "65804", address: "100 Main St, Springfield, MO 65804", phone: "" },
  { catalogKey: "node/1", name: "Bentonville Supercenter", type: "Supercenter", storeNumber: "100", city: "Bentonville", state: "AR", zip: "72712", address: "406 S Walton Blvd, Bentonville, AR 72712", phone: "" },
  { catalogKey: "dc/6006", name: "Cullman DC", type: "DC", storeNumber: "6006", city: "Cullman", state: "AL", zip: "35055", address: "2200 7th Ave SW, Cullman, AL 35055", phone: "" }
];

test("search by store number is exact", () => {
  const { StoreFinder } = loadScripts();
  const numbers = (rows) => Array.from(rows, (hit) => hit.storeNumber).join(",");
  const cities = (rows) => Array.from(rows, (hit) => hit.city).join(",");
  assert.equal(numbers(StoreFinder.searchCatalog(catalog, "59")), "59");
  assert.equal(numbers(StoreFinder.searchCatalog(catalog, "#59")), "59");
  assert.equal(cities(StoreFinder.searchCatalog(catalog, "store 59")), "Joplin");
});

test("search by city, state, and ZIP", () => {
  const { StoreFinder } = loadScripts();
  assert.equal(StoreFinder.searchCatalog(catalog, "Joplin")[0].storeNumber, "59");
  assert.equal(StoreFinder.searchCatalog(catalog, "Joplin, MO")[0].zip, "64804");
  assert.equal(StoreFinder.searchCatalog(catalog, "Joplin MO")[0].city, "Joplin");
  assert.equal(StoreFinder.searchCatalog(catalog, "64804")[0].city, "Joplin");
  assert.equal(StoreFinder.searchCatalog(catalog, "Missouri").length, 2);
  assert.equal(StoreFinder.searchCatalog(catalog, "AR")[0].city, "Bentonville");
  assert.equal(StoreFinder.searchCatalog(catalog, "Cullman")[0].type, "DC");
  assert.equal(StoreFinder.searchCatalog(catalog, "72712")[0].state, "AR");
});

test("unknown phone and number stay blank on an online element", async () => {
  const { StoreFinder } = loadScripts();
  const body = JSON.stringify({ elements: [
    { type: "node", id: 9, lat: 37.08, lon: -94.5, tags: { name: "Walmart Supercenter", shop: "supermarket", "addr:city": "Carthage", "addr:state": "MO" } },
    { type: "node", id: 10, tags: { name: "Walmart Pharmacy", shop: "pharmacy", "addr:city": "Carthage", "addr:state": "MO", phone: "417-555-0100", ref: "999" } }
  ]});
  const rows = await StoreFinder.lookupOnline("Carthage, MO", () => body);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].storeNumber, "");
  assert.equal(rows[0].phone, "");
  assert.equal(rows[0].city, "Carthage");
  assert.equal(rows[0].address, "Carthage, MO");
});

test("one-tap save persists and does not duplicate", () => {
  const { StoreFinder } = loadScripts();
  const storage = memory();
  const saved = StoreFinder.saveResult(storage, catalog[0], []);
  assert.equal(saved.storeNumber, "59");
  assert.equal(saved.metroArea, "Saved");
  assert.ok(saved.id >= 100000);
  const again = StoreFinder.saveResult(storage, catalog[0], StoreFinder.myList([], [], StoreFinder.loadUser(storage)));
  assert.equal(again.id, saved.id);
  const reloaded = memory(storage.dump());
  const list = StoreFinder.myList([], [], StoreFinder.loadUser(reloaded));
  assert.equal(list.length, 1);
  assert.equal(list[0].phone, "417-781-0100");
  assert.deepEqual(Object.keys(reloaded.dump()).sort(), ["wsf_custom"]);
});

test("add a custom DC and keep it after reload", () => {
  const { StoreFinder } = loadScripts();
  const storage = memory();
  const added = StoreFinder.addCustom(storage, {
    name: "Yard DC",
    type: "DC",
    storeNumber: "6006",
    address: "2200 7th Ave SW, Cullman, AL 35055",
    city: "Cullman",
    state: "AL",
    zip: "35055",
    phone: "",
    gateNotes: "dock 3, driver parking on the west side",
    notes: "receiving 06:00"
  });
  assert.equal(added.type, "DC");
  assert.equal(added.gateNotes, "dock 3, driver parking on the west side");
  const reloaded = memory(storage.dump());
  const list = StoreFinder.myList([], [], StoreFinder.loadUser(reloaded));
  assert.equal(list.length, 1);
  assert.equal(list[0].name, "Yard DC");
  assert.equal(list[0].phone, "");
  StoreFinder.updateEntry(reloaded, added.id, { gateNotes: "dock 4" });
  const afterEdit = memory(reloaded.dump());
  assert.equal(StoreFinder.loadUser(afterEdit).custom[0].gateNotes, "dock 4");
  StoreFinder.deleteEntry(afterEdit, added.id);
  assert.equal(StoreFinder.myList([], [], StoreFinder.loadUser(afterEdit)).length, 0);
});

test("v1.1.8 saved stores, edits, and deletions migrate", () => {
  const { StoreFinder, STORES_SEED } = loadScripts();
  const target = STORES_SEED.find((store) => store.id === 49);
  const removed = STORES_SEED.find((store) => store.id === 50);
  assert.ok(target && removed);
  const storage = memory({
    wsf_custom: JSON.stringify([{
      id: 100000, name: "My Yard", type: "Supercenter", storeNumber: "9999",
      address: "1 Main", city: "Joplin", county: "Jasper", phone: "417-555-0199",
      metroArea: "Joplin Metro", officialUrl: "", notes: "gate 4", sourceNote: "Added by you"
    }]),
    wsf_edits: JSON.stringify({ "49": { name: "Joplin Renamed", notes: "call first" } }),
    wsf_deleted: JSON.stringify([50])
  });
  const list = StoreFinder.myList(STORES_SEED, [], StoreFinder.loadUser(storage));
  const edited = list.find((store) => store.id === 49);
  assert.equal(edited.name, "Joplin Renamed");
  assert.equal(edited.notes, "call first");
  assert.equal(edited.storeNumber, target.storeNumber);
  assert.equal(edited.address, target.address);
  assert.equal(list.find((store) => store.id === 50), undefined);
  const custom = list.find((store) => store.id === 100000);
  assert.equal(custom.notes, "gate 4");
  assert.equal(custom.phone, "417-555-0199");
  assert.equal(list.length, STORES_SEED.length - 1 + 1);
  StoreFinder.addCustom(storage, { name: "Extra", type: "Other", storeNumber: "", phone: "" });
  const keys = Object.keys(storage.dump()).sort();
  assert.deepEqual(keys, ["wsf_custom", "wsf_deleted", "wsf_edits"]);
});

test("bundled US list and DC starter list are searchable and do not invent phones", () => {
  const sandbox = {};
  for (const name of ["us-stores.js", "dcs.js", "app.js"]) {
    vm.runInNewContext(fs.readFileSync(path.join(www, name), "utf8"), sandbox, { filename: name });
  }
  const { US_STORES, DC_SEED, StoreFinder } = sandbox;
  assert.ok(US_STORES.length > 1000, "expected a nationwide offline list, got " + US_STORES.length);
  assert.ok(DC_SEED.length >= 10, "expected a DC starter list, got " + DC_SEED.length);
  for (const record of US_STORES.concat(DC_SEED)) {
    assert.match(record.storeNumber || "", /^$|^\d{1,5}$/);
    assert.match(record.zip || "", /^$|^\d{5}$/);
    assert.match(record.state || "", /^$|^[A-Z]{2}$/);
    assert.equal((record.phone || "").toLowerCase().includes("n/a"), false);
    assert.equal((record.phone || "").toLowerCase().includes("unknown"), false);
    if (record.phone) assert.ok(record.phone.replace(/\D/g, "").length >= 7);
    assert.ok(record.source);
  }
  const withZip = US_STORES.find((store) => store.zip && store.city);
  const byZip = StoreFinder.searchCatalog(US_STORES, withZip.zip);
  assert.ok(byZip.some((store) => store.catalogKey === withZip.catalogKey));
  const numbered = US_STORES.find((store) => store.storeNumber);
  const byNumber = StoreFinder.searchCatalog(US_STORES, numbered.storeNumber);
  assert.ok(byNumber.every((store) => store.storeNumber === numbered.storeNumber));
  assert.ok(DC_SEED.every((dc) => dc.type === "DC" && dc.id >= 1000 && dc.id < 100000));
  assert.ok(DC_SEED.some((dc) => /OpenStreetMap|ABFBA/.test(dc.sourceNote || dc.source || "")));
});
