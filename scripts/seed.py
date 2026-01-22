import asyncio
import os
from sqlalchemy import select
from app.db.session import SessionLocal
from app.core.security import hash_token
from app.db.models import Terminal, Employee, Card

# Usage:
#   python -m scripts.seed
#
# It creates one ACTIVE terminal and one sample employee+card (without face).
# Adjust values as needed.

TERMINAL_TOKEN = os.getenv("TERMINAL_TOKEN", "dev-terminal-token")

async def main():
    async with SessionLocal() as db:
        # terminal
        th = hash_token(TERMINAL_TOKEN)
        t = (await db.execute(select(Terminal).where(Terminal.api_token_hash == th))).scalar_one_or_none()
        if not t:
            t = Terminal(name="Terminal #1", location="Canteen A", api_token_hash=th, status="ACTIVE")
            db.add(t)

        # employee
        e = Employee(tab_no="0001", full_name="Иванов Иван", employee_type="WORKER", status="ACTIVE", monthly_limit_cents=200000)
        db.add(e)
        await db.flush()

        c = Card(uid="DEMO-CARD-UID-1", employee_id=e.id, status="ACTIVE")
        db.add(c)

        await db.commit()
        print("Seeded.")
        print("Terminal token:", TERMINAL_TOKEN)
        print("Card UID:", c.uid)
        print("Employee ID:", e.id)

if __name__ == "__main__":
    asyncio.run(main())
