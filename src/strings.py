from html import escape
from typing import Optional

from aiogram.types import BotCommand

from src import commands


def code(it: str):
    return f"<code>{it}</code>"


def eschtml(it: str):
    return escape(it) if it else it


def italic(it: str):
    return f"<i>{it}</i>"


def item_id(it: int):
    return f"[<code>ID:{it}</code>]"


def blockquote(it: str, expand: bool = True):
    if expand:
        return f"<blockquote expandable>{it}</blockquote>"
    else:
        return f"<blockquote>{it}</blockquote>"


def command(it: "BotCommand", no_description: bool = False) -> str:
    if no_description:
        return f"/{it.command}"
    return f"/{it.command} - {it.description}"


def error_value(error_msg: str) -> str:
    return ERROR__VALUE__CANCELED.format(error_msg=error_msg)


# BTNs
BTN_CREATE = "+ Создать"
BTN_ADD = "+ Добавить"
BTN_BACK = "« Назад"
BTN_EDIT = "Изменить"
BTN_EDIT_CONTENT = "Изм. Контент"
BTN_EDIT_TITLE = "Изм. Заголовок"
BTN_SAVE = "✓ Сохранить"
BTN_READ_IT = "Я прочитал(а)"
BTN_REGENERATE = "Сгенерировать новый"
BTN_CLOSE = "X  Сохранить"
BTN_SAVE_SYMBOL = "✓"
BTN_ADD_SYMBOL = "+"
BTN_DELETE_YES = "Да, всё верно!"
BTN_DELETE_NO = "Нет"
BTN_DELETE_NO_1 = "Отменить!"
BTN_DELETE_BACK = "« Назад"
BTN_PREVIOUS_SYMBOL = "«"
BTN_NEXT_SYMBOL = "»"
BTN_SHOW = "Показать"
BTN_DELETE = "Удалить"
BTN_LEVELS = "Уровни"
BTN_TRAININGS = "Курсы"
BTN_EDIT_EMAIL = "Изм. email"
BTN_EDIT_NAME = "Изм. название"
BTN_EDIT_FULL_NAME = "Изм. ФИО"
BTN_RENAME = "Переименовать"
BTN_INVITE = "Пригласить"
BTN_PIN = "Закрепить"
BTN_LOG_IN = "Войти"
BTN_LOG_OUT = "Выйти"
BTN_STUDENTS = "Ученики"
BTN_ROLES = "Роли"
BTN_TRAINING_START = "▶️  Запустить"
BTN_TRAINING_STOP = "⏹  Остановить"
BTN_BEGIN = "Начать!"
BTN_CONTINUE = "Продолжить"
BTN_ALREADY_READ = "Прочитано"
BTN_REPORT = "📗 Отчёт"
BTN_NEXT = "Далее"
BTN_ACCESS_KEY = "🔑 Ключ доступа"
BTN_GIVE_UP_ACCOUNT = "Отдать аккаунт"
BTN_SHOW_RESULTS = "Показать результаты"

# ContentType
CONTENT_TYPE__TEXT = "Текст"
CONTENT_TYPE__PHOTO = "Фото"
CONTENT_TYPE__VIDEO = "Видео"
CONTENT_TYPE__DOCUMENT = "Документ"
CONTENT_TYPE__AUDIO = "Аудиофайл"
CONTENT_TYPE__STICKER = "Стикер"
CONTENT_TYPE__ANIMATION = "GIF"
CONTENT_TYPE__MEDIA_GROUP = "Медиа-группа"
CONTENT_TYPE__CONTACT = "Контакт"
CONTENT_TYPE__LOCATION = "Геопозиция"
CONTENT_TYPE__POLL = "Опрос"
CONTENT_TYPE__POLL__QUIZ = "Опрос-викторина"


# General
SESSION_ERROR = f"""Ошибка! Истек срок сессии."""

TELEGRAM_IS_NOT_STABLE = f"""Сервера телеграма нестабильны. Попробуйте позже."""

ACTION_CANCELED = f"""Действие отменено."""

WAIT_CLEAR_PREVIOUS_SESSION = f"""🔴 Дождитесь завершение предыдущей сессии... 
Это может занять продолжительное время."""

