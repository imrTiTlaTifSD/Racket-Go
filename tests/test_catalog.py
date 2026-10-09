"""Behavioural checks for catalogue persistence and public input validation."""

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"RACKET_GO_DATA_DIR": self.directory.name})
        self.environment.start()
        catalog.init_db()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def new_product(self, **overrides):
        return {
            "name": "Une vraie raquette",
            "brand": "Ma marque",
            "description": "Une description avec apostrophe : l’équilibre.",
            "price": 129.90,
            "stock": 2,
            "condition": "Occasion",
            "shape": "Goutte d’eau",
            "weight": 360,
            "image": "uploads/example.png",
            "is_demo": False,
            **overrides,
        }

    def test_initial_examples_and_settings_are_seeded_only_once(self):
        products = catalog.list_products()
        self.assertEqual(len(products), 4)
        self.assertEqual([item["name"] for item in products], ["Contrôle", "Polyvalente", "Puissance", "Pro"])
        self.assertEqual([item["price"] for item in products], [119, 159, 199, 229])
        self.assertEqual([item["stock"] for item in products], [3, 1, 2, 0])
        self.assertTrue(all(item["is_demo"] is True for item in products))
        self.assertEqual(catalog.get_settings(), catalog.DEFAULT_SETTINGS)
        catalog.init_db()
        self.assertEqual(len(catalog.list_products()), 4)
        for product in products:
            catalog.delete_product(product["id"])
        catalog.init_db()
        self.assertEqual(catalog.list_products(), [])

    def test_create_edit_delete_and_persistence_after_module_reload(self):
        product_id = catalog.save_product(self.new_product())
        original = catalog.get_product(product_id)
        self.assertEqual(original["price"], 129.90)
        self.assertEqual(original["description"], self.new_product()["description"])
        self.assertTrue(original["created_at"].endswith("Z"))
        self.assertEqual(catalog.save_product({"id": product_id, "stock": 0}), product_id)
        edited = catalog.get_product(product_id)
        self.assertEqual(edited["stock"], 0)
        self.assertEqual(edited["image"], original["image"])
        self.assertEqual(edited["created_at"], original["created_at"])
        importlib.reload(catalog)
        self.assertEqual(catalog.get_product(product_id), edited)
        catalog.delete_product(product_id)
        self.assertIsNone(catalog.get_product(product_id))

    def test_invalid_products_never_change_existing_data(self):
        invalid_values = (
            {"price": float("nan")}, {"price": float("inf")}, {"price": -1},
            {"price": True}, {"price": 1.001}, {"stock": True}, {"stock": 1.5},
            {"stock": -1}, {"weight": -1}, {"condition": "Comme neuf"},
            {"shape": "Inconnue"}, {"name": " "}, {"name": "x" * 121},
            {"description": "x" * 4001}, {"is_demo": 1}, {"secret": "do not store"},
        )
        product_id = catalog.save_product(self.new_product())
        before = catalog.get_product(product_id)
        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(ValueError):
                catalog.save_product({"id": product_id, **values})
            self.assertEqual(catalog.get_product(product_id), before)

    def test_images_must_stay_in_supported_relative_directories(self):
        for path in ("../secret.png", "uploads/../secret.png", "/tmp/photo.png", "uploads\\photo.png", "https://example.com/photo.png", "assets//photo.png", "uploads/./photo.png"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                catalog.save_product(self.new_product(image=path))
        product_id = catalog.save_product(self.new_product(image="assets/nested/photo.png"))
        self.assertEqual(catalog.get_product(product_id)["image"], "assets/nested/photo.png")

    def test_contact_settings_normalize_phone_and_persist(self):
        catalog.save_settings({"whatsapp_number": "+33 6 12 34 56 78", "facebook_url": "https://facebook.com/myshop", "site_name": "Mon padel"})
        importlib.reload(catalog)
        settings = catalog.get_settings()
        self.assertEqual(settings["whatsapp_number"], "33612345678")
        self.assertEqual(settings["facebook_url"], "https://facebook.com/myshop")
        self.assertEqual(settings["site_name"], "Mon padel")
        self.assertEqual(settings["tagline"], catalog.DEFAULT_SETTINGS["tagline"])
        catalog.save_settings({"whatsapp_number": "", "facebook_url": ""})
        self.assertEqual(catalog.get_settings()["whatsapp_number"], "")

    def test_invalid_settings_are_rejected_atomically(self):
        invalid_values = (
            {"facebook_url": "javascript:alert(1)"}, {"facebook_url": "//facebook.com"},
            {"vinted_url": "ftp://example.com"}, {"leboncoin_url": "https://example.com\n/script"},
            {"facebook_url": "https://user:password@example.com"},
            {"facebook_url": "https://example.com:99999"},
            {"whatsapp_number": "+33 letters"}, {"whatsapp_number": "123"},
            {"site_name": " "}, {"admin_password": "secret"},
        )
        before = catalog.get_settings()
        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(ValueError):
                catalog.save_settings({"tagline": "Must not be saved", **values})
            self.assertEqual(catalog.get_settings(), before)

    def test_whatsapp_rejects_local_numbers_without_country_code(self):
        before = catalog.get_settings()
        for number in ("0612345678", "06 12 34 56 78", "0033 6 12 34 56 78"):
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, "indicatif international"):
                catalog.save_settings({"whatsapp_number": number})
            self.assertEqual(catalog.get_settings(), before)

    def test_unknown_or_invalid_identifiers_cannot_update_products(self):
        for product_id in (False, -1, 0, "1"):
            with self.subTest(product_id=product_id), self.assertRaises(ValueError):
                catalog.get_product(product_id)
        with self.assertRaises(ValueError):
            catalog.save_product(self.new_product(id=999999))
        self.assertIsNone(catalog.get_product(999999))

    def test_configurable_directory_and_reset_preserve_real_products(self):
        self.assertEqual(catalog.get_data_dir(), Path(self.directory.name).resolve())
        self.assertTrue((catalog.get_data_dir() / "catalog.sqlite3").is_file())
        product_id = catalog.save_product(self.new_product())
        catalog.reset_demo()
        self.assertEqual(len(catalog.list_products()), 5)
        self.assertFalse(catalog.get_product(product_id)["is_demo"])


if __name__ == "__main__":
    unittest.main()
