from asyncio import sleep
from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import BaseMiddleware, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Message
from aiogram_album import AlbumMessage


class OneMessageMiddleware(BaseMiddleware):
    def __init__(self, router: Optional[Router], one_message_states: list[str], latency: float = 1):
        self.latency = latency
        self.one_message_states = one_message_states
        self.last_message_time = {}
        self.messages: dict[int, int] = {}
        if router:
            router.message.outer_middleware(self)
            router.channel_post.outer_middleware(self)

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: Message | AlbumMessage, data: Dict[str, Any]) -> Any:
        state: FSMContext = data['state']
        current_state = await state.get_state()

        if current_state in self.one_message_states:
            user_id = event.from_user.id

            try:
                self.messages[user_id] += 1
                return
            except KeyError:
                self.messages[user_id] = 1
                await sleep(self.latency)
                data['msg_count'] = self.messages.pop(user_id)

        return await handler(event, data)