WAIT_UPDATING = f"""🔴 Подождите, идет обновление..."""

ERROR__UNKNOWN = f"""Ошибка! Что-то пошло не так. Попробуйте позже..."""

ERROR__ACCESS = f"""Ошибка! У вас недостаточно прав."""

ERROR__VALUE__CANCELED = f"""<b>Ошибка!</b> {{error_msg}}

Попробуйте еще раз или отмените действие {command(commands.CANCEL, True)}."""

# LogIn
LOG_IN__SUCCESS = f"""👋  Добрый день, <code>{{first_name}}</code>."""

LOG_IN__WARNING__STUDENT = f"""⚠️  <b>Внимание:</b> Выйдя из этого аккаунта, вы больше не сможете вернуться в него снова!
—
Вы действительно хотите выйти из аккаунта?"""

LOG_OUT__WARNING = f"""⚠️  <b>Внимание:</b> Убедитесь, что вы сохранили ключ доступа для входа в этот аккаунт в следующий раз!

Сохранить ключ: /myaccount » {code(BTN_ACCESS_KEY)}

<b>Доступ к аккаунту будет утерян после выхода из него, если вы не сохраните ключ.</b>
—
Вы действительно хотите выйти из аккаунта?"""

LOG_IN__SUCCESS__FIRST = f"""⚠️  <b>Внимание:</b> Вы зашли в аккаунт впервые. Был присвоен новый ключ доступа.
<b>Доступ к аккаунту будет утерян после выхода из него, если вы не сохраните ключ.</b>

Сохранить ключ: /myaccount » {code(BTN_ACCESS_KEY)}"""

LOG_IN__DATA = f"""Ваши данные для входа, <code>{{first_name}}</code>.
Ключ доступа:  <tg-spoiler>{{access_key}}</tg-spoiler>
<i>(Храните ключ доступа в безопасном месте!)</i>

Нажмите '<code>{BTN_LOG_IN}</code>' чтобы войти в этот аккаунт."""

LOG_IN_DATA__INSTRUCTION = """📖  <b>Зачем это нужно?</b>
<i>Ключ доступа</i> - уникальный 16-значный код, дающий возможность войти в аккаунт.

<b>Что с ним делать?</b>
После подтверждения вам будет прислано сообщение на 1 минуту, содержащее в себе ключ доступа в удобном виде. Вам необходимо сохранить это сообщение, переслав его в любой безопасный чат."""

LOG_IN__ACCOUNT_NOT_FOUND = """
<b>Ошибка!</b> Аккаунт не найден. Возможно он был удален ранее.
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

VALUE_ERROR__ROLE__UNIQUE_NAME_ERROR = f"""Роль с таким именем уже существует."""

CREATE_ROLE__SUCCESS = f"""Новая роль с именем '<code>{{role_name}}</code>' успешно создана!"""

RENAME_ROLE__ENTER_NAME = f"""Введите новое название для роли '<code>{{role_name}}</code>'.
<i>(Максимум 15 символов)</i>

/{commands.ROLES.command} - {commands.ROLES.description}"""

ROLE__RENAME__SUCCESS = f"""Название роли успешно сменено!"""

ROLE = f"""Роль '<code>{{role_name}}</code>'  {{item_id}}
Дата создания: <code>{{date_create}}</code>
Сотрудники: {{employees_list}}
Курсы: {{trainings_list}}"""

ROLE_DELETE = f"""После подтверждения действия, роль будет навсегда удалена! Она удалиться у всех участников, которым была присвоена.
—
Вы действительно хотите удалить роль
'<code>{{role_name}}</code>'?"""

ROLE_DELETED = f"""Роль '{{role_name}}' удалена!"""

ROLE__NOT_FOUND = f"""Ошибка! Роль не найдена. Возможно она была удалена ранее."""

ROLE__TRAININGS = f"""Все курсы у роли  '<code>{{role_name}}</code>'.
—
Нажми на курс, чтобы отвязать его."""

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

CREATE_ACCOUNT__ERROR_FORMAT = f"""<b>Ошибка!</b> Формат ФИО некорректен. Попробуйте еще раз.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_EMPLOYEE__SUCCESS = f"""Аккаунт для сотрудника готов!

Ключ доступа: <tg-spoiler>{{access_key}}</tg-spoiler>
<code>{{access_link}}</code>

Пригласите пользователя, нажав '<code>Пригласить</code>'."""

