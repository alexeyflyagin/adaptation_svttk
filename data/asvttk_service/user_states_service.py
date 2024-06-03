from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data.asvttk_service.database import database
from data.asvttk_service.models import UserStateOrm


async def __create_user_state(s: AsyncSession, user_id: int, chat_id: int):
    user_state = UserStateOrm(user_id=user_id, chat_id=chat_id, state=None, data=dict())
    s.add(user_state)
    await s.commit()


async def __get_user_state_or_create(s: AsyncSession, user_id: int, chat_id: int) -> UserStateOrm:
    where = (UserStateOrm.user_id == user_id, UserStateOrm.chat_id == chat_id)
    res = await s.execute(select(UserStateOrm).filter(*where))
    user_state = res.scalar_one_or_none()
    if not user_state:
        await __create_user_state(s, user_id, chat_id)
        res = await s.execute(select(UserStateOrm).filter(*where))
        user_state = res.scalar_one_or_none()
    return user_state


async def set_state(user_id: int, chat_id: int, state: str | None):
    async with database.session_factory() as session:
        user_state = await __get_user_state_or_create(session, user_id, chat_id)
        user_state.state = state
        await session.commit()


async def set_data(user_id: int, chat_id: int, data: dict):
    async with database.session_factory() as session:
        user_state = await __get_user_state_or_create(session, user_id, chat_id)
        user_state.data = data
        await session.commit()


async def get_state(user_id: int, chat_id: int) -> str | None:
    async with database.session_factory() as session:
        user_state = await __get_user_state_or_create(session, user_id, chat_id)
        return user_state.state


async def get_data(user_id: int, chat_id: int) -> dict:
    async with database.session_factory() as session:
        user_state = await __get_user_state_or_create(session, user_id, chat_id)
        return user_state.data



