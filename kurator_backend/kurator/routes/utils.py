from pathlib import Path
from fastapi.templating import Jinja2Templates

static_dir = Path(__file__).parent.parent / 'static'

templates_dir = Path(__file__).parent.parent / 'templates'
templates = Jinja2Templates(directory=templates_dir)