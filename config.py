import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
INITIAL_GIFT_BYTES = int(os.getenv("INITIAL_GIFT_BYTES"))
INITIAL_GIFT_REQUESTS = int(os.getenv("INITIAL_GIFT_REQUESTS"))

DATABASE = os.getenv("DATABASE")

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

SQLITE_DB_NAME = os.getenv("SQLITE_DB_NAME")

HOURS_TO_KEEP_FILES = int(os.getenv("HOURS_TO_KEEP_FILES"))
SPLIT_CHUNK_SIZE = int(os.getenv("SPLIT_CHUNK_SIZE"))