EMPLOYEE = """Сотрудник  {item_id}
Фамилия:  <code>{last_name}</code>
Имя:  <code>{first_name}</code>
Отчество:  <code>{patronymic}</code>
Добавлен:  <code>{date_create}</code>
Email: {email}
Роли:  {roles_list}"""

EMPLOYEE__NOT_FOUND = """Ошибка! Сотрудник не найден. Возможно она был удален ранее."""

EMPLOYEE__DELETED = """Сотрудник успешно удален."""

EMPLOYEE_DELETE = f"""После подтверждения действия, сотрудник будет навсегда удален!
—
Вы действительно хотите удалить сотрудника
<code>{{full_name}}</code>?"""

EMPLOYEE_INVITE_LETTER = f"""Приглашаю вас в аккаунт сотрудника.
Присоединяйтесь, перейдя по ссылке: {{invite_link}}

❗️  Ссылка действует только один раз! После входа в аккаунт вам будет выдан постоянный ключ."""

ADMIN_INVITE_LETTER = f"""Приглашаю вас в аккаунт администратора.
Присоединяйтесь, перейдя по ссылке: {{invite_link}}

❗️  Ссылка действует только один раз! После входа в аккаунт вам будет выдан постоянный ключ."""

EDIT_EMAIL = f"""Введите <b>email</b>.
Пример: <code>ivanov_ivan66@email.ru</code> или <code>-</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

EDIT_FULL_NAME = f"""Введите новое <b>ФИО</b> сотрудника.
Пример:  <code>Иванов Иван -</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

EDIT_EMAIL__SUCCESS = f"""Email успешно изменен!"""

EDIT_FULL_NAME__SUCCESS = f"""ФИО успешно изменен!"""

EMPLOYEE__ROLES__REMOVED = """Роль '{role_name}' отвязана от аккаунта."""

EMPLOYEE__ROLES__ADDED = """Роль '{role_name}' привязана к аккаунту."""

EMPLOYEE__ALL_ROLES = f"""Выбери роль, которую хочешь добавить."""

EMPLOYEE__ALL_ROLES__FULL = f"""Вы добавили все роли. Вы можете создать новую.

/{commands.ROLES.command} - {commands.ROLES.description}"""

EMPLOYEE__ALL_ROLES__NOT_FOUND = f"""Ролей нет. Сначала добавьте их.

/{commands.ROLES.command} - {commands.ROLES.description}"""

EMPLOYEE__ROLES = f"""Все роли аккаунта  <code>{{full_name}}</code>.
—
Нажми на роль, чтобы отвязать её."""

# Trainings
TRAINING_IS_STARTED_ERROR = """Ошибка! Необходимо остановить курс."""

TRAINING_HAS_STUDENTS_ERROR = """Ошибка! Необходимо удалить всех учеников."""

TRAINING_IS_NOT_STARTED_ERROR = """Ошибка! Необходимо запустить курс."""

TRAININGS_ITEM = """<b>{index}</b>  <b>{title}</b>
{status} | Учеников: {student_counter}"""

TRAININGS = """
{items}
—
Выбирете существующий курс или создайте новый."""

TRAININGS__EMPTY = """Список курсов пуст. Создайте первый курс."""

TRAININGS__UNAVAILABLE = """У вас нет доступа к курсам."""

TRAINING_STATUS__INACTIVE = """<i>Не запущен</i>"""
TRAINING_STATUS__ACTIVE = """<b>Активный</b>"""

CREATE_TRAINING__NAME = f"""Введите название нового курса.
(Рекомендуемая длинна: 2-3 слова)

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_TRAINING__ROLE = f"""Выберите роль, которой будет привязан курс.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_TRAINING__ROLE__SELECTED = f"""Выберите роль, которой будет привязан курс.

Выбрана роль '<code>{{role_name}}</code>'."""

CREATE_TRAINING__CREATED = f"""Новый курс успешно создан."""

TRAINING__NOT_FOUND = """Курс не найден.  Возможно он был удален ранее."""

