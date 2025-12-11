from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes import employees, enroll, liveness, payments

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для dev, потом можно ужать
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём таблицы при старте
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


# Подключаем роуты
app.include_router(employees.router)
app.include_router(enroll.router)
app.include_router(liveness.router)
app.include_router(payments.router)

# Статика
app.mount("/static", StaticFiles(directory="static"), name="static")
