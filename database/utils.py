from config import (
    DATABASE,
    SQLITE_DB_NAME,
    POSTGRES_DB,
    POSTGRES_PASSWORD,
    POSTGRES_USER,
    POSTGRES_HOST,
    POSTGRES_PORT
)


def getDatabaseUrl():
    if DATABASE == "postgres":
        return f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    else:
        return f"sqlite+aiosqlite:///{SQLITE_DB_NAME}"
