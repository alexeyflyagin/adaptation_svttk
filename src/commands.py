from aiogram.types import BotCommand

START = BotCommand(command="start", description="войти в аккаунт (ключ доступа)")
HELP = BotCommand(command="help", description="помощь")
CANCEL = BotCommand(command="cancel", description="отменить текущее действие")

ROLES = BotCommand(command="roles", description="роли")
EMPLOYEES = BotCommand(command="employees", description="сотрудники")
TRAININGS = BotCommand(command="trainings", description="курсы")

MYACCOUNT = BotCommand(command="myaccount", description="мой профиль")
RESTART = BotCommand(command="restart", description="перезапустить")
