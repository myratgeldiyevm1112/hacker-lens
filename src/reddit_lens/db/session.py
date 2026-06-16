from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from reddit_lens.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields a database session and guarantees it is
    closed after use, even if an exception occurs mid-request.
    """
    async with async_session_factory() as session:
        yield session