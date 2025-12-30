"""
Indexer script for building a perceptual hash database of Magic: The Gathering cards.

This utility downloads Scryfall's "Unique Artwork" bulk JSON, computes a pHash for
card artwork, and stores the results in a SQLite database. It defaults to processing
the first 100 entries for quick iteration but can scale to the entire dataset by
adjusting the `--limit` flag.
"""

from __future__ import annotations

import argparse
import sqlite3
from io import BytesIO
from typing import Iterable, Optional

import imagehash
import requests
from PIL import Image
from tqdm import tqdm

BULK_METADATA_URL = "https://api.scryfall.com/bulk-data/unique-artwork"
DEFAULT_DB_PATH = "cards.db"


def fetch_bulk_download_url() -> str:
    """Retrieve the download URI for the Unique Artwork bulk JSON."""
    response = requests.get(BULK_METADATA_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    download_uri = data.get("download_uri")
    if not download_uri:
        raise RuntimeError("Failed to locate download_uri in Scryfall bulk metadata.")
    return download_uri


def download_bulk_cards(download_uri: str) -> list[dict]:
    """Download the full Unique Artwork JSON."""
    response = requests.get(download_uri, timeout=120)
    response.raise_for_status()
    return response.json()


def ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the cards table if it does not exist."""
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            set_code TEXT NOT NULL,
            phash TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_name_set
        ON cards(card_name, set_code)
        """
    )
    connection.commit()


def extract_image_url(card: dict) -> Optional[str]:
    """Return the best available image URL for the given card record."""
    image_uris = card.get("image_uris") or {}
    if image_uris:
        return image_uris.get("large") or image_uris.get("normal") or image_uris.get("png")

    # Double-faced or modal cards store images on the faces.
    faces = card.get("card_faces") or []
    for face in faces:
        face_uris = face.get("image_uris") or {}
        if face_uris:
            return face_uris.get("large") or face_uris.get("normal") or face_uris.get("png")
    return None


def compute_phash(image_bytes: bytes) -> str:
    """Compute the perceptual hash string for the given image bytes."""
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    return str(imagehash.phash(image))


def iter_cards(cards: list[dict], limit: Optional[int]) -> Iterable[dict]:
    """Yield cards up to the specified limit."""
    if limit is None:
        yield from cards
        return

    for card in cards[:limit]:
        yield card


def index_cards(db_path: str, limit: Optional[int] = 100) -> None:
    """Main indexing routine."""
    print("Fetching bulk metadata from Scryfall…")
    download_uri = fetch_bulk_download_url()
    print("Downloading Unique Artwork JSON…")
    cards = download_bulk_cards(download_uri)

    connection = sqlite3.connect(db_path)
    ensure_schema(connection)
    cursor = connection.cursor()

    processed = 0
    for card in tqdm(iter_cards(cards, limit), desc="Indexing cards"):
        image_url = extract_image_url(card)
        if not image_url:
            continue

        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()

        phash = compute_phash(image_response.content)
        cursor.execute(
            """
            INSERT OR REPLACE INTO cards(card_name, set_code, phash)
            VALUES (?, ?, ?)
            """,
            (card.get("name", "Unknown"), card.get("set", ""), phash),
        )
        processed += 1

    connection.commit()
    connection.close()
    print(f"Indexed {processed} cards into {db_path}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a pHash index for card images.")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database to create/update (default: cards.db)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of cards to process (default: 100). Use a higher value to index all cards.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_cards(db_path=args.db_path, limit=args.limit)


if __name__ == "__main__":
    main()
