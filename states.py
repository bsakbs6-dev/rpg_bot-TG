from aiogram.fsm.state import State, StatesGroup

class CustomCharacterState(StatesGroup):
    waiting_for_name = State()
    waiting_for_prompt = State()
