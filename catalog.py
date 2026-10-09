"""Persistent catalogue and public contact settings for Racket-Go.

The SQLite database and uploads live in RACKET_GO_DATA_DIR (or ./data next
to this file). All values returned to the UI are plain Python values; the
UI must escape them when rendering HTML. This module never stores secrets.
"""

from __future__ import annotations

import math
import os
import re
import sqlite3
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
CONDITIONS = ("Neuf", "Occasion")
SHAPES = ("Ronde", "Goutte d’eau", "Diamant")
DEFAULT_SETTINGS = {
    "site_name": "Racket-Go",
    "tagline": "Votre prochaine raquette de padel",
    "description": "Découvrez les raquettes disponibles et contactez-nous pour trouver celle qui vous convient.",
    "whatsapp_number": "",
    "facebook_url": "",
    "leboncoin_url": "",
    "vinted_url": "",
}
PRODUCT_FIELDS = {
    "id", "name", "brand", "description", "price", "stock", "condition",
    "shape", "weight", "image", "is_demo", "created_at",
}


def get_data_dir() -> Path:
    """Return the configurable location of persistent data, without creating it."""
    configured = os.environ.get("RACKET_GO_DATA_DIR", "").strip()
    directory = Path(configured).expanduser() if configured else ROOT / "data"
    if not directory.is_absolute():
        directory = ROOT / directory
    return directory.resolve()


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    directory = get_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(directory / "catalog.sqlite3", timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _demo_products() -> list[dict[str, Any]]:
    descriptions = (
        "Un exemple de raquette ronde pour privilégier le contrôle et la prise en main.",
        "Un exemple de raquette polyvalente pour équilibrer contrôle et puissance.",
        "Un exemple de raquette en diamant pour un jeu offensif.",
        "Un exemple de modèle premium. Indisponible pour illustrer l’affichage du stock.",
    )
    specifications = (
        ("Contrôle", 119, 3, "Ronde", 355, "assets/racket-control.png"),
        ("Polyvalente", 159, 1, "Goutte d’eau", 365, "assets/racket-versatile.png"),
        ("Puissance", 199, 2, "Diamant", 370, "assets/racket-power.png"),
        ("Pro", 229, 0, "Diamant", 365, "assets/racket-pro.png"),
    )
    return [
        {
            "name": name,
            "brand": "Modèle de démonstration",
            "description": description,
            "price": price,
            "stock": stock,
            "condition": "Neuf",
            "shape": shape,
            "weight": weight,
            "image": image,
            "is_demo": True,
        }
        for (name, price, stock, shape, weight, image), description in zip(specifications, descriptions)
    ]


def _insert_product(connection: sqlite3.Connection, product: dict[str, Any]) -> int:
    cursor = connection.execute(
        """INSERT INTO products
        (name, brand, description, price, stock, condition, shape, weight, image, is_demo)
        VALUES (:name, :brand, :description, :price, :stock, :condition, :shape,
                :weight, :image, :is_demo)""",
        product,
    )
    return int(cursor.lastrowid)


def init_db() -> None:
    """Create the database and seed examples exactly once, even after deletions."""
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL CHECK (price >= 0),
                stock INTEGER NOT NULL CHECK (stock >= 0),
                condition TEXT NOT NULL CHECK (condition IN ('Neuf', 'Occasion')),
                shape TEXT NOT NULL CHECK (shape IN ('Ronde', 'Goutte d’eau', 'Diamant')),
                weight INTEGER NOT NULL CHECK (weight >= 0),
                image TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )"""
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            DEFAULT_SETTINGS.items(),
        )
        seeded = connection.execute(
            "SELECT value FROM metadata WHERE key = 'initial_seed_done'"
        ).fetchone()
        if seeded is None:
            # Existing catalogue rows, if any, always take priority over examples.
            if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
                for product in _demo_products():
                    _insert_product(connection, product)
            connection.execute(
                "INSERT INTO metadata (key, value) VALUES ('initial_seed_done', '1')"
            )


def _product_dict(row: sqlite3.Row) -> dict[str, Any]:
    product = dict(row)
    product["is_demo"] = bool(product["is_demo"])
    return product


def list_products() -> list[dict[str, Any]]:
    init_db()
    with _connection() as connection:
        rows = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    return [_product_dict(row) for row in rows]


def _identifier(value: Any) -> int:
    if type(value) is not int or not 0 < value <= 2**63 - 1:
        raise ValueError("L’identifiant de la raquette est invalide.")
    return value


def get_product(product_id: int) -> dict[str, Any] | None:
    product_id = _identifier(product_id)
    init_db()
    with _connection() as connection:
        row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _product_dict(row) if row is not None else None


def _text(value: Any, label: str, maximum: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} doit être du texte.")
    value = value.strip()
    if "\x00" in value or len(value) > maximum:
        raise ValueError(f"{label} doit contenir au maximum {maximum} caractères.")
    if required and not value:
        raise ValueError(f"{label} est obligatoire.")
    return value


def _nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError(f"{label} doit être un entier positif ou nul.")
    return value


def _price(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Le prix doit être un nombre positif ou nul.")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError("Le prix doit être un nombre positif ou nul.")
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError("Le prix doit avoir au maximum deux décimales.")
        result = float(amount)
        if not math.isfinite(result):
            raise ValueError("Le prix est trop élevé.")
        return result
    except (InvalidOperation, OverflowError) as error:
        raise ValueError("Le prix est invalide.") from error


def _image(value: Any) -> str:
    value = _text(value, "Le chemin de l’image", 512)
    if not value:
        return ""
    parts = PurePosixPath(value).parts
    if (
        "\\" in value
        or value.startswith("/")
        or any(part in ("", ".", "..") for part in value.split("/"))
        or len(parts) < 2
        or parts[0] not in ("assets", "uploads")
    ):
        raise ValueError("L’image doit être un chemin relatif dans assets/ ou uploads/.")
    return value


def _validated_product(product: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(product, dict):
        raise ValueError("Les données de la raquette sont invalides.")
    unknown = set(product) - PRODUCT_FIELDS
    if unknown:
        raise ValueError("Un champ de la raquette est inconnu.")
    condition = product.get("condition", "Neuf")
    shape = product.get("shape", "Ronde")
    is_demo = product.get("is_demo", False)
    if condition not in CONDITIONS:
        raise ValueError("L’état doit être Neuf ou Occasion.")
    if shape not in SHAPES:
        raise ValueError("La forme de la raquette est invalide.")
    if type(is_demo) is not bool:
        raise ValueError("Le statut de démonstration est invalide.")
    return {
        "name": _text(product.get("name", ""), "Le nom", 120, required=True),
        "brand": _text(product.get("brand", ""), "La marque", 100),
        "description": _text(product.get("description", ""), "La description", 4000),
        "price": _price(product.get("price", 0)),
        "stock": _nonnegative_integer(product.get("stock", 0), "Le stock"),
        "condition": condition,
        "shape": shape,
        "weight": _nonnegative_integer(product.get("weight", 0), "Le poids"),
        "image": _image(product.get("image", "")),
        "is_demo": is_demo,
    }


def save_product(product: dict[str, Any]) -> int:
    """Create or update a product; omitted update fields retain their old values."""
    if not isinstance(product, dict):
        raise ValueError("Les données de la raquette sont invalides.")
    product_id = product.get("id")
    if product_id is not None:
        product_id = _identifier(product_id)
    init_db()
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if product_id is None:
            validated = _validated_product(product)
            return _insert_product(connection, validated)
        row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise ValueError("Cette raquette n’existe plus.")
        validated = _validated_product({**_product_dict(row), **product})
        connection.execute(
            """UPDATE products SET name = :name, brand = :brand,
                description = :description, price = :price, stock = :stock,
                condition = :condition, shape = :shape, weight = :weight,
                image = :image, is_demo = :is_demo WHERE id = :id""",
            {**validated, "id": product_id},
        )
    return product_id


def delete_product(product_id: int) -> None:
    product_id = _identifier(product_id)
    init_db()
    with _connection() as connection:
        connection.execute("DELETE FROM products WHERE id = ?", (product_id,))


def get_settings() -> dict[str, str]:
    init_db()
    with _connection() as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()
    return {**DEFAULT_SETTINGS, **{row["key"]: row["value"] for row in rows if row["key"] in DEFAULT_SETTINGS}}


def _url(value: Any, label: str) -> str:
    value = _text(value, label, 2048)
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(character.isspace() for character in value)
        ):
            raise ValueError("invalid URL")
        # Accessing port also checks for malformed or out-of-range port numbers.
        parsed.port
    except ValueError as error:
        raise ValueError(f"{label} doit être une URL complète en https:// ou http://.") from error
    return value


def _whatsapp(value: Any) -> str:
    value = _text(value, "Le numéro WhatsApp", 40)
    if not value:
        return ""
    if not re.fullmatch(r"\+?[0-9 ()-]+", value):
        raise ValueError("Le numéro WhatsApp doit contenir un indicatif et des chiffres.")
    normalized = re.sub(r"[ ()-]", "", value).lstrip("+")
    if not re.fullmatch(r"[1-9][0-9]{5,14}", normalized):
        raise ValueError(
            "Le numéro WhatsApp doit contenir entre 6 et 15 chiffres, "
            "avec l’indicatif international et sans zéro initial."
        )
    return normalized


def save_settings(settings: dict[str, str]) -> None:
    """Validate and atomically save any subset of the public settings."""
    if not isinstance(settings, dict) or set(settings) - set(DEFAULT_SETTINGS):
        raise ValueError("Un paramètre du site est inconnu.")
    validated: dict[str, str] = {}
    for key, value in settings.items():
        if key.endswith("_url"):
            validated[key] = _url(value, "Le lien de contact")
        elif key == "whatsapp_number":
            validated[key] = _whatsapp(value)
        else:
            limits = {"site_name": 80, "tagline": 160, "description": 600}
            validated[key] = _text(value, "Le texte du site", limits[key], required=key == "site_name")
    init_db()
    with _connection() as connection:
        connection.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            validated.items(),
        )


def reset_demo() -> None:
    """Replace only demonstration products, preserving the real catalogue."""
    init_db()
    with _connection() as connection:
        connection.execute("DELETE FROM products WHERE is_demo = 1")
        for product in _demo_products():
            _insert_product(connection, product)
