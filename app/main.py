from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.errors import AppError
from app.core.logging import setup_logging
from app.db.init_db import init_db

from app.api.routes.employee import router as employee_router
from app.api.routes.liveness import router as liveness_router
from app.api.routes.pay import router as pay_router
from app.api.routes.enrollment import router as enrollment_router

setup_logging()

app = FastAPI(title="Meal Subsidy Control")

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"ok": False, "code": exc.code, "message": exc.message, "details": exc.details},
    )

app.include_router(employee_router)
app.include_router(liveness_router)
app.include_router(pay_router)
app.include_router(enrollment_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
