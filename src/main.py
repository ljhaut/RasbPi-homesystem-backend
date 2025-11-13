import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from core.config import app_settings
from core.logging_config import setup_logger
from db.base import engine
from endpoints.api.v1.electricity import electricity_router
from endpoints.health import health_router
from services.electricity_monitor_service import ElectricityMonitorService


@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor_service = ElectricityMonitorService()
    asyncio.create_task(monitor_service.start())
    yield
    if monitor_service and monitor_service.is_running:
        await monitor_service.stop()


app = FastAPI(lifespan=lifespan)
logger = setup_logger()

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=app_settings.CORS_METHODS,
    allow_headers=app_settings.CORS_HEADERS,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    process_time = (time.time() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} completed_in={process_time:.2f}ms status_code={response.status_code}"
    )

    return response


app.include_router(health_router)
app.include_router(electricity_router, prefix="/api/v1", tags=["electricity"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, access_log=False)
