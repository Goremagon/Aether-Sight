from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import cv2
import numpy as np
import base64

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
MIN_MATCH_COUNT = 15

# NEW REQUEST FORMAT (Includes Target Coordinates)
class AnalyzeRequest(BaseModel):
    image: str
    target_x: float
    target_y: float

class CardIdentifier:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.orb = cv2.ORB_create(nfeatures=2000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.cards = self._load_cards()
        print(f"✅ Brain Loaded: {len(self.cards)} cards with Target Lock.")

    def _load_cards(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT card_name, set_code, image_blob FROM cards")
        except sqlite3.OperationalError:
            print("❌ Database Error: Table not found.")
            return []

        loaded = []
        for name, set_code, blob in cursor.fetchall():
            if blob:
                try:
                    nparr = np.frombuffer(blob, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                    kp, des = self.orb.detectAndCompute(img, None)
                    if des is not None:
                        loaded.append({"name": name, "set": set_code, "des": des})
                except:
                    continue
        return loaded

    def _find_targeted_card(self, img, click_x_pct, click_y_pct):
        height, width = img.shape
        click_x = int(click_x_pct * width)
        click_y = int(click_y_pct * height)
        
        # 1. Blur & Threshold
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 140, 255, cv2.THRESH_BINARY)
        
        # 2. Find Contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < 50 or h < 50: continue

            # HIT TEST: Did user click this box?
            if x <= click_x <= x + w and y <= click_y <= y + h:
                print(f"🎯 CLICK HIT! Found card at [{x},{y}]")
                return img[y:y+h, x:x+w]
        
        print("❌ Click missed. Scanning full image as backup.")
        return img

    def identify(self, user_image_base64, target_x, target_y):
        if "," in user_image_base64:
            user_image_base64 = user_image_base64.split(",")[1]
        
        try:
            image_data = base64.b64decode(user_image_base64)
            nparr = np.frombuffer(image_data, np.uint8)
            user_img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        except Exception:
            return {"match": False}

        # STEP 1: CROP TO TARGET
        zoomed_img = self._find_targeted_card(user_img, target_x, target_y)

        # STEP 2: SCAN
        kp, user_des = self.orb.detectAndCompute(zoomed_img, None)
        if user_des is None: return {"match": False}

        best_match = None
        max_good_matches = 0
        bad_moon_score = 0

        for card in self.cards:
            if card["des"] is None: continue
            try:
                matches = self.matcher.knnMatch(card["des"], user_des, k=2)
                good = []
                for m, n in matches:
                    if m.distance < 0.75 * n.distance:
                        good.append(m)
                
                score = len(good)
                if score > max_good_matches:
                    max_good_matches = score
                    best_match = card
                if "Bad Moon" in card["name"]:
                    bad_moon_score = score
            except: continue

        print(f"🔎 TARGET SCAN: Best: {best_match['name']} ({max_good_matches}) | Bad Moon: {bad_moon_score}")

        if best_match and max_good_matches >= MIN_MATCH_COUNT:
            return {"match": True, "card": best_match["name"]}
        
        return {"match": False}

identifier = CardIdentifier()

@app.post("/analyze")
async def analyze_card(request: AnalyzeRequest):
    return identifier.identify(request.image, request.target_x, request.target_y)