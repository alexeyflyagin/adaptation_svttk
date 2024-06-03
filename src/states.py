from aiogram.fsm.state import StatesGroup, State


class MainStates(StatesGroup):
    ADMIN = State()
    EMPLOYEE = State()
    STUDENT = State()


class CreateRoleStates(StatesGroup):
    NAME = State()
