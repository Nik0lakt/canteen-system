# Meal Control (FastAPI + PostgreSQL + Face ID + Liveness)

Backend prototype for subsidized employee meals with:
- daily subsidy pocket (non-cumulative),
- monthly payroll pocket,
- strict server-side business rules,
- face recognition + active liveness (head pose challenges + blink),
- cashier web prototype (HTML + getUserMedia).

## Notes
- Amounts are stored in cents (integers) to avoid floating-point errors.
- Face embeddings are stored in PostgreSQL using pgvector.
- This is a prototype; for production you should add stronger liveness/attestation, secrets management, encryption-at-rest, rate limiting, audit controls, and migrations.

## Configuration
Create `.env` from `.env.example`.

## Cashier UI
Open `/static/cashier.html` (served via FastAPI at `/static/cashier.html`) and set `TERMINAL_TOKEN` in `cashier.js`.
