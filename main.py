import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram_album.no_check_count_middleware import WithoutCountCheckAlbumMiddleware

from handlers import handlers
from config import settings


async def main():
    bot_properties = DefaultBotProperties(parse_mode="HTML")
    bot = Bot(token=settings.BOT_TOKEN, default=bot_properties)
    db = Dispatcher()
    WithoutCountCheckAlbumMiddleware(router=db)
    db.include_router(handlers.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await db.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
