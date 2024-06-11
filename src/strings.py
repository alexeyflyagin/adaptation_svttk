from src import commands


def code(it: str):
    return f"<code>{it}</code>"


# BTNs
BTN_CREATE = "+ Создать"
BTN_ADD = "+ Добавить"
BTN_BACK = "« Назад"
BTN_SAVE = "✓ Сохранить"
BTN_SAVE_SYMBOL = "✓"
BTN_DELETE_YES = "Да, всё верно!"
BTN_DELETE_NO = "Нет"
BTN_DELETE_NO_1 = "Отменить!"
BTN_DELETE_BACK = "« Назад"
BTN_DELETE = "Удалить"
BTN_EDIT_EMAIL = "Изм. email"
BTN_RENAME = "Переименовать"
BTN_INVITE = "Пригласить"
BTN_PIN = "Закрепить"
BTN_LOG_IN = "Войти"
BTN_ROLES = "Роли"


# DateFormats
DATE_FORMAT_FULL = "%d.%m.%Y"


# General
SESSION_ERROR = f"""Ошибка! Истек срок сессии."""

ACTION_CANCELED = f"""Действие отменено."""


# LogIn
LOG_IN__SUCCESS = f"""Вы успешно вошли в аккаунт! 
Добрый день, <code>{{first_name}}</code>. 

/{commands.HELP.command} - {commands.HELP.description}"""

LOG_IN__SUCCESS__FIRST = f"""Вы зашли в аккаунт впервые. В целях безопасности был присвоен новый ключ доступа.
Ключ доступа:  <tg-spoiler>{{access_key}}</tg-spoiler>
<i>(Храните ключ доступа в безопасном месте!)</i>

Нажмите '<code>{BTN_PIN}</code>', чтобы не потерять данные для входа."""


LOG_IN__DATA__PINED = f"""Ваши данные для входа, <code>{{first_name}}</code>.
Ключ доступа:  <tg-spoiler>{{access_key}}</tg-spoiler>
<i>(Храните ключ доступа в безопасном месте!)</i>

Нажмите '<code>{BTN_LOG_IN}</code>' чтобы войти в этот аккаунт."""


LOG_IN__ACCOUNT_NOT_FOUND = """
<b>Ошибка!</b> Аккаунт не найден.
"""

LOG_IN__NO_ACCESS_KEY = """
<b>Ошибка!</b> Вы не указали ключ доступа.
"""


# Help
HELP__NO_AUTHORIZATION = """Для начала необходимо войти в аккаунт по ссылке, содержащей в себе ключ доступа."""


HELP__ADMIN = f"""Список команд, доступных вам.

Мой аккаунт
/{commands.MYACCOUNT.command} - {commands.MYACCOUNT.description}

Основное
/{commands.EMPLOYEES.command} - {commands.EMPLOYEES.description}
/{commands.ROLES.command} - {commands.ROLES.description}
/{commands.TRAININGS.command} - {commands.TRAININGS.description}
"""

HELP__EMPLOYEE = f"""Список команд, доступных вам.

Мой аккаунт
/{commands.MYACCOUNT.command} - {commands.MYACCOUNT.description}

Основное
/{commands.TRAININGS.command} - {commands.TRAININGS.description}
"""


# roles
ROLES = f"""Выберите существующую роль или создайте новую."""

ROLES__EMPTY = f"""Список ролей пуст. Создайте первую роль."""


CREATE_ROLE__ENTER_NAME = f"""Введите название роли.
<i>(Максимум 15 символов)</i>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__ENTER_NAME__TOO_LONGER_ERROR = f"""<b>Ошибка!</b> Это слишком длинное название <i>(Максимум 15 символов)</i>. Попробуйте еще раз.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__ENTER_NAME__UNIQUE_NAME_ERROR = f"""<b>Ошибка!</b> Роль с таким названием уже существует. Попробуйте еще раз.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_ROLE__ERROR_FORMAT = f"""<b>Ошибка!</b> Формат названия для роли некорректен. Попробуйте еще раз.

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

ROLE__NOT_FOUND = f"""Ошибка! Роль не найдена."""


# Employees
EMPLOYEES_ITEM = """<b>{index}</b>  <b>{full_name}</b>
{roles}"""

