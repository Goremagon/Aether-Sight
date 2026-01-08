# Aether Sight Architecture

## The Data Pipeline

1. **Master Source (`backend/cards.db`)**

- **Type:** SQLite Database (Heavy).
- **Content:** Raw high-res images and metadata.
- **Role:** Developer-Only Asset. Used solely to generate the Brain.
- **Deployment:** DO NOT SHIP.

2. **The Compiler (`backend/compile_brain.py`)**

- **Role:** The Build System.
- **Action:** Reads `cards.db` -> Extracts Features (ORB/Color/Hash) -> Writes `brain.pkl`.
- **Note:** Must be run whenever `cards.db` is updated (e.g., new sets added).

3. **The Runtime Brain (`backend/brain.pkl`)**

- **Type:** Python Pickle Binary (Lightweight).
- **Content:** Mathematical feature vectors only (No images).
- **Role:** Production Asset. Required for `main.py` to start.
- **Performance:** Loads in <2 seconds.

## Workflow

1. **Update:** `python indexer.py --set [CODE]` (Adds to DB).
2. **Build:** `python compile_brain.py` (Creates Brain).
3. **Run:** `python start_all.py` (Loads Brain).
