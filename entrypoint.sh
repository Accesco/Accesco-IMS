#!/bin/bash
set -e

# -------------------------------------------------------
# Entrypoint script for the Accesco IMS backend container.
# Waits for PostgreSQL, runs Alembic migrations, optionally
# seeds the database, then starts the application.
# -------------------------------------------------------

echo "============================================"
echo "  Accesco IMS Backend — Starting Up"
echo "============================================"

# --- Wait for PostgreSQL ---
echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" > /dev/null 2>&1; do
  echo "[entrypoint]   ...PostgreSQL not ready, retrying in 2s"
  sleep 2
done
echo "[entrypoint] PostgreSQL is ready!"

# --- Run Alembic Migrations ---
echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

# --- Optional: Seed the database ---
if [ "${RUN_SEED}" = "true" ]; then
  echo "[entrypoint] Seeding the database..."
  python -m app.scripts.seed
  echo "[entrypoint] Seeding complete."
else
  echo "[entrypoint] Skipping database seed (set RUN_SEED=true to enable)."
fi

echo "[entrypoint] Handing off to application command..."
echo "============================================"

# Execute the CMD passed to the container (uvicorn by default)
exec "$@"
