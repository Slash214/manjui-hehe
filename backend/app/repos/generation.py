from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.task_state import ACTIVE
from app.models import GenerationTask, User


def lock_owner(db: Session, user_id: str) -> None:
    db.scalar(select(User).where(User.id == user_id).with_for_update())


def active_count(db: Session, user_id: str, shot_id: str | None = None) -> int:
    query = select(func.count()).select_from(GenerationTask).where(
        GenerationTask.owner_id == user_id, GenerationTask.status.in_(ACTIVE))
    if shot_id:
        query = query.where(GenerationTask.shot_id == shot_id)
    return int(db.scalar(query) or 0)
