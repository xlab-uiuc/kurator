from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from starlette.config import Config

from kurator.utils import validate_config, CodexModel

config = Config()
router = APIRouter()


class EditDataPoint(BaseModel):
    id: int | None = None
    username: str
    before_edit: str
    human_change_instruction: str
    after_edit: str
    gpt3_change_instruction: str = ""
    note: str = ""
    edited: bool = False
    deleted: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    tags: str = "[]"


class ValidateConfigsPayload(BaseModel):
    before: str
    after: str


def get_db(test_conn: bool = False) -> Engine:
    user = config.get('MYSQL_USER')
    password = config.get('MYSQL_PASSWORD')
    host = config.get('MYSQL_HOST')
    port = config.get('MYSQL_PORT')
    db = config.get('MYSQL_DATABASE')
    engine = None
    try:
        engine = create_engine(f'mysql://{user}:{password}@{host}:{port}/{db}')
        if test_conn:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        yield engine
    except Exception as e:
        if test_conn:
            raise e
    finally:
        if engine:
            engine.dispose()


########### CRUD of data points ###########


@router.get('/api/get_data_points')
def get_data_points(
    request: Request,
    username: str | None = None,
    include_deleted: bool = False,
    db: Engine = Depends(get_db), response_model=List[EditDataPoint]
):
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # TODO: handle `include_deleted`
    # TODO: handle `username` - should we allow users to see other users' data points?

    with db.connect() as conn:
        if username is None:
            data_points = conn.execute(
                text("SELECT * FROM edit_data_points WHERE Deleted = False")).fetchall()
        else:
            data_points = conn.execute(text(
                "SELECT * FROM edit_data_points WHERE Deleted = False AND username = :username"), {"username": username}).fetchall()

    return data_points


def get_instructions_from_gpt3(before_edit: str, after_edit: str) -> str:
    # TODO: Implement this
    return ""


@router.post('/api/add_data_point')
async def add_data_point(request: Request, data_point: EditDataPoint, db: Engine = Depends(get_db)):
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Unauthorized")

    editing_user = request.session.get('user')['email']

    # sanity checks:
    if data_point.after_edit.strip() == data_point.before_edit.strip():
        raise HTTPException(
            status_code=400, detail="after_edit is the same as before_edit")

    if data_point.human_change_instruction.strip() == "":
        raise HTTPException(
            status_code=400, detail="human_change_instruction is empty")

    data_point.username = editing_user
    data_point.gpt3_change_instruction = get_instructions_from_gpt3(
        data_point.before_edit, data_point.after_edit)
    data_point.edited = data_point.human_change_instruction.strip(
    ) != data_point.gpt3_change_instruction.strip()

    # TODO: validate config
    # TODO: compute tags

    with db.begin() as conn:
        cols = ["username", "before_edit", "human_change_instruction",
                "after_edit", "gpt3_change_instruction", "edited", "note"]
        if (
            data_point.id is not None and
            (str(data_point.id).isdigit() or isinstance(data_point.id, int)) and
            int(data_point.id) > 0
        ):
            # check if the id exists, and if so, whether the username matches
            existing_data_point = conn.execute(text(
                "SELECT * FROM edit_data_points WHERE id = :id"), {"id": data_point.id}).fetchone()
            if existing_data_point is None:
                raise HTTPException(
                    status_code=400, detail="id does not exist")
            if existing_data_point['username'] != editing_user:
                raise HTTPException(
                    status_code=400, detail="username does not match")
            cols = ["id"] + cols

        # insert or update - mysql syntax
        conn.execute(text('REPLACE INTO edit_data_points ({}) VALUES ({})'.format(
            ', '.join(cols),
            ', '.join([':' + col for col in cols])
        )), data_point.dict())

        return {"success": True}


@router.post('/api/del_data_point')
async def del_data_point(request: Request, data_point_id: int, db: Engine = Depends(get_db)):
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Unauthorized")

    editing_user = request.session.get('user')['email']

    # sanity checks:
    if not (str(data_point_id).isdigit() or isinstance(data_point_id, int)) or int(data_point_id) <= 0:
        raise HTTPException(status_code=400, detail="id is invalid")

    with db.begin() as conn:
        # check if the id exists, and if so, whether the username matches
        existing_data_point = conn.execute(text(
            "SELECT * FROM edit_data_points WHERE id = :id"), {"id": data_point_id}).fetchone()
        if existing_data_point is None:
            raise HTTPException(status_code=400, detail="id does not exist")
        if existing_data_point['username'] != editing_user:
            raise HTTPException(
                status_code=400, detail="username does not match")

        conn.execute(text('UPDATE edit_data_points SET Deleted = True WHERE id = :id'), {
                     "id": data_point_id})

        return {"success": True}


########### Validation ###########


@router.post('/api/validate_configs')
def validate_configs_api(
    request: Request,
    payload: ValidateConfigsPayload,
):
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Unauthorized")

    before_error = validate_config(payload.before)
    after_error = validate_config(payload.after)

    return {
        "before_error": before_error,
        "after_error": after_error
    }
