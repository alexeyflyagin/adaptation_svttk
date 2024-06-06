from aiogram.fsm.state import StatesGroup, State


class MainStates(StatesGroup):
    ADMIN = State()
    EMPLOYEE = State()
    STUDENT = State()


class EmployeeCreateStates(StatesGroup):
    FULL_NAME = State()


class EmployeeEditEmailStates(StatesGroup):
    EditEmail = State()


class RoleCreateStates(StatesGroup):
    NAME = State()


class RoleRenameStates(StatesGroup):
    RENAME = State()
