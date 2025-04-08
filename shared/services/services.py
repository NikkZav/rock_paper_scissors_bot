import random
from src.repositories.db import online_users


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


def get_random_online_user(except_user_id: int) -> int:
    users = {**online_users.users}
    users.pop(except_user_id, None)
    if not len(users):
        raise IndexError
    opponent_id = random.choice(list(users.keys()))
    return opponent_id
