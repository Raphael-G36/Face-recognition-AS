Railway deployment notes

- Ensure `requirements.txt` exists (this project includes it).
- Railway will run the `web` process from the `Procfile`.
- The app uses `gunicorn` (already listed in `requirements.txt`).

Quick deploy steps:
1. Commit your code and push to a Git provider connected to Railway.
2. On Railway, create a new project and link the repo/branch.
3. Railway will install dependencies and run:
   `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 3 --threads 4`

Environment variables:
- `PORT` – set by Railway automatically.
- `FLASK_DEBUG` – set to `true` for debug mode (not for production).

Important notes:
- SQLite is stored on the container filesystem and is ephemeral. Use an external database (e.g., PostgreSQL) for persistent storage and set the appropriate connection string via Railway environment variables.
- Do not enable TLS/SSL in `app.run()`; Railway provides TLS termination.

Local testing:
- Install deps in a virtualenv, then run:
  `gunicorn app:app --bind 0.0.0.0:8000 --workers 3`

Contact: Update this file with project-specific environment variables and secrets as needed.
