# 🎬 MoodFlix — Mood-Aware Media Recommendation

> Stop endless scrolling. Tell us how you feel, and we'll find the perfect movie, series, or anime.

---

## 🏗 Architecture Overview

```
┌─────────────────────┐     HTTPS / REST      ┌───────────────────────┐
│   Next.js 15 Web    │ ◄─────────────────────► │   FastAPI Backend     │
│   (TypeScript)      │   Bearer JWT (Firebase) │   (Python 3.12)       │
│   Tailwind + Framer │                         │   Uvicorn + Gunicorn  │
└─────────────────────┘                         └──────────┬────────────┘
         ▲                                                  │
         │  Same API  ◄── Future React Native app           │
                                                   ┌────────▼────────────┐
                                                   │  Firebase           │
                                                   │  • Auth (JWT)       │
                                                   │  • Firestore (DB)   │
                                                   └─────────────────────┘
                                                            │
                                                   ┌────────▼────────────┐
                                                   │  TMDB API           │
                                                   │  (movie metadata)   │
                                                   └─────────────────────┘
```

### Why Firebase?
- **Firestore** scales horizontally with zero ops overhead
- **Firebase Auth** handles Google OAuth, JWT issuance & verification
- **Same project** used by both web and the planned React Native app
- Free tier handles ~50K reads + 20K writes/day

---

## 📁 Project Structure

```
moodflix/
├── backend/                    # Python FastAPI
│   ├── app/
│   │   ├── main.py             # App entrypoint, middleware, router registration
│   │   ├── config.py           # Env var config (pydantic-settings)
│   │   ├── dependencies.py     # Firebase JWT auth dependency
│   │   ├── models/
│   │   │   └── schemas.py      # All Pydantic v2 models
│   │   ├── routers/
│   │   │   ├── auth.py         # /api/v1/auth
│   │   │   ├── users.py        # /api/v1/users
│   │   │   ├── mood.py         # /api/v1/mood
│   │   │   ├── recommendations.py  # /api/v1/recommendations
│   │   │   └── import_history.py   # /api/v1/import
│   │   └── services/
│   │       ├── firebase.py     # Firestore + Auth client
│   │       └── recommender.py  # Hybrid CF + mood ranking engine
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                   # Next.js 15 + Tailwind
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout with ambient glow + toasts
│   │   │   ├── globals.css     # Custom fonts, glass, noise, animations
│   │   │   ├── page.tsx        # Landing / hero page
│   │   │   ├── dashboard/      # Main app (mood picker + import tabs)
│   │   │   └── recommend/      # Results grid page
│   │   ├── components/
│   │   │   ├── layout/NavBar.tsx
│   │   │   ├── mood/MoodPicker.tsx      # Mood pill grid + intensity slider
│   │   │   └── media/
│   │   │       ├── MediaCard.tsx        # Standard + featured card layouts
│   │   │       └── ImportPanel.tsx      # Drag-and-drop import UI
│   │   ├── hooks/useAuth.ts    # Zustand auth store
│   │   └── lib/
│   │       ├── api.ts          # Typed API client (all backend calls)
│   │       ├── firebase.ts     # Firebase client SDK init
│   │       └── moods.ts        # Mood definitions + colors
│   ├── tailwind.config.js      # Custom colors, fonts, animations
│   ├── next.config.js
│   ├── Dockerfile
│   └── .env.example
│
└── docker-compose.yml          # Full stack in one command
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- Firebase project (free tier is fine)
- TMDB API key (free at themoviedb.org)

### 1. Firebase Setup
1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable **Google Auth** (Authentication → Sign-in method)
3. Create a **Firestore** database (start in test mode, lock down later)
4. Generate a **service account key** (Project Settings → Service Accounts → Generate key)
5. Save the JSON as `backend/firebase-credentials.json`

### 2. Backend
```bash
cd backend
cp .env.example .env
# Edit .env with your TMDB key

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
# API docs at http://localhost:8000/api/docs
```

### 3. Frontend
```bash
cd frontend
cp .env.example .env.local
# Fill in Firebase config from Project Settings → Your Apps → Web

npm install
npm run dev
# http://localhost:3000
```

### 4. Docker (full stack)
```bash
# From project root
cp backend/.env.example .env
# Fill in TMDB_API_KEY and Firebase config in .env

docker compose up --build
```

---

## 🎯 Recommendation Algorithm

```
User Watch History  ──► Build genre preference vector (L1-normalized)
                                      │
TMDB API            ──► Fetch candidates (top genres from mood session)
                                      │
                           Score each candidate:
                           ┌─────────────────────────────┐
                           │ cf_score   = cosine(user_vec, title_vec)   │
                           │ mood_score = cosine(title_vec, genre_weights)│
                           │ final = 0.5 * cf + 0.5 * mood              │
                           └─────────────────────────────┘
                                      │
                           Inject 1 serendipity pick (high mood, low CF)
                                      │
                           Return top-N to client
```

**V2 upgrade path:** Swap the cosine CF step for a proper Matrix Factorization model trained offline (surprise, LightFM) and served via a vector DB (Pinecone / Vertex AI Matching Engine).

---

## 🔒 Firestore Collections

| Collection | Purpose |
|---|---|
| `users` | User profile, preferences |
| `watch_history` | Imported watch events (keyed by uid+platform+title) |
| `mood_sessions` | Mood selections + computed genre weights |
| `recommendation_events` | Logged recs for analytics |
| `feedback` | User thumbs up/down per title |

**Recommended Firestore rules** (lock down after dev):
```js
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{collection}/{docId} {
      allow read, write: if request.auth != null
        && request.auth.uid == resource.data.uid;
    }
  }
}
```

---

## 📱 React Native (Future)

The backend is already RN-ready:
1. Install `@react-native-firebase/app` + `@react-native-firebase/auth`
2. Use the same `apiClient` pattern from `frontend/src/lib/api.ts` — just swap `auth.currentUser.getIdToken()` with the RN Firebase equivalent
3. All endpoints, models, and auth flow are identical

---

## 🧪 API Reference

Full interactive docs at `http://localhost:8000/api/docs` (Swagger UI).

Key endpoints:
- `POST /api/v1/mood/session` — Create mood session
- `POST /api/v1/recommendations/` — Get recommendations
- `POST /api/v1/recommendations/feedback` — Submit feedback
- `POST /api/v1/import/netflix` — Import Netflix CSV
- `POST /api/v1/import/prime` — Import Prime/Hotstar CSV
- `POST /api/v1/import/mal` — Import MAL XML
