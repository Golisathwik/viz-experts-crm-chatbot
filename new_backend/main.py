from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from new_backend.api.auth_api import router as auth_router
from new_backend.api.chat_api import router as chat_router
from new_backend.api.config_api import router as config_router
from new_backend.api.session_api import router as session_router
from new_backend.api.settings_api import router as settings_router
from new_backend.database.schema import initialize_database
from new_backend.api.transcribe_api import router as transcribe_router
from new_backend.config.settings import settings
from new_backend.api.zoho_oauth_api import (
    router as zoho_oauth_router
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

initialize_database()


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(session_router)
app.include_router(settings_router)
app.include_router(transcribe_router)
app.include_router(zoho_oauth_router)

STATIC_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "static"
)

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

@app.get("/", response_class=HTMLResponse)
def home():

    index_path = os.path.join(
        STATIC_DIR,
        "index.html"
    )

    if os.path.exists(index_path):

        with open(
            index_path,
            "r",
            encoding="utf-8"
        ) as f:

            return HTMLResponse(f.read())

    return HTMLResponse(
        "<h2>Frontend not found.</h2>"
    )