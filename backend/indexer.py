# Copyright (C) 2025 Goremagon
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

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
import time

# DATABASE SETUP
DB_PATH = "cards.db"
SET_TYPES = {"core", "expansion", "masters", "draft_innovation"}


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
        print(f"Searching specifically for set: {set_code.upper()}...")
    else:
        # Default: Search for old cards if no set specified
        query = "year<=1994 unique:prints"
        print("Searching for all cards from 1993-1994...")

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

                    time.sleep(0.1)

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
                params = {}  # Clear params because next_page url has them built-in
            else:
                break

        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    conn.close()
    print(f"\nDone! Added {count} new cards to the database.")


def fetch_sets():
    resp = requests.get("https://api.scryfall.com/sets", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    sets = [s for s in data.get("data", []) if s.get("set_type") in SET_TYPES]
    sets.sort(key=lambda s: s.get("released_at") or "9999-99-99")
    return sets


def get_set_card_count(set_code):
    if set_code:
        set_code = set_code.lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE set_code = ?", (set_code,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Magic cards for Aether Sight")
    parser.add_argument("--limit", type=int, help="Limit number of cards to download", default=None)
    parser.add_argument("--set", type=str, help="Download a specific set (e.g., '3ed' for Revised)", default=None)
    parser.add_argument("--all", action="store_true", help="Download all historical sets")

    args = parser.parse_args()

    init_db()
    if args.all:
        sets = fetch_sets()
        total = len(sets)
        for index, set_info in enumerate(sets, start=1):
            set_code = set_info.get("code", "").lower()
            if not set_code:
                continue
            existing_count = get_set_card_count(set_code)
            if existing_count > 0:
                print(f"\u23e9 Skipping {set_code.upper()} (Already exists)")
                continue
            print(f"=== Starting Set: {set_code.upper()} ({index}/{total}) ===")
            fetch_cards(limit=args.limit, set_code=set_code)
    else:
        if args.set:
            normalized_set = args.set.lower()
            existing_count = get_set_card_count(normalized_set)
            if existing_count > 0:
                print(f"\u23e9 Skipping {normalized_set.upper()} (Already exists)")
                sys.exit(0)
            fetch_cards(limit=args.limit, set_code=normalized_set)
        else:
            fetch_cards(limit=args.limit, set_code=args.set)
