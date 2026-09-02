import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gateway.settings")

django_application = get_asgi_application()


async def application(scope, receive, send):
    """uvicorn 需要 lifespan；Django 默认不实现，这里补上以免启动告警。"""
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    await django_application(scope, receive, send)
