import datetime
import traceback
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from starlette.config import Config

from kurator.utils import validate_config, ROOT_PATH

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

############ Helper functions ############

def get_current_user(request: Request) -> Dict[str, Any]:
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

########### CRUD of data points ###########


@router.get('/api/get_data_points')
def get_data_points(
    request: Request,
    username: str | None = None,
    include_deleted: bool = False,
    db: Engine = Depends(get_db), response_model=List[EditDataPoint],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
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
async def add_data_point(
    request: Request,
    data_point: EditDataPoint,
    db: Engine = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    editing_user = current_user['email']

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
async def del_data_point(
    request: Request,
    data_point_id: int,
    db: Engine = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    editing_user = current_user['email']

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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    validation_errors = []

    try:
        before_error = validate_config(payload.before)
    except Exception as e:
        print("Error while validating before", traceback.format_exc())
        before_error = ""
        validation_errors.append(("before", traceback.format_exc()))

    try:
        after_error = validate_config(payload.after)
    except Exception as e:
        print("Error while validating after", traceback.format_exc())
        after_error = ""
        validation_errors.append(("after", traceback.format_exc()))

    if len(validation_errors):
        # log the data, user, and error
        with open(ROOT_PATH / "validation_errors.log", "a") as f:
            f.write(f"{datetime.datetime.now()}\n")
            f.write(f"User: {current_user['email']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"**Before**:\n{payload.before}\n")
            f.write("-" * 80 + "\n")
            f.write(f"**After**:\n{payload.after}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Errors:\n")
            for error in validation_errors:
                f.write(f"**{error[0]}**:\n{error[1]}\n")
            f.write("=" * 80 + "\n")
            f.write("\n")

    return {
        "before_error": before_error,
        "after_error": after_error,
        "validation_error": len(validation_errors) > 0,
    }
