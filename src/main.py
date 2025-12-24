import asyncio
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from core.config import app_settings
from core.logging_config import setup_logger
from endpoints.api.v1.electricity import electricity_router
from endpoints.health import health_router
from services.electricity_monitor_service import ElectricityMonitorService

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=60.0)
    logger.info("HTTP client initialized")

    monitor_service = ElectricityMonitorService(app.state.http_client)
    asyncio.create_task(monitor_service.start())

    yield

    if monitor_service and monitor_service.status.is_running:
        await monitor_service.stop()
    await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)

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
