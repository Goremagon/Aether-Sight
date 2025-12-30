"""Application entrypoint for real-time Magic card recognition."""

import sqlite3
from typing import Dict, Optional, Tuple

import cv2
import imagehash
import numpy as np
from PIL import Image

from vision_engine import CardDetector


def load_hashes(db_path: str) -> Dict[str, imagehash.ImageHash]:
    """Load card hashes from SQLite into memory for fast lookup."""
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS cards (name TEXT PRIMARY KEY, hash TEXT)")
    cursor.execute("SELECT name, hash FROM cards")
    hashes = {name: imagehash.hex_to_hash(hash_value) for name, hash_value in cursor.fetchall()}
    connection.close()
    return hashes


def find_best_match(
    query_hash: imagehash.ImageHash, stored: Dict[str, imagehash.ImageHash], threshold: int
) -> Tuple[Optional[str], Optional[int]]:
    """Find the closest hash match below the given Hamming distance threshold."""
    best_name = None
    best_distance = None
    for name, stored_hash in stored.items():
        distance = query_hash - stored_hash
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_name = name
    if best_distance is not None and best_distance < threshold:
        return best_name, best_distance
    return None, None


def draw_annotation(
    frame: np.ndarray, contour: np.ndarray, name: str, distance: int, threshold: int
) -> None:
    """Draw the detected contour and annotation text on the frame."""
    cv2.polylines(frame, [contour], True, (0, 255, 0), 2)
    confidence = max(0.0, 1.0 - distance / max(threshold, 1))
    text = f"{name} (score: {confidence:.2f})"
    x, y = contour.reshape(-1, 2).min(axis=0)
    cv2.putText(frame, text, (int(x), int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


def main() -> None:
    """Run the real-time recognition loop."""
    detector = CardDetector()
    hashes = load_hashes("cards.db")
    if not hashes:
        print("No card hashes found. Run indexer.py to build the database first.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Unable to access webcam.")
        return

    threshold = 10
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            contour = detector.detect_card(frame)
            if contour is not None:
                warped = detector.get_warp(frame, contour)
                if warped is not None:
                    pil_image = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
                    query_hash = imagehash.phash(pil_image)
                    name, distance = find_best_match(query_hash, hashes, threshold)
                    if name and distance is not None:
                        draw_annotation(frame, contour, name, distance, threshold)

            cv2.imshow("Aether Sight", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
