"""
FastAPI application for card identification using perceptual hashing.

The API accepts a base64-encoded image, detects the most prominent card in view,
normalizes perspective, and matches it against a SQLite-backed pHash index.
"""

from __future__ import annotations

import base64
import sqlite3
from io import BytesIO
from typing import Optional, Tuple

import cv2
import imagehash
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

DATABASE_PATH = "cards.db"
HAMMING_THRESHOLD = 12


class AnalyzeRequest(BaseModel):
    image: str


def decode_image(image_data: str) -> bytes:
    try:
        return base64.b64decode(image_data, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data.") from exc


def order_points(pts: np.ndarray) -> np.ndarray:
    """Return points ordered as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    destination = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype="float32",
    )

    transform_matrix = cv2.getPerspectiveTransform(rect, destination)
    warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))
    return warped


class CardIdentifier:
    def __init__(self, db_path: str = DATABASE_PATH, distance_threshold: int = HAMMING_THRESHOLD) -> None:
        self.db_path = db_path
        self.distance_threshold = distance_threshold
        self.cards = self._load_cards()

    def _load_cards(self) -> list[Tuple[str, str, imagehash.ImageHash]]:
        connection = sqlite3.connect(self.db_path)
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
        connection.commit()
        cursor.execute("SELECT card_name, set_code, phash FROM cards")
        rows = cursor.fetchall()
        connection.close()
        return [(name, set_code, imagehash.hex_to_hash(phash)) for name, set_code, phash in rows]

    def _find_card_contour(self, edges: np.ndarray) -> Optional[np.ndarray]:
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approximation) == 4:
                return approximation.reshape(4, 2)
        return None

    def _extract_card(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 75, 200)

        contour = self._find_card_contour(edges)
        if contour is None:
            return image

        warped = four_point_transform(image, contour)
        return warped

    def _compute_phash(self, image_array: np.ndarray) -> imagehash.ImageHash:
        rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        return imagehash.phash(pil_image)

    def _query(self, phash: imagehash.ImageHash) -> Optional[dict]:
        best_match: Optional[dict] = None
        for card_name, set_code, stored_hash in self.cards:
            distance = phash - stored_hash
            if distance < self.distance_threshold:
                if best_match is None or distance < best_match["distance"]:
                    best_match = {
                        "card": card_name,
                        "set": set_code,
                        "distance": distance,
                        "confidence": self._confidence_level(distance),
                    }
        return best_match

    def _confidence_level(self, distance: int) -> str:
        if distance < 6:
            return "High"
        if distance < 10:
            return "Medium"
        return "Low"

    def identify(self, image_bytes: bytes) -> Optional[dict]:
        np_image = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=400, detail="Could not decode image bytes.")

        card_image = self._extract_card(frame)
        phash = self._compute_phash(card_image)
        return self._query(phash)


app = FastAPI(title="Aether Sight Vision API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
identifier = CardIdentifier()


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    image_bytes = decode_image(request.image)
    match = identifier.identify(image_bytes)
    if not match:
        return {"match": False}
    return {"match": True, **match}


__all__ = ["app"]
