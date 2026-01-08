# CLAUDE.md - Aether-Sight Operational Guide

## 🚀 Speed Commands
**Run Everything:** `python start_all.py` (Boots Backend :8000 + Frontend :3000)

### Backend (The Brain)
- **Work Dir:** `cd backend`
- **Rebuild Brain:** `python compile_brain.py` (REQUIRED if DB changes)
- **Fetch Cards:** `python indexer.py --limit 100` (Or `--set [CODE]` for full sets)
- **Dev Server:** `uvicorn main:app --reload --port 8000`
- **Deps:** `pip install -r requirements.txt`

### Frontend (The Eye)
- **Work Dir:** `cd frontend`
- **Dev Server:** `npm run dev` (Vite, ultra-fast)
- **Install:** `npm install`

## 🧠 Architecture Cheatsheet
- **The Brain:** `brain.pkl` (Serialized feature vectors). If detection sucks, delete this and run `compile_brain.py`.
- **The Database:** `cards.db` (Raw images). Heavy. Never ship this.
- **The Eye:** `GameRoom.jsx`. Uses `useHighResCamera.js` to force 4K.
- **The Fix:** We use "Center Crop" logic (50%) to ignore playmats. If you touch image processing, **MATCH THE CROP** in both `compile_brain.py` and `main.py`.

## ⚡ Coding Style
- **Python:** Functional > Object Oriented. Keep it flat. Use `print` for debug (we scrape stdout).
- **React:** Functional components. Tailwind for styles. No class-based components.
- **Philosophy:** "Ship it." If it works, it works. Optimize later.