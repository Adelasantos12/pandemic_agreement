from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .settings import settings

# Railway often provides postgres://; SQLAlchemy async uses postgresql+asyncpg://
db_url = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()
