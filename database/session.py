from database.utils import getDatabaseUrl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.models import Base

# Create Async Engine
engine = create_async_engine(getDatabaseUrl(), echo=False)

# Create a session factory
asyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db():
    """Creates the tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
