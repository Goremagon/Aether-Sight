"""
Indexer script for building a perceptual hash database of Magic: The Gathering cards.

This utility downloads Scryfall's "Unique Artwork" bulk JSON, computes a pHash for
card artwork, and stores the results in a SQLite database. It defaults to processing
the first 100 entries for quick iteration but can scale to the entire dataset by
adjusting the `--limit` flag.
"""

import sqlite3
import requests
import argparse
import os
import sys

# DATABASE SETUP
DB_PATH = "cards.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cards
                 (id TEXT PRIMARY KEY, card_name TEXT, image_url TEXT, set_name TEXT, set_code TEXT, image_blob BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS phashes
                 (card_id TEXT, phash TEXT, 
                  FOREIGN KEY(card_id) REFERENCES cards(id))''')
    conn.commit()
    conn.close()

def download_image_as_blob(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
    return None

def fetch_cards(limit=None, set_code=None):
    """
    Fetches cards from Scryfall.
    If set_code is provided (e.g., '3ed'), it fetches ONLY that set.
    Otherwise, it defaults to a general 'Old School' search (1993-1994).
    """
    base_url = "https://api.scryfall.com/cards/search"
    
    # LOGIC: Choose what to search for
    if set_code:
        # User asked for a specific set (e.g., '3ed' for Revised)
        query = f"e:{set_code} unique:prints"
        print(f"🔍 Searching specifically for set: {set_code.upper()}...")
    else:
        # Default: Search for old cards if no set specified
        query = "year<=1994 unique:prints"
        print("🔍 Searching for all cards from 1993-1994...")

    params = {
        "q": query,
        "order": "released",
        "dir": "asc"
    }
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    count = 0
    url = base_url
    
    while url and (limit is None or count < limit):
        try:
            print(f"Downloading page: {url} ...")
            resp = requests.get(url, params=params)
            data = resp.json()
            
            # Scryfall puts the actual card data in 'data' list
            if "data" not in data:
                print("No data found or end of list.")
                break

            for card in data["data"]:
                if limit and count >= limit:
                    break
                
                # We only care about cards that have actual images
                if "image_uris" in card and "normal" in card["image_uris"]:
                    c_id = card["id"]
                    name = card["name"]
                    img_url = card["image_uris"]["normal"]
                    set_name = card.get("set_name", "Unknown")
                    s_code = card.get("set", "unk")

                    # Check if we already have this specific card ID
                    c.execute("SELECT id FROM cards WHERE id=?", (c_id,))
                    if c.fetchone():
                        print(f"Skipping existing: {name} ({s_code})")
                        continue

                    # Download the image to save in DB
                    blob = download_image_as_blob(img_url)
                    if blob:
                        c.execute("INSERT INTO cards (id, card_name, image_url, set_name, set_code, image_blob) VALUES (?, ?, ?, ?, ?, ?)",
                                  (c_id, name, img_url, set_name, s_code, blob))
                        conn.commit()
                        print(f"Saved: {name} [{s_code}]")
                        count += 1
            
            # Pagination: Get the next page URL
            if "next_page" in data:
                url = data["next_page"]
                params = {} # Clear params because next_page url has them built-in
            else:
                break
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    conn.close()
    print(f"\n✅ Done! Added {count} new cards to the database.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Magic cards for Aether Sight")
    parser.add_argument("--limit", type=int, help="Limit number of cards to download", default=None)
    parser.add_argument("--set", type=str, help="Download a specific set (e.g., '3ed' for Revised)", default=None)
    
    args = parser.parse_args()
    
    init_db()
    fetch_cards(limit=args.limit, set_code=args.set)