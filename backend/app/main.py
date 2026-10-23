import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.api.auth import DB
from app.api.auth import router as auth_router
from app.api.content import router as content_router
from app.api.events import router as events_router
from app.api.generation import router as generation_router
from app.creative.api import router as creative_router
from app.services.content import Problem

app = FastAPI(title="漫剧工作台 阶段 1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(creative_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")


@app.exception_handler(Problem)
async def problem_handler(request: Request, error: Problem) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={"code": error.code, "message": error.message, "details": error.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "INVALID_INPUT", "message": "输入格式不正确，请检查必填字段。", "details": None},
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, error: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"code": "DATA_CONFLICT", "message": "内容已变化或重复，请刷新后重试。", "details": None},
    )


@app.exception_handler(HTTPException)
async def http_handler(request: Request, error: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": "REQUEST_ERROR", "message": "请求无法完成，请检查地址或重新登录。", "details": None},
    )


@app.exception_handler(Exception)
async def unexpected_handler(request: Request, error: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("request_failed", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务暂时无法完成请求，请稍后重试。", "details": None},
    )


@app.get("/healthz")
def health(db: DB) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "phase": "1", "database": "ok"}
