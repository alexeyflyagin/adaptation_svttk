from aiogram.fsm.state import StatesGroup, State


class MainStates(StatesGroup):
    WAIT = State()
    CLEAR_PREVIOUS_SESSION = State()
    ADMIN = State()
    EMPLOYEE = State()
    STUDENT = State()


class EmployeeCreateStates(StatesGroup):
    FULL_NAME = State()


class EmployeeEditEmailStates(StatesGroup):
    EDIT_EMAIL = State()


class LevelCreateStates(StatesGroup):
    TITLE = State()
    CONTENT = State()


class StudentCreateState(StatesGroup):
    FULL_NAME = State()


class TrainingStartEditStates(StatesGroup):
    CONTENT = State()


class LevelEditStates(StatesGroup):
    TITLE = State()
    CONTENT = State()


class EmployeeEditFullNameStates(StatesGroup):
    EDIT_FULL_NAME = State()


class RoleCreateStates(StatesGroup):
    NAME = State()


class RoleRenameStates(StatesGroup):
    RENAME = State()


class TrainingCreateStates(StatesGroup):
    NAME = State()
    ROLE = State()


class TrainingEditNameStates(StatesGroup):
    NAME = State()


class MyAccountEditStates(StatesGroup):
    EMAIL = State()
    FULL_NAME = State()