TRAINING = """<code>{name}</code>  {item_id}

Статус:  {status}
Дата создания:  <code>{data_create}</code>"""

TRAINING__DELETED = """Курс успешно удален."""

TRAINING__STARTED = """Курс успешно запущен."""

TRAINING__STARTED__ERROR__ALREADY_STARTED = """Ошибка! Курс уже запущен."""

TRAINING__STARTED__ERROR__TRAINING_IS_EMPTY = """Ошибка! Невозможно запустить курс без уровней."""

TRAINING__STARTED__ERROR__NOT_STARTED = """Ошибка! Курс не запущен."""

TRAINING__STOPPED = """Курс успешно остановлен."""

TRAINING__DELETE = f"""После подтверждения действия, курс будет навсегда удален!
—
Вы действительно хотите удалить курс
'<code>{{training_name}}</code>'?"""

TRAINING__START = f"""После подтверждения действия, курс будет недоступен для изменения! 
<b>Все ученики будут удалены!</b>
—
Вы действительно хотите запустить курс
'<code>{{training_name}}</code>'?"""

TRAINING__STOP = f"""После подтверждения действия, курс будет остновлен, а ученики больше не смогут проходить его!
—
Вы действительно хотите остановить курс
'<code>{{training_name}}</code>'?"""

TRAINING__EDIT_NAME = f"""Введите новое название для курса.
(Рекомендуемая длинна: 2-3 слова)

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

TRAINING__EDIT_NAME__SUCCESS = f"""Название курса успешно изменено!"""

TRAINING__EDIT_NAME__ERROR__INCORRECT_FORMAT = f"""<b>Ошибка!</b> Некорректный формат названия.

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

ROLE__TRAININGS__REMOVED = """Курс '{training_name}' успешно отвязан от роли."""

ROLE__TRAININGS__ADDED = """Курс '{training_name}' успешно привязан к роли."""

ROLE__ALL_TRAININGS = f"""Выбери курс, который хочешь добавить."""

ROLE__ALL_TRAININGS__FULL = f"""Вы добавили все курсы. Вы можете создать новый.

/{commands.TRAININGS.command} - {commands.TRAININGS.description}"""

ROLE__ALL_TRAININGS__NOT_FOUND = f"""Курсов нет. Сначала добавьте их.

/{commands.TRAININGS.command} - {commands.TRAININGS.description}"""

TRAININGS__LEVELS__ITEM__TYPE__START_I = """👋"""
TRAININGS__LEVELS__ITEM__TYPE__INFO_I = """▫️️"""
TRAININGS__LEVELS__ITEM__TYPE__QUIZ_I = """🔸"""

TRAININGS__LEVELS__ITEM__TYPE__INFO = "ИНФОРМАЦИЯ"
TRAININGS__LEVELS__ITEM__TYPE__QUIZ = "КОНТРОЛЬ"

TRAININGS__LEVELS__ITEM = """{type_icon}  <b>{index}</b>  {level_title}"""
TRAININGS__LEVELS__ITEM__NO_INDEX = """{type_icon}  {level_title}"""

TRAINING__LEVELS = f"""Список уровней курса '<code>{{training_name}}</code>'
—
{{items}}
—
Выберите уровень."""

ENTER__LEVEL__TITLE = f"""Введите заголовок для уровня.
(Рекомендуемая длинна: 2-3 слова)

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_LEVEL__TITLE__ERROR__INCORRECT_FORMAT = f"""<b>Ошибка!</b> Некорректный формат заголовка. Попробуйте еще раз.
(Рекомендуемая длинна: 2-3 слова)

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

ALLOW_LEVEL_CONTENT_TYPE_HELPER = f"""{code(TRAININGS__LEVELS__ITEM__TYPE__QUIZ)}:  <i>{CONTENT_TYPE__POLL__QUIZ}</i>
{code(TRAININGS__LEVELS__ITEM__TYPE__INFO)}:  <i>{CONTENT_TYPE__MEDIA_GROUP} (до 10 элементов)</i>, <i>{CONTENT_TYPE__TEXT}</i>, <i>{CONTENT_TYPE__PHOTO}</i>, <i>{CONTENT_TYPE__VIDEO}</i>, <i>{CONTENT_TYPE__DOCUMENT}</i>, <i>{CONTENT_TYPE__AUDIO}</i>, <i>{CONTENT_TYPE__STICKER}</i>, <i>{CONTENT_TYPE__ANIMATION}</i>, <i>{CONTENT_TYPE__CONTACT}</i>, <i>{CONTENT_TYPE__LOCATION}</i>"""

