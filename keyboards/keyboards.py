from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from lexicon.lexicon_ru import LEXICON

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------

# Создаем кнопки с ответами согласия и отказа
button_yes = KeyboardButton(text=LEXICON['yes_button'])
button_no = KeyboardButton(text=LEXICON['no_button'])

# Инициализируем билдер для клавиатуры с кнопками "Давай" и "Не хочу!"
yes_no_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=2
yes_no_kb_builder.row(button_yes, button_no, width=2)

# Создаем клавиатуру с кнопками "Давай!" и "Не хочу!"
yes_no_kb: ReplyKeyboardMarkup = yes_no_kb_builder.as_markup(
    one_time_keyboard=True,
    resize_keyboard=True
)

# # ------- Создаем игровую клавиатуру без использования билдера -------

# # Создаем кнопки игровой клавиатуры
# button_1 = KeyboardButton(text=LEXICON['rock'])
# button_2 = KeyboardButton(text=LEXICON['scissors'])
# button_3 = KeyboardButton(text=LEXICON['paper'])

# # Создаем игровую клавиатуру с кнопками "Камень 🗿",
# # "Ножницы ✂" и "Бумага 📜" как список списков
# game_kb = ReplyKeyboardMarkup(
#     keyboard=[[button_1],
#               [button_2],
#               [button_3]],
#     resize_keyboard=True
# )


# Функция для формирования инлайн-клавиатуры на лету
def create_inline_kb(*args: str,
                     width: int | None = 3,
                     **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=LEXICON[button] if button in LEXICON else button,
                callback_data=button))
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=button))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()
