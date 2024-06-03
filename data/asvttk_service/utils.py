import random
import time
import uuid
from enum import Enum
from typing import Any, Optional


def generate_access_key() -> str:
    return str(uuid.uuid4()).replace("-", "")


def generate_session_token(user_id: int) -> str:
    return f'{int(user_id)}:{str(uuid.uuid4()).replace("-", "")}'


def get_current_time() -> int:
    return int(time.time())