UIBRAS — Face recognition attendance (Flask)

Overview
- Simple Flask web app that captures student face images and performs recognition for attendance using DeepFace and OpenCV.

Prerequisites
- Python 3.9+
- System libraries for OpenCV (if needed) and a working internet connection for some packages.

Install (recommended inside a virtualenv)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run locally (development)

```bash
export FLASK_DEBUG=true
python app.py
# or (production-like) using gunicorn
gunicorn app:app --bind 0.0.0.0:8000 --workers 3
```

Railway / production notes
- See `README_RAILWAY.md` for Railway-specific deployment steps.
- A `Procfile` exists and starts the app with Gunicorn.
- `PORT` is read from the environment (set automatically by Railway).
- Do not rely on the bundled SQLite database (`face_recognition.db`) for production: container storage is ephemeral. Use a managed database (Postgres) and store credentials in env vars.

Security & files
- The repository ignores virtualenvs, generated images, logs, `.env`, and private certs (see `.gitignore`).
- Keep any secret keys and DB connection strings out of the repo and in Railway environment variables.

Next steps (suggested)
- Migrate DB logic to use `SQLAlchemy` and `DATABASE_URL` for Postgres.
- Add automated tests and a small CI workflow.

Files added/changed for deployment
- `Procfile` — Gunicorn process
- `requirements.txt` — root requirements
- `README_RAILWAY.md` — Railway deployment notes
- `.gitignore` — ignores for virtualenv, DB, and generated media

If you'd like, I can:
- Convert the app to use Postgres + SQLAlchemy and wire `DATABASE_URL`.
- Add a small GitHub Actions workflow for tests and deploy previews.
