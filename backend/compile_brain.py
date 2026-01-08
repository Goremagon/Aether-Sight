"""
Compile the Host Engine brain with ORB descriptors, HSV histograms, and semantic hooks.
"""

from __future__ import annotations

import argparse
import pickle
import time
from typing import Optional

import cv2
import imagehash
import numpy as np
import requests
from PIL import Image
from tqdm import tqdm

N_FEATURES = 2000
BULK_METADATA_URL = "https://api.scryfall.com/bulk-data/unique-artwork"
BRAIN_PATH = "brain.pkl"


def log_server(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SERVER] {timestamp} {message}")


def get_center_crop(image: np.ndarray, crop_ratio: float = 0.5) -> np.ndarray:
    height, width = image.shape[:2]
    crop_width = int(width * crop_ratio)
    crop_height = int(height * crop_ratio)
    start_x = (width - crop_width) // 2
    start_y = (height - crop_height) // 2
    return image[start_y : start_y + crop_height, start_x : start_x + crop_width]


def fetch_bulk_download_url() -> str:
    response = requests.get(BULK_METADATA_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    download_uri = data.get("download_uri")
    if not download_uri:
        raise RuntimeError("Failed to locate download_uri in Scryfall bulk metadata.")
    return download_uri


def download_bulk_cards(download_uri: str) -> list[dict]:
    response = requests.get(download_uri, timeout=120)
    response.raise_for_status()
    return response.json()


def extract_image_url(card: dict) -> Optional[str]:
    image_uris = card.get("image_uris") or {}
    if image_uris:
        return image_uris.get("large") or image_uris.get("normal") or image_uris.get("png")

    faces = card.get("card_faces") or []
    for face in faces:
        face_uris = face.get("image_uris") or {}
        if face_uris:
            return face_uris.get("large") or face_uris.get("normal") or face_uris.get("png")
    return None


def compute_hsv_histogram(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 12, 3], [0, 180, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist.astype(np.float32)


def compute_phash(image: np.ndarray) -> str:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    return str(imagehash.phash(pil_image))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile the Host Engine brain.")
    parser.add_argument("--output", default=BRAIN_PATH, help="Output brain file name.")
    parser.add_argument("--limit", type=int, default=100, help="Limit cards for testing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_server("Fetching bulk metadata from Scryfall")
    download_uri = fetch_bulk_download_url()
    log_server("Downloading Unique Artwork JSON")
    cards = download_bulk_cards(download_uri)

    orb = cv2.ORB_create(nfeatures=N_FEATURES)
    descriptors: list[np.ndarray] = []
    descriptor_card_index: list[int] = []
    card_names: list[str] = []
    set_codes: list[str] = []
    card_hsv_hist: list[np.ndarray] = []
    card_phash: list[str] = []
    oracle_texts: list[str] = []
    mana_costs: list[str] = []
    card_image_urls: list[str] = []

    log_server("Extracting features")
    for card in tqdm(cards[: args.limit], desc="Compiling brain"):
        image_url = extract_image_url(card)
        if not image_url:
            continue

        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()
        image_array = np.frombuffer(image_response.content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            continue

        cropped = get_center_crop(image, 0.5)
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        keypoints, desc = orb.detectAndCompute(gray, None)
        if desc is None or len(keypoints) == 0:
            continue

        card_index = len(card_names)
        card_names.append(card.get("name", "Unknown"))
        set_codes.append(card.get("set", ""))
        oracle_texts.append(card.get("oracle_text", ""))
        mana_costs.append(card.get("mana_cost", ""))
        card_image_urls.append(image_url)
        card_hsv_hist.append(compute_hsv_histogram(cropped))
        card_phash.append(compute_phash(cropped))

        for row in desc:
            descriptors.append(row)
            descriptor_card_index.append(card_index)

    if not descriptors:
        raise RuntimeError("No descriptors compiled; cannot write brain file.")

    brain = {
        "descriptors": np.vstack(descriptors).astype(np.uint8),
        "descriptor_card_index": np.array(descriptor_card_index, dtype=np.int32),
        "card_names": card_names,
        "set_codes": set_codes,
        "card_hsv_hist": np.vstack(card_hsv_hist).astype(np.float32),
        "card_phash": card_phash,
        "oracle_texts": oracle_texts,
        "mana_costs": mana_costs,
        "card_image_urls": card_image_urls,
    }

    with open(args.output, "wb") as handle:
        pickle.dump(brain, handle)
    log_server(
        f"Brain compiled: {args.output} ({len(card_names)} cards, {len(descriptors)} descriptors)"
    )


if __name__ == "__main__":
    main()
