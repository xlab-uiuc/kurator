from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from starlette.config import Config

config = Config()
router = APIRouter()


class EditDataPoint(BaseModel):
    id: int
    username: str
    before_edit: str
    human_change_instruction: str
    after_edit: str
    gpt3_change_instruction: str = ""
    note: str = ""
    edited: bool = False
    deleted: bool = False
    created_at: str
    updated_at: str
    tags: str


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


@router.get('/api/get_data_points')
def get_data_points(
    user_email: str | None = None,
    db: Engine = Depends(get_db), response_model=List[EditDataPoint]
):
    with db.connect() as conn:
        if user_email is None:
            data_points = conn.execute(
                text("SELECT * FROM edit_data_points WHERE Deleted = False")).fetchall()
        else:
            data_points = conn.execute(text(
                "SELECT * FROM edit_data_points WHERE Deleted = False AND user_email = :user_email"), {"user_email": user_email}).fetchall()

    return data_points
