from collections.abc import Generator

from sqlmodel import Session, create_engine

from core.config import app_settings

engine = create_engine(app_settings.DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.

    :return: Database session
    :rtype: Generator[Session, None, None]
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()
