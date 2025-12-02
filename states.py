from aiogram.fsm.state import State, StatesGroup

class Onboarding(StatesGroup):
    name = State()
    phone = State()
    balance = State()
