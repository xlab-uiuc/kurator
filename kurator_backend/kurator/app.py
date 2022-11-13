from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware

import kurator.routes.auth as auth
import kurator.routes.db as db
import kurator.routes.home as home
import kurator.routes.utils as rutils

config = Config()

app = FastAPI()
app.add_middleware(SessionMiddleware,
                   secret_key=config.environ["AUTH_SECRET_KEY"])

app.mount("/static", StaticFiles(directory=rutils.static_dir), name="static")

# Initialize the routes
app.include_router(auth.router)
app.include_router(db.router)
app.include_router(home.router)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("kurator.app:app", host="0.0.0.0",
                port=8000, log_level="debug", reload=True)
