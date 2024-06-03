import commands

LOG_IN__SUCCESS = """Вы успешно вошли в аккаунт."""

LOG_IN__SUCCESS__FIRST = f"""{LOG_IN__SUCCESS}
Вы зашли в аккаунт впервые. В целях безопасности был присвоен новый ключ: <code>{{key}}</code>.
Новая ссылка для входа в аккаунт: {{key_link}}"""

LOG_IN__ACCOUNT_NOT_FOUND = """
<b>Ошибка!</b> Аккаунт не найден.
"""

LOG_IN__NO_ACCESS_KEY = """
<b>Ошибка!</b> Вы не указали ключ доступа.
"""

HELP__NO_AUTHORIZATION = """Для начала необходимо войти в аккаунт по ссылке, содержащей в себе ключ доступа."""


HELP__ADMIN = f"""
/{commands.EMPLOYEES.command} - {commands.EMPLOYEES.description}
/{commands.ROLES.command} - {commands.ROLES.description}
/{commands.TRAININGS.command} - {commands.TRAININGS.description}
"""
