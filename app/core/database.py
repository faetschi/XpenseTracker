from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine_kwargs = {}
if settings.DB_TYPE == "sqlite":
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# Optimize SQLite for SD card performance
if settings.DB_TYPE == "sqlite":
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(f"PRAGMA temp_store={settings.SQLITE_TEMP_STORE}")
        cursor.execute(f"PRAGMA cache_size=-{settings.SQLITE_CACHE_SIZE_KB}")
        cursor.execute(f"PRAGMA mmap_size={settings.SQLITE_MMAP_SIZE_MB * 1024 * 1024}")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
