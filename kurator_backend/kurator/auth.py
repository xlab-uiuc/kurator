from fastapi import FastAPI
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

config = Config()
oauth = OAuth(config)


def setup(app: FastAPI):
    app.add_middleware(SessionMiddleware,
                       secret_key=config.environ["AUTH_SECRET_KEY"])

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='google',
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    @app.get('/login')
    async def login(request: Request):
        if request.session.get('user'):
            return RedirectResponse(url='/')
        return app.templates.TemplateResponse("login.html", {"request": request})

    @app.get('/login/google')
    async def google_login(request: Request):
        if request.session.get('user'):
            return RedirectResponse(url='/')
        redirect_uri = request.base_url.replace(path='/auth/callback')._url
        return await oauth.google.authorize_redirect(request, redirect_uri)

    @app.get('/auth/callback')
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

    @app.get('/logout')
    async def logout(request: Request):
        request.session.pop('user', None)
        return RedirectResponse(url='/')
