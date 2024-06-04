from src import commands

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


ROLES = f"""Выберите существующую роль или создайте новую."""

ROLES__EMPTY = f"""Вы пока не создали ни одной роли. Создайте первую роль."""


SESSION_ERROR = f"""Ошибка! Истек срок сессии."""

ACTION_CANCELED = f"""Действие отменено."""

CREATE_ROLE__ENTER_NAME = f"""Введите название роли.
<i>(Максимум 15 символов)</i>
/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__ENTER_NAME__TOO_LONGER_ERROR = f"""<b>Ошибка!</b> Это слишком длинное название <i>(Максимум 15 символов)</i>. Попробуйте еще раз.
/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__ENTER_NAME__UNIQUE_NAME_ERROR = f"""<b>Ошибка!</b> Роль с таким названием уже существует. Попробуйте еще раз.
/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__SUCCESS = f"""Новая роль с именем '<code>{{role_name}}</code>' успешно создана!"""


ROLE__RENAME = f"""Введите новое название для роли '<code>{{role_name}}</code>'.
<i>(Максимум 15 символов)</i>
/{commands.ROLES.command} - {commands.ROLES.description}"""

ROLE__RENAME__SUCCESS = f"""Название роли успешно сменено!"""


ROLE = f"""Роль '<code>{{role_name}}</code>'
Дата создания: <code>{{date_create}}</code>
Сотрудники: {{employees_list}}
Курсы: {{trainings_list}}"""

ROLE_DELETE = f"""После подтверждения действия, роль будет навсегда удалена! Она удалиться у всех участников, которым была присвоена.
—
Вы действительно хотите удалить роль 
'<code>{{role_name}}</code>'?"""

ROLE_DELETED = f"""Роль '{{role_name}}' удалена!"""

ROLE__NOT_FOUND = f"""<b>Ошибка!</b> Роль не найдена."""


BTN_ADD = "+ Добавить"
BTN_BACK = "« Назад"
BTN_DELETE_YES = "Да, всё верно!"
BTN_DELETE_NO = "Нет"
BTN_DELETE_NO_1 = "Отменить!"
BTN_DELETE_BACK = "« Назад"
BTN_DELETE = "Удалить"
BTN_RENAME = "Переименовать"

DATE_FORMAT_FULL = "%d.%m.%Y"
