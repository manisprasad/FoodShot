from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_for_icr = State()
    waiting_for_isf = State()
    waiting_for_target_bg = State()
    waiting_for_insulin_type = State()
    waiting_for_daily_report_onboarding = State()
    waiting_for_calorie_target = State()


class FoodAnalysis(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_bg = State()


class Settings(StatesGroup):
    waiting_for_value = State()
    waiting_for_delete_confirm = State()


class HistoryState(StatesGroup):
    waiting_for_delete = State()
