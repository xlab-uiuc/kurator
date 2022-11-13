import json
from pathlib import Path

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import kurator.auth

app = FastAPI()
app.static_dir = Path(__file__).parent / 'static'
app.templates_dir = Path(__file__).parent / 'templates'
app.mount("/static", StaticFiles(directory=app.static_dir), name="static")

app.templates = Jinja2Templates(directory=app.templates_dir)

kurator.auth.setup(app)

@app.get('/')
async def homepage(request: Request, response_class=HTMLResponse):
    user = request.session.get('user')
    if user:
        return app.templates.TemplateResponse(
            "index.html",
            {"request": request, "user_first_name": user['given_name']}
        )
    return RedirectResponse(url='/login')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("kurator.app:app", host="0.0.0.0", port=8000, log_level="debug", reload=True)