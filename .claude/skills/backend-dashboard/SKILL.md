---
name: backend-dashboard
description: Use when writing backend (FastAPI + PostgreSQL) or dashboard (React) code — in/out sessions, anti-fraud matching, fees, statistics — for the smart parking thesis.
---

# Backend & Dashboard

Backend in `src/backend/` (FastAPI + SQLAlchemy + PostgreSQL), dashboard in `src/frontend/` (React + Vite). Consumes `VehicleRecord` from `alpr-pipeline`.

## Database schema (PostgreSQL)

- `parking_sessions`: id, plate_text, plate_color, vehicle_type, entry_time, exit_time (nullable), entry_image_path, exit_image_path (nullable), entry_confidence, exit_confidence, fee_amount (nullable), status (`in_lot` | `completed` | `disputed`)
- `fee_rules`: id, vehicle_type, price_per_block, block_hours, active
- `users`: id, username, password_hash (bcrypt), role (`operator` | `admin`)
- Evidence images on disk `src/backend/storage/evidence/YYYY-MM-DD/<session-id>-{entry,exit}.jpg`; DB stores paths. **Privacy (CLAUDE.md):** plate_text encrypted at rest (pgcrypto `pgp_sym_encrypt` or app-level Fernet — pick one, document in report), role-based access on all read endpoints, nightly job deletes sessions + images past retention period after exit.

## In/out flow + anti-fraud

- **Entry:** `POST /api/sessions/entry` body = VehicleRecord fields → creates `in_lot` session, stores evidence image.
- **Exit:** `POST /api/sessions/exit` → find `in_lot` session with matching normalized plate. Match rules: exact match ⇒ compute fee, close. No match or vehicle_type mismatch ⇒ status `disputed`, operator resolves comparing entry/exit evidence images (this is the anti-fraud mechanism from the outline).
- Fee: ceil((exit − entry)/block_hours) × price_per_block by vehicle_type from active `fee_rules`.

## API routes

- `POST /api/sessions/entry`, `POST /api/sessions/exit` — called by pipeline host
- `GET /api/sessions?status=in_lot&plate=...` — lookup/search
- `GET /api/stats/traffic?granularity=hour|day` · `GET /api/stats/revenue` · `GET /api/stats/breakdown?by=vehicle_type|plate_color`
- `GET /api/sessions/{id}/evidence/{entry|exit}` — auth-gated image serve
- Auth: JWT bearer; `operator` reads + resolves disputes, `admin` also edits fee_rules and users.

## Dashboard pages (React)

1. **Live** — realtime in/out feed (poll 2 s or SSE), current in-lot count
2. **Lookup** — search by plate fragment; session detail with evidence images side-by-side
3. **Disputes** — `disputed` queue, operator resolve UI
4. **Stats** — charts: traffic over time, revenue, breakdown by vehicle type and plate color (recharts)
5. **Settings** (admin) — fee rules, users

## Conventions

- Pydantic schemas mirror DB models; SQLAlchemy 2.0 style; Alembic migrations from day one.
- Tests: pytest + httpx against a dockerized Postgres (or SQLite fallback marked xfail for pg-specific features); fee and matching logic get exhaustive unit tests — they're the anti-fraud thesis claims.
