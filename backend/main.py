# Copyright (C) 2025 Goremagon
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import cv2
import numpy as np
import base64
import imagehash
from PIL import Image
from io import BytesIO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
DB_PATH = "cards.db"
# Now that input is clean, we can demand a high quality match
MIN_ORB_MATCHES = 40
PHASH_VERIFY_THRESHOLD = 35
COLOR_HIST_BINS = (8, 8, 8)
COLOR_CORR_THRESHOLD = 0.5

class AnalyzeRequest(BaseModel):
    image: str
    target_x: float
    target_y: float
    box_scale: float

class HybridIdentifier:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # 3000 features is the sweet spot for speed/accuracy
        self.orb = cv2.ORB_create(nfeatures=3000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        # Standard contrast
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))
        self.cards = self._load_cards()
        print(f"? Brain Loaded: {len(self.cards)} cards.")

    def _calc_color_hist(self, img_bgr):
        hist = cv2.calcHist(
            [img_bgr], [0, 1, 2], None, COLOR_HIST_BINS,
            [0, 256, 0, 256, 0, 256]
        )
        return cv2.normalize(hist, hist).flatten()

    def _load_cards(self):
        cursor = self.conn.cursor()
        loaded = []
        try:
            cursor.execute("SELECT card_name, set_code, image_blob FROM cards")
            for name, set_code, blob in cursor.fetchall():
                if blob:
                    nparr = np.frombuffer(blob, np.uint8)
                    color_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Pre-compute features for the DB
                    gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
                    kp, des = self.orb.detectAndCompute(gray_img, None)
                    color_hist = self._calc_color_hist(color_img)

                    pil_img = Image.open(BytesIO(blob))
                    phash = imagehash.phash(pil_img)

                    if des is not None:
                        loaded.append({
                            "name": name, "set": set_code, "des": des,
                            "phash": phash, "hist": color_hist
                        })
        except Exception as e:
            print(f"Database Error: {e}")
        return loaded

    def _get_sniper_crop(self, user_img, click_x_pct, click_y_pct, box_scale):
        """
        Extracts the exact Red Box area from the user's screen.
        """
        h, w = user_img.shape[:2]
        center_x = int(click_x_pct * w)
        center_y = int(click_y_pct * h)

        # Calculate size based on Frontend Box Scale
        box_w = int(w * box_scale)
        box_h = int(box_w / 0.716)

        x1 = max(0, center_x - box_w // 2)
        y1 = max(0, center_y - box_h // 2)
        x2 = min(w, center_x + box_w // 2)
        y2 = min(h, center_y + box_h // 2)

        return user_img[y1:y2, x1:x2]

    def identify(self, user_image_base64, target_x, target_y, box_scale):
        if "," in user_image_base64:
            user_image_base64 = user_image_base64.split(",")[1]

        # 1. Decode
        image_data = base64.b64decode(user_image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        user_img_color = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 2. SNIPER CROP (Get the perfect card image)
        crop_color = self._get_sniper_crop(user_img_color, target_x, target_y, box_scale)

        # 3. DEBUG: Save it so we know what we are matching against
        cv2.imwrite("last_match_input.jpg", crop_color)
        print("?? Saved Crop to 'last_match_input.jpg'")

        # 4. PREPARE FOR MATCHING
        # Enhance contrast to help seeing through glare
        lab = cv2.cvtColor(crop_color, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        enhanced_color = cv2.merge((l, a, b))
        enhanced_color = cv2.cvtColor(enhanced_color, cv2.COLOR_LAB2BGR)

        crop_gray = cv2.cvtColor(enhanced_color, cv2.COLOR_BGR2GRAY)
        crop_hist = self._calc_color_hist(crop_color)

        # Calculate pHash
        crop_pil = Image.fromarray(crop_gray)
        crop_phash = imagehash.phash(crop_pil)

        # 5. RUN MATCHING
        kp, user_des = self.orb.detectAndCompute(crop_gray, None)
        if user_des is None:
            print("?? No features found in crop (Too blurry?)")
            return {"match": False}

        best_match = None
        max_matches = 0

        for card in self.cards:
            if card["des"] is None:
                continue
            try:
                # Compare features
                matches = self.matcher.knnMatch(card["des"], user_des, k=2)
                good = [m for m, n in matches if m.distance < 0.75 * n.distance]
                score = len(good)

                if score > max_matches:
                    max_matches = score
                    best_match = card
            except:
                continue

        # 6. VERIFY AND RETURN
        if best_match and max_matches >= MIN_ORB_MATCHES:
            color_corr = cv2.compareHist(
                crop_hist, best_match["hist"], cv2.HISTCMP_CORREL
            )
            if color_corr < COLOR_CORR_THRESHOLD:
                print(f"? VETO: ORB match but color mismatch (Corr {color_corr:.2f}).")
                return {"match": False}

            phash_diff = crop_phash - best_match["phash"]
            print(
                f"?? Top Match: {best_match['name']} (Score: {max_matches}) | "
                f"Shape Diff: {phash_diff}"
            )

            # Shape Verification
            if phash_diff > PHASH_VERIFY_THRESHOLD:
                print(f"? VETO: Matches art but wrong shape (Diff {phash_diff}).")
                return {"match": False}

            return {"match": True, "card": best_match["name"]}

        print(
            f"?? No good match found. Best was "
            f"{best_match['name'] if best_match else 'None'} ({max_matches})"
        )
        return {"match": False}

identifier = HybridIdentifier()

@app.post("/analyze")
async def analyze_card(request: AnalyzeRequest):
    return identifier.identify(request.image, request.target_x, request.target_y, request.box_scale)
