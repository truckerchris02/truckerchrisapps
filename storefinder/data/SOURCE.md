# Store Finder location data

Retrieved **2026-11-09**. Store numbers, street addresses, and phone numbers that were not in a source below are stored as empty strings. They are not guessed.

## United States stores

Source: OpenStreetMap features tagged `brand:wikidata=Q483551` (Walmart).

The snapshot was read from the public [QLever OSM planet](https://qlever.dev/osm-planet) SPARQL endpoint, which republishes OpenStreetMap. Rebuild with `python3 storefinder/data/build_dataset.py`.

License: **Open Database License (ODbL) 1.0**. © OpenStreetMap contributors. https://www.openstreetmap.org/copyright

Departments mapped as their own points (pharmacy, garden center, photo, vision, fuel, auto care) are not listed as stores. A store number is copied only when the OSM `ref` tag is a 1 to 5 digit number. A phone is copied only from `phone` or `contact:phone` when it contains at least seven digits. The state is the `addr:state` tag when that tag is a US state or Puerto Rico. When `addr:state` is blank, the state is the US state polygon that contains the mapped coordinate.

Counts for this snapshot are in `COUNTS.json` after the build.

## Distribution centers

Two public sources are combined. A record keeps the address from the source that supplied the street. Conflicting street numbers are kept as separate rows instead of being averaged or rewritten.

1. **OpenStreetMap (ODbL)**, same retrieval as the stores. Included when the name says distribution or fulfillment (entrances, exits, and parking rows are dropped). A DC number is copied only when `ref` or the name itself contains that number.
2. **ABFBA 2026 Walmart Warehouse Master List (Public Edition)**, retrieved 2026-11-09 from https://www.abfba.com/walmart-warehouse-master-list . That page says Walmart does not publish a full address directory and that its rows come from public local-government records, development material, or recruiting pages. It is a third-party compilation, not an official Walmart directory. Rows that say the public address is limited are omitted. That page does not list phone numbers, so those fields are blank. Regional rows that say `DC6006` and similar are stored as the digits only.

Chris can add, edit, and delete every row. His changes are not written back to these files.

## Reviewed and not used as current addresses

Thomas J. Holmes, University of Minnesota, `distribution_center_openings.csv` (posted for *The Diffusion of Wal-Mart and Economies of Density*, Econometrica 2011; file at https://users.econ.umn.edu/~holmes/data/WalMart/distribution_center_openings.csv). The file records openings through 2006. Several of those street addresses disagree with later public listings, so it is not shipped as a current list.
