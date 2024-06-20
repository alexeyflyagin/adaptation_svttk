import asyncio
from asyncio import CancelledError

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram_album.no_check_count_middleware import WithoutCountCheckAlbumMiddleware

import config
from custom_storage import CustomStorage
from data.asvttk_service.database import database
from handlers import main_handlers, trainings_handlers, admin_roles_handlers, my_account_handlers, \
    admin_employees_handlers, student_handlers, last_handlers, authorization_handlers
from config import settings


async def main():
    # logging.basicConfig(level=logging.INFO)
    bot_properties = DefaultBotProperties(parse_mode="HTML")
    bot = Bot(token=settings.BOT_TOKEN, default=bot_properties)
    storage = CustomStorage(ignore_users_id=[bot.id])
    dispatcher = Dispatcher(storage=storage)
    WithoutCountCheckAlbumMiddleware(router=dispatcher, latency=0.5)
    dispatcher.include_routers(main_handlers.router, authorization_handlers.router, trainings_handlers.router,
                               admin_roles_handlers.router, my_account_handlers.router, admin_employees_handlers.router,
                               student_handlers.router, last_handlers.router)
    student_handlers.bot = bot
    try:
        await bot.set_my_commands(config.BOT_COMMANDS)
        await database.connect(drop_all="ye")
        await bot.delete_webhook(drop_pending_updates=True)
        print("bot started")
        await dispatcher.start_polling(bot)
    except CancelledError:
        print("bot ended")
        await storage.close()


if __name__ == '__main__':
    asyncio.run(main())
