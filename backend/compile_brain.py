# Copyright (C) 2025 Goremagon
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sqlite3
import pickle
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


def _center_crop(img_bgr, crop_pct=0.6):
    h, w = img_bgr.shape[:2]
    crop_w = max(1, int(w * crop_pct))
    crop_h = max(1, int(h * crop_pct))
    x1 = (w - crop_w) // 2
    y1 = (h - crop_h) // 2
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    return img_bgr[y1:y2, x1:x2]


def _calc_color_hist(img_bgr):
    center = _center_crop(img_bgr, 0.6)
    hist = cv2.calcHist(
        [center], [0, 1, 2], None, COLOR_HIST_BINS,
        [0, 256, 0, 256, 0, 256]
    )
    return cv2.normalize(hist, hist).flatten()


def _iter_with_progress(rows, total):
    if tqdm:
        return tqdm(rows, total=total, unit="card")

    def generator():
        count = 0
        for row in rows:
            count += 1
            if total:
                if count == 1 or count == total or count % 500 == 0:
                    print(f"Processed {count}/{total}")
            elif count == 1 or count % 500 == 0:
                print(f"Processed {count}")
            yield row

    return generator()


def main():
    conn = sqlite3.connect(DB_PATH)
    orb = cv2.ORB_create(nfeatures=3000)

    count_cursor = conn.cursor()
    count_cursor.execute("SELECT COUNT(*) FROM cards")
    total = count_cursor.fetchone()[0] or 0

    cursor = conn.cursor()
    cursor.execute("SELECT card_name, set_code, image_blob FROM cards")

    brain = []
    for name, set_code, blob in _iter_with_progress(cursor, total):
        if not blob:
            continue

        nparr = np.frombuffer(blob, np.uint8)
        color_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if color_img is None:
            continue

        gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
        _, des = orb.detectAndCompute(gray_img, None)
        if des is None:
            continue

        color_hist = _calc_color_hist(color_img)
        pil_img = Image.open(BytesIO(blob))
        phash = imagehash.phash(pil_img)

        brain.append({
            "name": name,
            "set_code": set_code,
            "des": des,
            "hist": color_hist,
            "phash": phash,
        })

    with open(BRAIN_PATH, "wb") as f:
        pickle.dump(brain, f, protocol=pickle.HIGHEST_PROTOCOL)

    conn.close()
    print(f"Brain compiled: {len(brain)} cards -> {BRAIN_PATH}")


if __name__ == "__main__":
    main()
