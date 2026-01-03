# Copyright (C) 2025 Goremagon
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import multiprocessing
import os
import pickle
import sqlite3
from io import BytesIO

import cv2
import numpy as np
import imagehash
from PIL import Image

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

DB_PATH = "cards.db"
BRAIN_PATH = "brain.pkl"
COLOR_HIST_BINS = (8, 8, 8)
N_FEATURES = 250


def get_center_crop(img_bgr, crop_pct=0.5):
    h, w = img_bgr.shape[:2]
    crop_w = max(1, int(w * crop_pct))
    crop_h = max(1, int(h * crop_pct))
    x1 = (w - crop_w) // 2
    y1 = (h - crop_h) // 2
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    return img_bgr[y1:y2, x1:x2]


def _calc_color_hist(img_bgr):
    center = get_center_crop(img_bgr, 0.5)
    hist = cv2.calcHist(
        [center], [0, 1, 2], None, COLOR_HIST_BINS,
        [0, 256, 0, 256, 0, 256]
    )
    return cv2.normalize(hist, hist).flatten()


def process_card(card_tuple):
    name, set_code, blob = card_tuple
    if not blob:
        return None

    nparr = np.frombuffer(blob, np.uint8)
    color_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if color_img is None:
        return None

    gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=N_FEATURES)
    _, des = orb.detectAndCompute(gray_img, None)
    if des is None:
        return None

    try:
        color_hist = _calc_color_hist(color_img)
        pil_img = Image.open(BytesIO(blob))
        phash = imagehash.phash(pil_img)
    except Exception:
        return None

    return {
        "name": name,
        "set_code": set_code,
        "des": des,
        "hist": color_hist,
        "phash": phash,
    }


if __name__ == "__main__":
    num_workers = max(1, os.cpu_count() // 2)
    print(f"🚀 Starting compilation with {num_workers} cores...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    all_rows = cursor.execute(
        "SELECT card_name, set_code, image_blob FROM cards"
    ).fetchall()
    conn.close()

    brain = []
    with multiprocessing.Pool(num_workers) as pool:
        results = pool.imap_unordered(process_card, all_rows, chunksize=50)
        if tqdm:
            results = tqdm(results, total=len(all_rows), unit="card")
        for result in results:
            if result is not None:
                brain.append(result)

    with open(BRAIN_PATH, "wb") as f:
        pickle.dump(brain, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Brain compiled: {len(brain)} cards -> {BRAIN_PATH}")

