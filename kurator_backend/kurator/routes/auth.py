from fastapi import APIRouter
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

from kurator.routes.utils import templates

config = Config()
oauth = OAuth(config)

router = APIRouter()

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get('/login')
async def login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/')
    return templates.TemplateResponse("login.html", {"request": request})

@router.get('/login/google')
async def google_login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/')
    redirect_uri = request.base_url.replace(path='/auth/callback')._url
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/callback')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        request.session.clear()
        return RedirectResponse(url='/login')
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')
