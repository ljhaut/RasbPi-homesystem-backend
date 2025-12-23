from fastapi import APIRouter

health_router = APIRouter(
    prefix="/health",
)


@health_router.get("/")
async def health_check():
    """
    Health check endpoint to verify if the service is running.

    :return: Status of the service
    :rtype: dict
    """
    return {"status": "ok"}
