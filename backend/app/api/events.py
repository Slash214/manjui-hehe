import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.auth import DB, CurrentUser
from app.models import GenerationTask, Project
from app.repos import SessionLocal
from app.services.content import ContentService, dump

router = APIRouter()


@router.get("/projects/{id}/events")
def events(id: str, request: Request, db: DB, user: CurrentUser) -> StreamingResponse:
    ContentService(db, user.id).get(Project, id)
    owner_id = user.id
    db.commit()  # Release the request transaction before entering a long-lived stream.

    async def stream():
        seen: dict[str, str] = {}
        yield "event: connected\ndata: {}\n\n"
        while not await request.is_disconnected():
            with SessionLocal() as session:
                project = session.get(Project, id)
                if project is None or project.owner_id != owner_id or project.deleted_at:
                    return
                tasks = session.scalars(select(GenerationTask).where(GenerationTask.project_id == id).order_by(GenerationTask.updated_at.desc()).limit(200))
                for task in tasks:
                    value = json.dumps(dump(task), ensure_ascii=False)
                    if seen.get(task.id) != value:
                        seen[task.id] = value
                        yield f"id: {task.id}:{task.updated_at.isoformat()}\nevent: task.updated\ndata: {value}\n\n"
            yield ": heartbeat\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
