import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE")
INITIAL_GIFT_BYTES = os.getenv("INITIAL_GIFT_BYTES")
INITIAL_GIFT_REQUESTS = os.getenv("INITIAL_GIFT_REQUESTS")

DATABASE = os.getenv("DATABASE")

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

SQLITE_DB_NAME = os.getenv("SQLITE_DB_NAME")
