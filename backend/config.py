import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

os.makedirs(INSTANCE_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(
    INSTANCE_DIR,
    "players.db"
)

DATABASE_URL = "sqlite:///" + DATABASE_PATH

VALID_BETS = [10, 50, 100, 500]

STARTING_COINS = 1100

DAILY_BONUS = 100