ALLOW_TRAINING_START_CONTENT_TYPE_HELPER = f"""Вы можете прислать {italic(CONTENT_TYPE__TEXT)} или {italic(CONTENT_TYPE__PHOTO)} (для первью)."""

CREATE_LEVEL__CONTENT__ERROR__INCORRECT_FORMAT = f"""<b>Ошибка!</b> Некорректный формат контента. Попробуйте еще раз.

{ALLOW_LEVEL_CONTENT_TYPE_HELPER}

/{commands.CANCEL.command} - {commands.CANCEL.description}"""


ENTER__LEVEL_CONTENT = f"""Пришлите контент для уровня <b>одним сообщением</b>.

{ALLOW_LEVEL_CONTENT_TYPE_HELPER}

/{commands.CANCEL.command} - {commands.CANCEL.description}"""


CREATE_LEVEL__SUCCESS = f"""Новый уровень успешно создан!"""

EDIT_CONTENT_LEVEL__SUCCESS = f"""Контент уровня успешно изменен!"""

EDIT_TITLE_LEVEL__SUCCESS = f"""Заголовок уровня успешно изменен!"""

LEVEL__NOT_FOUND = f"""Уровень не найден. Возможно он был удален ранее."""

LEVEL__ERROR__VIEW = f"""<b>Ошибка!</b> Не удалось отобразить уровень."""

LEVEL = f"""<code>{{training_name}}</code>  :  <code>{{level_name}}</code>  {{item_id}}
Дата создания:  <code>{{data_create}}</code>
Тип уровня:  {{level_type_icon}} <code>{{level_type}}</code>
Тип контента:  <code>{{content_type}}</code>"""

TRAINING__START_LEVEL = f"""{TRAININGS__LEVELS__ITEM__TYPE__START_I}  Начальное сообщение
Курс:  <code>{{training_name}}</code>
Превью:  {{has_preview}}

<i>Сообщение будет показано в самом начале обучения. Поприветствуйте ученика и расскажите ему про данный курс.</i>"""

LEVEL__DELETE = f"""После подтверждения действия, уровень будет навсегда удален!
—
Вы действительно хотите удалить уровень
'<code>{{level_name}}</code>' из курса '<code>{{training_name}}</code>'?"""

LEVEL__DELETED = f"""✅  Уровень '{{level_name}}' успешно удален!"""

LEVEL__NO_TEXT = "<i>(Текст отсутствует)</i>"

LEVEL__START_TEXT_DEFAULT = """Добро пожаловать на курс."""

TRAINING__START__EDIT__CONTENT = f"""Пришлите контент для начального сообщения <b>одним сообщением</b>.

{ALLOW_TRAINING_START_CONTENT_TYPE_HELPER}

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

TRAINING__START__EDIT__CONTENT__ERROR__INCORRECT_FORMAT = f"""<b>Ошибка!</b> Некорректный формат контента. Попробуйте еще раз.

{ALLOW_TRAINING_START_CONTENT_TYPE_HELPER}

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

TRAINING__START__EDIT__CONTENT__SUCCESS = f"""Контент начального сообщения успешно сменен!"""


# Students
STUDENT_NOT_FOUND = """Ученик не найден. Возможно он был удален ранее."""

STUDENT = f"""<b>Ученик</b>  {{item_id}}
Фамилия:  <code>{{last_name}}</code>
Имя:  <code>{{first_name}}</code>
Отчество:  <code>{{patronymic}}</code>
Дата создания:  <code>{{date_create}}</code>

Состояние:  <code>{{state}}</code>
Прогресс:  {{answer_count}} / {{level_count}}  ({{progress_percent}}%)"""

STUDENT_ITEM = """<b>{index}</b>  <b>{full_name}</b>
{state}  <i>({progress_percent}%)</i>"""

