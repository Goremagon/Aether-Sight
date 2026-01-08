# Copyright (C) 2025 Goremagon
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sqlite3
import requests
import time
import sys

# --- CONFIG ---
DB_PATH = "cards.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT,
            set_code TEXT,
            image_blob BLOB,
            UNIQUE(card_name, set_code)
        )
    """)
    conn.commit()
    return conn

def download_set(set_code):
    set_code = set_code.lower()
    print(f"\n📥 Fetching set: {set_code.upper()}...")
    url = f"https://api.scryfall.com/cards/search?q=set:{set_code}+unique:prints"
    
    conn = init_db()
    cursor = conn.cursor()
    
    has_more = True
    count = 0

    while has_more:
        try:
            resp = requests.get(url)
            data = resp.json()
        except Exception as e:
            print(f"❌ Network error: {e}")
            return

        if "data" not in data:
            print(f"❌ Set '{set_code}' not found on Scryfall.")
            return

        for card in data["data"]:
            if "image_uris" not in card:
                continue

            name = card["name"]
            image_url = card["image_uris"]["normal"] 
            
            try:
                img_resp = requests.get(image_url)
                if img_resp.status_code == 200:
                    blob = img_resp.content
                    try:
                        cursor.execute("INSERT OR REPLACE INTO cards (card_name, set_code, image_blob) VALUES (?, ?, ?)", 
                                      (name, set_code, blob))
                        conn.commit()
                        count += 1
                        print(f"   ✅ Saved: {name}")
                    except sqlite3.Error:
                        pass 
            except:
                pass
            time.sleep(0.05) 

        has_more = data.get("has_more", False)
        url = data.get("next_page")

    print(f"🎉 Finished {set_code.upper()}. Added {count} cards.")
    conn.close()

if __name__ == "__main__":
    # Check if user typed a set code
    if len(sys.argv) < 2:
        print("⚠️  Usage: python ingest.py [set_code]")
        print("   Example: python ingest.py wot")
        print("   Example: python ingest.py 3ed")
    else:
        # Loop through all sets typed (e.g., "python ingest.py wot 3ed")
        for set_code in sys.argv[1:]:
            download_set(set_code)
        print("\n✅ All downloads complete. Restart your backend to apply changes.")