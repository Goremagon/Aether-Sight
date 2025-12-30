"""Tools for building a local Magic: The Gathering card hash database."""

import sqlite3
from io import BytesIO
from typing import Iterable, Optional

import requests
from PIL import Image
from imagehash import phash
from tqdm import tqdm


SCRYFALL_BULK_ENDPOINT = "https://api.scryfall.com/bulk-data"


def download_scryfall_data(timeout: int = 15) -> list[dict]:
    """Fetch the Scryfall \"Unique Artwork\" bulk JSON payload.

    Args:
        timeout: Number of seconds to wait for network responses.

    Returns:
        A list of card JSON objects containing image URIs and metadata.

    Raises:
        RuntimeError: If the desired bulk data cannot be located.
        requests.RequestException: When the HTTP request fails.
    """
    response = requests.get(SCRYFALL_BULK_ENDPOINT, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    for entry in payload.get("data", []):
        if entry.get("type") == "unique_artwork":
            download_uri = entry["download_uri"]
            break
    else:
        raise RuntimeError("Unique artwork bulk data not found from Scryfall.")

    download_response = requests.get(download_uri, timeout=timeout)
    download_response.raise_for_status()
    return download_response.json()


def _get_image_uri(card: dict) -> Optional[str]:
    """Extract a low-resolution image URI from a Scryfall card record."""
    if "image_uris" in card:
        return card["image_uris"].get("small") or card["image_uris"].get("normal")
    faces = card.get("card_faces", [])
    if faces:
        face = faces[0]
        if "image_uris" in face:
            return face["image_uris"].get("small") or face["image_uris"].get("normal")
    return None


def _iter_cards(cards: list[dict]) -> Iterable[dict]:
    """Yield cards that contain an accessible image URI."""
    for card in cards:
        uri = _get_image_uri(card)
        if uri:
            card_copy = dict(card)
            card_copy["selected_image"] = uri
            yield card_copy


def process_images(db_path: str = "cards.db", timeout: int = 15) -> None:
    """Download card images, compute pHashes, and store them in SQLite.

    The database uses a simple schema mapping card names to their perceptual
    hashes. Existing rows are replaced to keep the database up to date.

    Args:
        db_path: Path to the SQLite database file to create or update.
        timeout: Number of seconds to wait for network responses.
    """
    cards = download_scryfall_data(timeout=timeout)
    filtered_cards = list(_iter_cards(cards))
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            name TEXT PRIMARY KEY,
            hash TEXT NOT NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON cards(hash)")

    for card in tqdm(filtered_cards, desc="Indexing cards", unit="card"):
        try:
            image_response = requests.get(card["selected_image"], timeout=timeout)
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content)).convert("RGB")
            hash_value = phash(image)
            cursor.execute(
                "INSERT OR REPLACE INTO cards (name, hash) VALUES (?, ?)",
                (card.get("name", "Unknown"), str(hash_value)),
            )
        except requests.Timeout:
            tqdm.write(f"Timeout fetching image for {card.get('name', 'Unknown')}.")
            continue
        except requests.RequestException as exc:
            tqdm.write(
                f"Network error for {card.get('name', 'Unknown')}: {exc}"
            )
            continue
        except OSError as exc:
            tqdm.write(f"Image processing error for {card.get('name', 'Unknown')}: {exc}")
            continue
    connection.commit()
    connection.close()
