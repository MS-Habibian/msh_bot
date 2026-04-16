# run_once.py
from utils.tg_client import tg_app

with tg_app:
    print("Successfully logged in!")