STUDENTS = f"""Список учеников курса '<code>{{training_name}}</code>'.
—
{{items}}
—
Выберите ученика или добавьте нового.
"""

STUDENT_STATUS__CREATED = "СОЗДАНО"
STUDENT_STATUS__LEARNING = "ОБУЧЕНИЕ"
STUDENT_STATUS__COMPLETED = "ЗАВЕРШЕНО"

STUDENTS__EMPTY = f"""Список учеников курса '<code>{{training_name}}</code>' пуст. Добавьте первого ученика."""

STUDENTS__ENTER__FULL_NAME = f"""Введите <b>ФИО</b> ученика.
Пример:  <code>Иванов Иван -</code>

/{commands.CANCEL.command} - {commands.CANCEL.description}"""

CREATE_STUDENT__SUCCESS = f"""Аккаунт для ученика готов!

Ключ доступа: <tg-spoiler>{{access_key}}</tg-spoiler>
<code>{{access_link}}</code>

Пригласите пользователя, нажав '<code>Пригласить</code>'."""


STUDENT_INVITE_LETTER = f"""Приглашаю вас пройти курс.
Вы можете пройти его, пройдя по ссылке: {{invite_link}}."""


# MyAccount
ACCOUNT_TYPE__ADMIN = "Администратор"
ACCOUNT_TYPE__EMPLOYEE = "Сотрудник"
ACCOUNT_TYPE__STUDENT = "Ученик"

MY_ACCOUNT__ADMIN = f"""<b>Мой аккаунт</b>  {{item_id}}
Тип аккаунта: <code>{{account_type}}</code>
Фамилия:  <code>{{last_name}}</code>
Имя:  <code>{{first_name}}</code>
Отчество:  <code>{{patronymic}}</code>
Email: {{email}}"""

MY_ACCOUNT__EMPLOYEE = f"""<b>Мой аккаунт</b>  {{item_id}}
Тип аккаунта: <code>{{account_type}}</code>
Фамилия:  <code>{{last_name}}</code>
Имя:  <code>{{first_name}}</code>
Отчество:  <code>{{patronymic}}</code>
Email: {{email}}
—
Роли:  {{roles}}
Курсы:  {{trainings}}"""


GIVE_UP_ACCOUNT_WARNING = f"""⚠️  <b>Внимание</b>: Доступ к аккаунту по вашему текущему ключу доступа <b>будет уже невозможен</b>.

<b>Эта сессия будет завершена</b>, а вам будет выдан пригласительный ключ доступа. Перешлите его новому пользователю.

После того, как новый пользователь перейдет по ключу доступа в этот аккаунт, ему уже будет выдан его новый постоянный ключ доступа.

<b>Таким образом будет произведена полная передача вашего аккаунта другому пользователю!</b>
—
Вы действительно хотите полностью <b>передать свой аккаунт</b> другому пользователю?"""


# TrainingProgress
TRAINING_PROGRESS__BEGIN = f"""Нажмите '<code>{BTN_BEGIN}</code>', чтобы приступить к прохождению курса."""
TRAINING_PROGRESS__COMPLETED = f"""<b>Поздравлем вас!</b> Вы успешно завершили курс  '<code>{{training_name}}</code>'. 
<i>Все результаты сохранены.</i>"""
TRAINING_PROGRESS__TRAINING_IS_STOPPED = f"""Увы, данный курс завершился и больше не доступен для прохождения.
<i>Все результаты сохранены.</i>"""

TRAINING_PROGRESS__NEXT__INFO = f"""<i>Ознакомьтесь с информацией.</i>"""


# Reports
WAIT_OF_REPORT_GENERATING = "🔴  Пожалуйста, подождите. Отчёт уже генерируется..."

REPORT_GENERATING_IS_READY = "✅  Отчёт готов!"

REPORT_TRAINING = f"""Курс:  <code>{{training_name}}</code>  (<code>ID:{{training_id}}</code>)
Дата генерации:  <code>{{date_create}}</code>
Составитель:  <code>{{full_name}}</code>

<i>Отчет сгенерирован автоматически.</i>"""


def field(it: Optional[str]):
    return it if it else EMPTY_FIELD
