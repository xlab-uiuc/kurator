from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from kurator.routes.utils import templates

router = APIRouter()

@router.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user_first_name": user['given_name']}
        )
    return RedirectResponse(url='/login')
