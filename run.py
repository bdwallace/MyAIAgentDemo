import uvicorn

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "gateway.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
