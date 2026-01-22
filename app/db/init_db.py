from sqlalchemy import text
from app.db.session import engine
from app.db.models import Base

async def init_db() -> None:
    async with engine.begin() as conn:
        # pgvector extension (safe if already installed)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            # On some managed PG instances extension may be unavailable.
            # The app can still run if you change Face.embedding type to FLOAT8[].
            pass

        await conn.run_sync(Base.metadata.create_all)
