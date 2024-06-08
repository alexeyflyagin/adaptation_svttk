from typing import Dict, Any, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from data.asvttk_service import user_states_service
from data.asvttk_service.database import database


TOKEN = "token"


class CustomStorage(BaseStorage):

    def __init__(self, ignore_users_id: Optional[list[int]] = None):
        self.ignore_users_id = ignore_users_id if ignore_users_id else []

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        if key.user_id in self.ignore_users_id:
            return
        new_state = state.state if state else None
        await user_states_service.set_state(user_id=key.user_id, chat_id=key.chat_id, state=new_state)

    async def get_state(self, key: StorageKey) -> Optional[str]:
        if key.user_id in self.ignore_users_id:
            return None
        return await user_states_service.get_state(user_id=key.user_id, chat_id=key.chat_id)

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        if key.user_id in self.ignore_users_id:
            return
        await user_states_service.set_data(user_id=key.user_id, chat_id=key.chat_id, data=data)

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        if key.user_id in self.ignore_users_id:
            return dict()
        return await user_states_service.get_data(user_id=key.user_id, chat_id=key.chat_id)

    async def close(self) -> None:
        await database.disconnect()
