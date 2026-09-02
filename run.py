import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gateway.settings")

import uvicorn

from config import ROOT_DIR, settings

if __name__ == "__main__":
    uvicorn.run(
        "gateway.asgi:application",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=[str(ROOT_DIR)],
        reload_excludes=[".venv", ".git", "sandbox"],
    )
