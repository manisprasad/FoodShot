from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import config

# Remote databases require SSL, local docker does not
connect_args = {}
db_url = config.DATABASE_URL.lower()
is_local_host = any(
    host in db_url for host in ("localhost", "127.0.0.1", "@db:", "@postgres:")
)
if not is_local_host or any(
    provider in db_url
    for provider in ("neon.tech", "supabase.co", "supabase.com", "supabase.net")
):
    connect_args["ssl"] = True

engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
