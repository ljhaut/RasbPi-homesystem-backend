from sqlmodel import Session, SQLModel, create_engine

from core.config import app_settings

engine = create_engine(app_settings.DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session():
    with Session(engine) as session:
        yield session
