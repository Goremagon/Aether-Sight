# Aether-Sight

High-fidelity remote play prototype with a Python computer-vision backend and a React-based high-resolution camera hook.

## Backend

- `backend/indexer.py`: Build a pHash database from Scryfall's "Unique Artwork" bulk data. Default limit is 100 cards for quick testing.
- `backend/main.py`: FastAPI application that extracts a card from an input image, computes its pHash, and looks it up in `cards.db`.
- `backend/requirements.txt`: Python dependencies.

### Quickstart

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python indexer.py --limit 100  # build cards.db
uvicorn main:app --reload --port 8000
```

## Frontend

- `frontend/src/hooks/useHighResCamera.js`: Custom hook that requests a 4K/30fps video stream and manages lifecycle helpers for start/stop and errors.
