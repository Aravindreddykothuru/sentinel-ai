# SENTINEL AI — Predictive Maintenance

| Part | Path | Stack | Free hosting |
|---|---|---|---|
| Backend | `backend-hackathon-master/backend-hackathon-master` | FastAPI, WebSockets, SQLite, Gemini | Render (free web service) |
| Frontend | `frontend-hackathon-master/frontend-hackathon-master` | Next.js 16, React 19 | Vercel (Hobby) |

## How they connect

- `GET /machines/` and `GET /alerts/` (polled every 5 s) load machines and alerts.
- `ws(s)://<backend>/ws/<client-id>` streams live sensor readings every 2 s for every subscribed machine.
- The scheduler generates a reading per machine every 60 s, runs the 3-tier monitor, asks Gemini for a diagnosis when a machine turns critical, and raises an alert after two confirmations.
- Copilot chat goes to the frontend route `/api/sentinel-chat`, which streams from Gemini if the frontend has a key and otherwise forwards to the backend's `POST /copilot/chat`.
- The frontend only needs `NEXT_PUBLIC_API_URL`; the WebSocket URL is derived from it (`https` → `wss`).

On first start the backend seeds the four dashboard machines (A–D).

## Run locally

```bash
# Backend (http://localhost:8000, docs at /docs)
cd backend-hackathon-master/backend-hackathon-master
python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                              # add GOOGLE_API_KEY if you have one
uvicorn main:app --reload --port 8000

# Frontend (http://localhost:3000)
cd frontend-hackathon-master/frontend-hackathon-master
npm ci
cp .env.example .env.local
npm run dev
```

## Deploy (free)

1. **Backend on Render** — Dashboard → **New → Blueprint** → select this repo. `render.yaml` configures everything; fill in `GOOGLE_API_KEY` when prompted (optional). Copy the service URL, e.g. `https://sentinel-ai-backend.onrender.com`.
2. **Frontend on Vercel** — **Add New → Project** → import this repo → set **Root Directory** to `frontend-hackathon-master/frontend-hackathon-master` → add env var `NEXT_PUBLIC_API_URL` = the Render URL → Deploy.
3. Optional: on Render set `CORS_ORIGINS` to your Vercel URL to restrict API access.

Free-tier notes: the Render service sleeps after 15 minutes without traffic and takes about a minute to wake (the dashboard shows built-in demo data until it connects, then switches to live data). SQLite lives on an ephemeral disk, so data resets on restart; point `DATABASE_URL` at a free Postgres (Neon, Supabase) to keep it.
