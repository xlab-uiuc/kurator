import httpx
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
oauth.register(
    name='github',
    client_id=config.environ["GITHUB_CLIENT_ID"],
    client_secret=config.environ["GITHUB_CLIENT_SECRET"],
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email read:user'},
)   

@router.get('/login')
async def login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/')
    if config.environ["USE_FAKE_AUTH"].lower() in ["true", "1"]:
        request.session['user'] = {"given_name": "Test", "email": "test@test.com"}
    return templates.TemplateResponse("login.html", {"request": request})

@router.get('/login/google')
async def google_login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/')
    redirect_uri = request.base_url.replace(path='/auth/google/callback')._url
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/google/callback')
async def google_auth_cb(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        request.session.clear()
        return RedirectResponse(url='/login')
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@router.get('/login/github')
async def github_login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/')
    redirect_uri = request.base_url.replace(path='/auth/github/callback')._url
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get('/auth/github/callback')
async def github_auth_cb(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
    except OAuthError as error:
        request.session.clear()
        return RedirectResponse(url='/login')
    access_token = token.get('access_token')
    # use requests to make a call api.github.com/user with access_token
    
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.github.com/user', headers={
            "Authorization": "Bearer " + access_token,
        })
        user = response.json()
        user = {"given_name": user["name"], "email": user["email"]}

    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')
