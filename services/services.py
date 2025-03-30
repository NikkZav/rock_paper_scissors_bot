import random

from lexicon.lexicon_ru import LEXICON_MOVES


# Функция, возвращающая случайный выбор бота в игре
def get_bot_choice() -> str:
    return random.choice(["rock", "paper", "scissors"])


# Функция, определяющая победителя
def get_winner(user_choice: str, bot_choice: str) -> str:
    rules = {"rock": "scissors",
             "scissors": "paper",
             "paper": "rock"}
    print(f"user_choice = {user_choice}")
    print(f"bot_choice = {bot_choice}")
    if user_choice == bot_choice:
        return "nobody_won"
    elif rules[user_choice] == bot_choice:
        return "user_won"
    return "bot_won"
