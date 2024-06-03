import time
import uuid


def generate_access_key() -> str:
    return str(uuid.uuid4()).replace("-", "")[16:]


def generate_session_token() -> str:
    return f'{str(uuid.uuid4()).replace("-", "")}'


def get_current_time() -> int:
    return int(time.time())
