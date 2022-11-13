from pathlib import Path

import kurator.auth as auth
import kurator.db as db

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

config = Config()

app = FastAPI()
app.add_middleware(SessionMiddleware,
                   secret_key=config.environ["AUTH_SECRET_KEY"])

app.static_dir = Path(__file__).parent / 'static'
app.mount("/static", StaticFiles(directory=app.static_dir), name="static")

app.templates_dir = Path(__file__).parent / 'templates'
app.templates = Jinja2Templates(directory=app.templates_dir)

# Initialize the routes
app.include_router(auth.router)
app.include_router(db.router)


@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        return app.templates.TemplateResponse(
            "index.html",
            {"request": request, "user_first_name": user['given_name']}
        )
    return RedirectResponse(url='/login')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("kurator.app:app", host="0.0.0.0",
                port=8000, log_level="debug", reload=True)
