from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Content, Row

engine = create_engine(settings.database_url, pool_pre_ping=True)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_fk(connection: Any, _: Any) -> None:
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def database() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def rows(db: Session, model: type[Row], **where: Any) -> list[Any]:
    query = select(model).filter_by(**where)
    if issubclass(model, Content):
        query = query.where(model.deleted_at.is_(None))
    order = getattr(model, "order_no", getattr(model, "version_no", model.created_at))
    return list(db.scalars(query.order_by(order, model.id)))
