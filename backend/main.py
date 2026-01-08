"""
Host Engine vision API with HSV-first filtering and FLANN ORB matching.
"""

from __future__ import annotations

import argparse
import base64
import os
import pickle
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

N_FEATURES = 2000
MIN_MATCHES = 25
COLOR_THRESHOLD = 0.15
TOP_CANDIDATES = 500
BRAIN_PATH = "brain.pkl"
COLLECTION_DB = "user_collection.db"
BRAIN_DOWNLOAD_URL = "https://example.com/mtg/brain.pkl"


class AnalyzeRequest(BaseModel):
    image: str
    mode: str = "play"


class LoadDeckRequest(BaseModel):
    decklist: str


def log_server(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SERVER] {timestamp} {message}")


def log_client(message: str) -> None:
    print(f"[CLIENT] {message}")


def log_match(message: str) -> None:
    print(f"[MATCH] {message}")


def log_phase2(message: str) -> None:
    print(f"[PHASE2] {message}")


def decode_image(image_data: str) -> bytes:
    try:
        return base64.b64decode(image_data, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data.") from exc


def cleanup_temp_files() -> None:
    temp_files = ["last_match_input.jpg", f"{BRAIN_PATH}.tmp"]
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log_server(f"Removed temp file: {file_path}")
            except OSError as exc:
                log_server(f"Failed to remove temp file {file_path}: {exc}")


def ensure_assets_ready() -> None:
    if os.path.exists(BRAIN_PATH):
        return

    log_server("Brain missing. Downloading pre-optimized MTG fingerprints...")
    temp_path = f"{BRAIN_PATH}.tmp"
    try:
        with requests.get(BRAIN_DOWNLOAD_URL, timeout=60, stream=True) as response:
            response.raise_for_status()
            with open(temp_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    except requests.RequestException as exc:
        log_server(f"Brain download failed: {exc}")
        raise

    file_size = os.path.getsize(temp_path)
    if file_size <= 0:
        os.remove(temp_path)
        raise RuntimeError("Downloaded brain file is empty.")

    os.replace(temp_path, BRAIN_PATH)
    log_server(f"Brain ready: {BRAIN_PATH} ({file_size} bytes)")


def start_headless_broadcast(port: int, interval: float = 2.0) -> threading.Thread:
    def broadcast_loop() -> None:
        message = f"Aether-Sight Host Engine on port {port}".encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                sock.sendto(message, ("255.255.255.255", 37020))
                time.sleep(interval)

    thread = threading.Thread(target=broadcast_loop, daemon=True)
    thread.start()
    log_server("Headless broadcast enabled")
    return thread


def order_points(pts: np.ndarray) -> np.ndarray:
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


def get_center_crop(image: np.ndarray, crop_ratio: float = 0.5) -> np.ndarray:
    height, width = image.shape[:2]
    crop_width = int(width * crop_ratio)
    crop_height = int(height * crop_ratio)
    start_x = (width - crop_width) // 2
    start_y = (height - crop_height) // 2
    return image[start_y : start_y + crop_height, start_x : start_x + crop_width]


def apply_clahe(image: np.ndarray, clahe: cv2.CLAHE) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    l_channel = clahe.apply(l_channel)
    merged = cv2.merge([l_channel, a_channel, b_channel])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def compute_hsv_histogram(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 12, 3], [0, 180, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist.astype(np.float32)


def ensure_collection_db() -> None:
    connection = sqlite3.connect(COLLECTION_DB)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            set_code TEXT NOT NULL,
            matches INTEGER NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def log_collection_hit(card_name: str, set_code: str, matches: int, mode: str) -> None:
    connection = sqlite3.connect(COLLECTION_DB)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO collection_hits(card_name, set_code, matches, mode, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (card_name, set_code, matches, mode, time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    connection.commit()
    connection.close()


@dataclass
class Brain:
    descriptors: np.ndarray
    descriptor_card_index: np.ndarray
    card_names: list[str]
    set_codes: list[str]
    card_hsv_hist: np.ndarray
    card_phash: list[str]
    oracle_texts: list[str]
    mana_costs: list[str]
    card_image_urls: list[str]


def load_brain(path: str) -> Brain:
    log_server(f"Loading brain from {path}")
    with open(path, "rb") as handle:
        data = pickle.load(handle)
    return Brain(
        descriptors=data["descriptors"],
        descriptor_card_index=data["descriptor_card_index"],
        card_names=data["card_names"],
        set_codes=data["set_codes"],
        card_hsv_hist=data["card_hsv_hist"],
        card_phash=data["card_phash"],
        oracle_texts=data["oracle_texts"],
        mana_costs=data["mana_costs"],
        card_image_urls=data["card_image_urls"],
    )


class HostEngineIdentifier:
    def __init__(self, brain_path: str = BRAIN_PATH) -> None:
        self.orb = cv2.ORB_create(nfeatures=N_FEATURES)
        self.clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        self.brain = load_brain(brain_path)
        index_params = dict(algorithm=6, table_number=6, key_size=12, multi_probe_level=1)
        search_params = dict(checks=50)
        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
        self.matcher.add([self.brain.descriptors])
        self.matcher.train()
        self.active_deck_indices: Optional[set[int]] = None

    def set_active_deck(self, decklist: str) -> None:
        names = {line.strip().lower() for line in decklist.splitlines() if line.strip()}
        if not names:
            self.active_deck_indices = None
            log_client("Active deck cleared")
            return
        indices = {
            idx for idx, name in enumerate(self.brain.card_names) if name.lower() in names
        }
        self.active_deck_indices = indices if indices else None
        log_client(f"Active deck loaded: {len(indices)} cards")

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
        return four_point_transform(image, contour)

    def _confidence_level(self, match_count: int) -> str:
        if match_count >= 75:
            return "High"
        if match_count >= 40:
            return "Medium"
        return "Low"

    def _stage_one_candidates(self, hsv_hist: np.ndarray, use_deck: bool) -> list[int]:
        if use_deck and self.active_deck_indices:
            indices = np.array(list(self.active_deck_indices), dtype=np.int32)
            histograms = self.brain.card_hsv_hist[indices]
        else:
            indices = np.arange(len(self.brain.card_names))
            histograms = self.brain.card_hsv_hist

        correlations = np.array(
            [cv2.compareHist(hsv_hist, candidate, cv2.HISTCMP_CORREL) for candidate in histograms],
            dtype=np.float32,
        )
        top_k = min(TOP_CANDIDATES, len(indices))
        top_indices = np.argpartition(-correlations, top_k - 1)[:top_k]
        sorted_indices = top_indices[np.argsort(-correlations[top_indices])]
        return indices[sorted_indices].tolist()

    def _stage_two_match(
        self, descriptors: np.ndarray, candidate_indices: list[int], mode: str
    ) -> tuple[Optional[dict], list[dict]]:
        matches = self.matcher.knnMatch(descriptors, k=2)
        good_matches = []
        for pair in matches:
            if len(pair) < 2:
                continue
            first, second = pair
            if first.distance < 0.75 * second.distance:
                good_matches.append(first)

        if not good_matches:
            log_match("No good matches after ratio test")
            return None, []

        candidate_set = set(candidate_indices)
        card_votes = {idx: 0 for idx in candidate_indices}
        for match in good_matches:
            card_index = int(self.brain.descriptor_card_index[match.trainIdx])
            if card_index in candidate_set:
                card_votes[card_index] += 1

        sorted_candidates = sorted(card_votes.items(), key=lambda item: item[1], reverse=True)
        best_index, best_count = sorted_candidates[0]
        log_match(f"Best match {self.brain.card_names[best_index]} with {best_count} matches")

        if best_count < MIN_MATCHES:
            log_match("Best match below minimum threshold")
            return None, []

        if mode == "collection":
            log_collection_hit(
                self.brain.card_names[best_index], self.brain.set_codes[best_index], best_count, mode
            )

        candidates_payload = [
            {
                "card": self.brain.card_names[idx],
                "set": self.brain.set_codes[idx],
                "matches": count,
                "image_url": self.brain.card_image_urls[idx],
            }
            for idx, count in sorted_candidates[:5]
        ]

        result = {
            "card": self.brain.card_names[best_index],
            "set": self.brain.set_codes[best_index],
            "matches": best_count,
            "confidence": self._confidence_level(best_count),
            "oracle_text": self.brain.oracle_texts[best_index],
            "mana_cost": self.brain.mana_costs[best_index],
        }
        return result, candidates_payload

    def identify(self, image_bytes: bytes, mode: str) -> Optional[dict]:
        np_image = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=400, detail="Could not decode image bytes.")

        card_image = self._extract_card(frame)
        crop = get_center_crop(card_image, 0.5)
        if crop.mean() < 5:
            log_match("Black hole crop detected")
            return {"match": False, "error": "Black hole crop detected"}

        crop = apply_clahe(crop, self.clahe)
        hsv_hist = compute_hsv_histogram(crop)

        candidate_indices = self._stage_one_candidates(hsv_hist, use_deck=True)
        if self.active_deck_indices and not candidate_indices:
            candidate_indices = self._stage_one_candidates(hsv_hist, use_deck=False)
        elif not self.active_deck_indices:
            candidate_indices = self._stage_one_candidates(hsv_hist, use_deck=False)

        if not candidate_indices:
            log_match("No candidates after HSV stage")
            return None

        top_candidate = candidate_indices[0]
        correlation = float(
            cv2.compareHist(hsv_hist, self.brain.card_hsv_hist[top_candidate], cv2.HISTCMP_CORREL)
        )
        log_match(f"HSV correlation {correlation:.3f} for {self.brain.card_names[top_candidate]}")
        if correlation < COLOR_THRESHOLD:
            log_match("Rejected by HSV veto")
            return None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        if descriptors is None or len(keypoints) == 0:
            log_match("No descriptors detected")
            return None

        if mode == "collection":
            ensure_collection_db()
            result, candidates = self._stage_two_match(descriptors, candidate_indices, mode)
            if result:
                log_phase2("Collection mode semantic hooks ready")
            return {"match": bool(result), **(result or {}), "candidates": candidates}

        result, candidates = self._stage_two_match(descriptors, candidate_indices, mode)
        if result:
            log_phase2("Semantic hooks attached")
            if result["confidence"] == "Low":
                return {"match": True, **result, "candidates": candidates}
            return {"match": True, **result}

        return None


app = FastAPI(title="Aether Sight Host Engine", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cleanup_temp_files()
ensure_assets_ready()
identifier = HostEngineIdentifier()


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    image_bytes = decode_image(request.image)
    mode = request.mode if request.mode in {"play", "collection"} else "play"
    result = identifier.identify(image_bytes, mode)
    if not result:
        return {"match": False}
    return result


@app.post("/load-deck")
def load_deck(request: LoadDeckRequest):
    identifier.set_active_deck(request.decklist)
    return {"status": "ok"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aether-Sight Host Engine")
    parser.add_argument("--headless", action="store_true", help="Enable UDP broadcast mode")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.headless:
        start_headless_broadcast(args.port)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


__all__ = ["app"]
