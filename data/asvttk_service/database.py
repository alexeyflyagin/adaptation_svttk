from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from data.asvttk_service.models import AccountOrm, Base, KeyOrm, AccountType


async def is_foreign_key(session: AsyncSession, value: bool):
    value_str = "ON" if value else "OFF"
    await session.execute(text(f"PRAGMA foreign_keys = {value_str}"))


class ASVTTKDatabase:
    def __init__(self, url: str, admin_access_key: str):
        self.engine = create_async_engine(url, echo=False)
        self.session_factory = async_sessionmaker(self.engine)
        self.admin_access_key = admin_access_key

    async def connect(self, drop_all: str = "no"):
        async with self.engine.begin() as conn:
            if drop_all.lower() == "yes":
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with self.session_factory() as service:
            res = await service.execute(select(AccountOrm))
            if res.scalars().first() is None:
                await self.__first_connect()
                await service.commit()

    async def __first_connect(self):
        async with self.session_factory() as service:
            admin_acc = AccountOrm(type=AccountType.ADMIN, first_name="ADMIN")
            service.add(admin_acc)
            await service.flush()
            key = KeyOrm(access_key=self.admin_access_key, account_id=admin_acc.id, is_first_log_in=True)
            service.add(key)
            await service.commit()

    async def disconnect(self):
        await self.engine.dispose()


database = ASVTTKDatabase(url=settings.ASVTTK_DATABASE_URL, admin_access_key=settings.ADMIN_ACCESS_KEY)