EMPLOYEES_ITEM__ROLES_EMPTY = """<i>(Нет ролей)</i>"""

EMPTY_FIELD = """-"""

EMPLOYEES = """
{items}
—
Выберите сотрудника.
"""

EMPLOYEES__EMPTY = """Список сотрудников пуст. Добавьте первого сотрудника."""

CREATE_EMPLOYEE = f"""Введите <b>ФИО</b> сотрудника.
Пример:  <code>Иванов Иван -</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_EMPLOYEE__ERROR_FORMAT = f"""<b>Ошибка!</b> Формат ФИО некорректен. Попробуйте еще раз.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_EMPLOYEE__SUCCESS = f"""Аккаунт для сотрудника готов!

Ключ доступа: <tg-spoiler>{{access_key}}</tg-spoiler>

<code>{{access_link}}</code>

Пригласите пользователя, нажав '<code>Пригласить</code>'."""


EMPLOYEE = """Сотрудник
Добавлен:  <code>{date_create}</code>
Фамилия:  <code>{last_name}</code>
Имя:  <code>{first_name}</code>
Отчество:  <code>{patronymic}</code>
Email: {email}
Роли:  {roles_list}"""

EMPLOYEE__NOT_FOUND = """Ошибка! Сотрудник не найден."""

EMPLOYEE__DELETED = """Сотрудник успешно удален."""

EMPLOYEE_DELETE = f"""После подтверждения действия, сотрудник будет навсегда удален!
—
Вы действительно хотите удалить сотрудника
<code>{{full_name}}</code>?"""

EMPLOYEE_INVITE = f"""Приглашаю вас в аккаунт сотрудника.
Присоединяйтесь, перейдя по ссылке: {{invite_link}}"""

EMPLOYEE__EDIT_EMAIL = f"""Введите <b>email</b>.
Пример: <code>ivanov_ivan66@email.ru</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

EMPLOYEE__EDIT_EMAIL__SUCCESS = f"""Email сотрудника успешно изменен!"""

EMPLOYEE__ROLES__REMOVED = """Роль '{role_name}' отвязана от аккаунта."""

EMPLOYEE__ROLES__ADDED = """Роль '{role_name}' привязана к аккаунту."""

EMPLOYEE__ALL_ROLES = f"""Выбери роль, которую хочешь добавить."""

EMPLOYEE__ALL_ROLES__FULL = f"""Вы добавили все роли. Вы можете создать новую роль.

/{commands.ROLES.command} - {commands.ROLES.description}"""

EMPLOYEE__ALL_ROLES__NOT_FOUND = f"""Ролей нет. Сначала добавьте их.

/{commands.ROLES.command} - {commands.ROLES.description}"""

EMPLOYEE__ROLES = f"""Все роли аккаунта  <code>{{full_name}}</code>.
—
Нажми на роль, чтобы отвязать её."""

EMPLOYEE__EDIT_EMAIL__EMAIL_ERROR = f"""<b>Ошибка!</b> Email должен содержать '<code>@</code>'.
Пример: <code>ivanov_ivan66@email.ru</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""


# Trainings
TRAININGS_ITEM = """<b>{index}</b>  <b>{title}</b>
<i>{status} | {student_counter}</i>"""

TRAININGS = """
{items}
—
Выбирете существующий курс или создайте новый."""

TRAININGS__EMPTY = """Список курсов пуст. Создайте первый курс."""

TRAININGS__UNAVAILABLE = """У вас нет доступа к курсам."""

TRAINING_STATUS__INACTIVE = """Не запущен"""
TRAINING_STATUS__ACTIVE = """Активный"""
TRAINING_STATUS__COMPLETED = """Завершен"""

CREATE_TRAINING__NAME = f"""Введите название нового курса.
(Рекомендуемая длинна: 2-3 слова)

/{commands.CANCEL.command} - {commands.CANCEL.description}"""


CREATE_TRAINING__ROLE = f"""Выберите роль, которой будет привязан курс.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""


CREATE_TRAINING__ROLE__SELECTED = f"""Выберите роль, которой будет привязан курс.

Выбрана роль '<code>{{role_name}}</code>'."""


CREATE_TRAINING__CREATED = f"""Новый курс успешно создан."""

