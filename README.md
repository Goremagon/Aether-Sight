Aether-Sight
Aether-Sight is a high-fidelity remote play prototype designed for Magic: The Gathering. It bridges a physical tabletop experience with digital recognition by combining a Python computer-vision backend with a high-resolution React frontend.

🌟 Features
Computer Vision Backend: Uses perceptual hashing (pHash) to fingerprint and identify cards from a live video feed.

Scryfall Integration: database generation using Scryfall's "Unique Artwork" bulk data.

High-Fidelity Frontend: Custom React hooks designed to force 4K/30fps video streams for maximum card readability.

FastAPI Architecture: Lightweight and fast REST API for handling image processing requests.

🛠 Tech Stack
Backend: Python 3.x, FastAPI, Uvicorn, SQLite (via cards.db)

Frontend: React, JavaScript

Data Source: Scryfall API

📂 Project Structure
Plaintext

├── backend/
│   ├── indexer.py        # Builds pHash database from Scryfall data
│   ├── main.py           # FastAPI app: receives images, computes pHash, queries DB
│   └── requirements.txt  # Python dependencies
│
└── frontend/
    └── src/
        └── hooks/
            └── useHighResCamera.js  # Custom hook for 4K/30fps stream management
🚀 Getting Started
1. Backend Setup
The backend handles the card indexing and identification logic.

Prerequisites: Python 3.8+

Bash

cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
Database Initialization:

Before running the server, you must build the local card database. By default, this limits processing to 100 cards for quick testing.

Bash

# Downloads Scryfall data and builds cards.db
python indexer.py --limit 100
Running the Server:

Start the FastAPI development server:

Bash

uvicorn main:app --reload --port 8000
The API will be available at http://localhost:8000.

2. Frontend Setup
The frontend utilizes a custom hook to manage high-resolution camera constraints.

(Note: Ensure you have Node.js installed)

Bash

cd frontend

# Install dependencies (assuming standard React setup)
npm install

# Start the client
npm start
🧩 Key Components
backend/indexer.py
This script fetches the latest bulk data from Scryfall. It downloads the "Unique Artwork" JSON, processes the images to generate perceptual hashes (pHash), and stores them in cards.db.

Usage: python indexer.py [--limit N]

frontend/src/hooks/useHighResCamera.js
A custom React hook that interacts with the browser's MediaDevices API. It specifically requests 4K resolution constraints ({ width: 3840, height: 2160 }) and manages the stream lifecycle (start/stop) and error handling.

📄 License :GNU GPLv3

## ⚖️ Legal & Disclaimers

**Aether-Sight** is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

The card data and images are provided by [Scryfall](https://scryfall.com/). Please adhere to Scryfall's [API Guidelines](https://scryfall.com/docs/api) regarding rate limits and data usage.