from aiogram.types import BotCommand

START = BotCommand(command="start", description="Войти в аккаунт")
HELP = BotCommand(command="help", description="Справка о коммандах и возможностях")

ROLES = BotCommand(command="roles", description="Роли")
EMPLOYEES = BotCommand(command="employees", description="Сотрудники")
TRAININGS = BotCommand(command="trainings", description="Курсы")
