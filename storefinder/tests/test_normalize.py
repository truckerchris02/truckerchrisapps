#!/usr/bin/env python3
"""Normalization stays blank when the source did not provide a fact."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from normalize import classify, phone_of, store_number  # noqa: E402


def locate(_lat, _lon):
    return "MO"


class NormalizeTests(unittest.TestCase):
    def test_missing_number_address_and_phone_stay_blank(self):
        record = classify({
            "catalog_key": "node/1",
            "name": "Walmart Supercenter",
            "shop": "supermarket",
            "ref": "Walmart",
            "phone": "N/A",
            "city": "Joplin",
            "state": "Missouri",
            "lat": 37.05,
            "lon": -94.51,
        }, locate)
        self.assertIsNotNone(record)
        self.assertEqual(record["storeNumber"], "")
        self.assertEqual(record["phone"], "")
        self.assertEqual(record["address"], "Joplin, MO")
        self.assertNotIn("000", record["phone"])

    def test_real_ref_and_phone_are_kept(self):
        record = classify({
            "catalog_key": "node/2",
            "name": "Walmart Supercenter",
            "shop": "supermarket",
            "ref": "59",
            "phone": "+1-417-781-0100",
            "housenumber": "1501",
            "street": "S Range Line Rd",
            "city": "Joplin",
            "state": "MO",
            "postcode": "64804",
            "lat": 37.07,
            "lon": -94.47,
        }, locate)
        self.assertEqual(record["storeNumber"], "59")
        self.assertEqual(record["phone"], "+1-417-781-0100")
        self.assertEqual(record["zip"], "64804")
        self.assertEqual(record["address"], "1501 S Range Line Rd, Joplin, MO 64804")

    def test_pharmacy_is_not_a_store(self):
        self.assertIsNone(classify({
            "name": "Walmart Pharmacy",
            "shop": "pharmacy",
            "city": "Joplin",
            "state": "MO",
            "lat": 37.0,
            "lon": -94.5,
        }, locate))

    def test_outside_the_us_is_dropped(self):
        self.assertIsNone(classify({
            "name": "Walmart",
            "shop": "supermarket",
            "city": "Toronto",
            "state": "ON",
            "country": "CA",
            "lat": 43.7,
            "lon": -79.4,
        }, lambda *_: ""))

    def test_distribution_number_comes_only_from_the_name(self):
        record = classify({
            "catalog_key": "way/9",
            "name": "Walmart Distribution Center #6073",
            "city": "Pageland",
            "state": "SC",
            "lat": 34.7,
            "lon": -80.4,
        }, lambda *_: "")
        self.assertEqual(record["type"], "DC")
        self.assertEqual(record["storeNumber"], "6073")
        self.assertEqual(record["phone"], "")

    def test_helpers_do_not_invent(self):
        self.assertEqual(store_number("Store 12 extra"), "")
        self.assertEqual(store_number("#12"), "12")
        self.assertEqual(phone_of("none"), "")
        self.assertEqual(phone_of("1234"), "")


if __name__ == "__main__":
    unittest.main()
