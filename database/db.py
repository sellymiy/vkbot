from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from .models import Base

def make_database(url: str):
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, factory

async def init_db(engine):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def transaction(factory):
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
