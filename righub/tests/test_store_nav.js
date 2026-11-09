"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const stores = path.join(__dirname, "..", "android", "assets", "stores");

function load(names) {
  const sandbox = {};
  for (const name of names) {
    vm.runInNewContext(fs.readFileSync(path.join(stores, name), "utf8"), sandbox, { filename: name });
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

function fakeNav() {
  return {
    tab: "stores",
    calls: [],
    setDestination(lat, lng, name) {
      this.tab = "nav";
      this.calls.push({ mode: "point", lat: lat, lng: lng, name: name });
    },
    geocodeDestination(query, name) {
      this.tab = "nav";
      this.calls.push({ mode: "address", query: query, name: name });
    }
  };
}

const bundled = load(["us-stores.js", "dcs.js", "app.js", "navlink.js"]);
const { US_STORES, DC_SEED, StoreFinder, RigHubStoreNav } = bundled;
const catalog = US_STORES.concat(DC_SEED);

test("Walmart 59 hands the mapped store to Rig Nav", () => {
  const hits = RigHubStoreNav.catalogHits(catalog, "Walmart 59", StoreFinder.searchCatalog);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].storeNumber, "59");
  assert.equal(hits[0].city, "Joplin");
  const hop = RigHubStoreNav.handoff(hits[0]);
  assert.equal(hop.ok, true);
  assert.equal(hop.mode, "point");
  assert.equal(hop.tab, "nav");
  assert.equal(hop.destination.lat, 37.07283);
  assert.equal(hop.destination.lng, -94.47296);
  assert.match(hop.destination.name, /Joplin/);
  assert.match(hop.destination.name, /1501 South Range Line Road/);
  const nav = fakeNav();
  RigHubStoreNav.applyToNav(nav, hits[0]);
  assert.equal(nav.tab, "nav");
  assert.equal(nav.calls.length, 1);
  assert.equal(nav.calls[0].mode, "point");
  assert.equal(nav.calls[0].lat, hop.destination.lat);
  assert.equal(nav.calls[0].lng, hop.destination.lng);
  assert.equal(nav.calls[0].name, hop.destination.name);
});

test("DC 6006 is found and sent to Rig Nav by address when the list has no coordinate", () => {
  const hits = RigHubStoreNav.catalogHits(catalog, "DC 6006", StoreFinder.searchCatalog);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].type, "DC");
  assert.equal(hits[0].storeNumber, "6006");
  assert.equal(hits[0].city, "Cullman");
  const hop = RigHubStoreNav.handoff(hits[0]);
  assert.equal(hop.ok, true);
  assert.equal(hop.mode, "address");
  assert.equal(hop.tab, "nav");
  assert.match(hop.destination.address, /Cullman, AL 35055/);
  assert.match(hop.destination.name, /6006/);
  const nav = fakeNav();
  RigHubStoreNav.applyToNav(nav, hits[0]);
  assert.equal(nav.tab, "nav");
  assert.equal(nav.calls[0].mode, "address");
  assert.equal(nav.calls[0].query, hits[0].address);
  assert.equal(nav.calls[0].name, hop.destination.name);
});

test("a mapped distribution center uses lat/lon", () => {
  const hits = RigHubStoreNav.catalogHits(catalog, "DC 6095", StoreFinder.searchCatalog);
  assert.ok(hits.length >= 1);
  assert.equal(hits[0].type, "DC");
  const nav = fakeNav();
  const hop = RigHubStoreNav.applyToNav(nav, hits[0]);
  assert.equal(hop.mode, "point");
  assert.equal(nav.calls[0].lat, Number(hits[0].lat));
  assert.equal(nav.calls[0].lng, Number(hits[0].lon));
  assert.match(nav.calls[0].name, /6095|Distribution/);
});

test("a saved store without coordinates borrows the bundled map point", () => {
  const saved = {
    id: 49,
    name: "Joplin S Range Line Rd Supercenter",
    type: "Supercenter",
    storeNumber: "59",
    address: "1501 S Range Line Rd, Joplin, MO, 64804",
    city: "Joplin",
    state: "MO"
  };
  const place = RigHubStoreNav.enrich(saved, catalog);
  const nav = fakeNav();
  const hop = RigHubStoreNav.applyToNav(nav, place);
  assert.equal(hop.mode, "point");
  assert.equal(nav.tab, "nav");
  assert.equal(nav.calls[0].lat, 37.07283);
  assert.equal(nav.calls[0].lng, -94.47296);
  assert.match(nav.calls[0].name, /Joplin S Range Line Rd Supercenter/);
  assert.match(nav.calls[0].name, /1501 S Range Line Rd/);
});

test("hub saves use namespaced keys and still hand off after reload", () => {
  const storage = memory();
  const found = RigHubStoreNav.catalogHits(catalog, "Walmart 59", StoreFinder.searchCatalog)[0];
  const saved = StoreFinder.saveResult(storage, found, []);
  assert.deepEqual(Object.keys(storage.dump()).sort(), ["righub_stores_custom"]);
  assert.equal(Object.prototype.hasOwnProperty.call(storage.dump(), "wsf_custom"), false);
  const again = memory(storage.dump());
  const list = StoreFinder.myList([], [], StoreFinder.loadUser(again));
  assert.equal(list.length, 1);
  assert.equal(list[0].id, saved.id);
  const nav = fakeNav();
  RigHubStoreNav.applyToNav(nav, list[0]);
  assert.equal(nav.tab, "nav");
  assert.equal(nav.calls[0].mode, "point");
  assert.equal(nav.calls[0].lat, 37.07283);
  const custom = StoreFinder.addCustom(storage, {
    name: "Yard DC",
    type: "DC",
    storeNumber: "7001",
    address: "1 Gate Rd, Tulsa, OK 74107",
    city: "Tulsa",
    state: "OK",
    gateNotes: "dock 3",
    lat: "36.131",
    lon: "-95.937"
  });
  const nav2 = fakeNav();
  const hop = RigHubStoreNav.applyToNav(nav2, custom);
  assert.equal(hop.mode, "point");
  assert.equal(nav2.calls[0].lat, 36.131);
  assert.equal(nav2.calls[0].lng, -95.937);
  assert.match(nav2.calls[0].name, /Yard DC/);
  assert.match(nav2.calls[0].name, /1 Gate Rd/);
});
