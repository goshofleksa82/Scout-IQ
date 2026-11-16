"""Stable JSON errors without leaking SQL, parameters, or account secrets."""
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


async def database_failure(request, exc):
    logger.error("Unhandled database operation failed")
    return JSONResponse(status_code=500, content={"detail": "Database service unavailable"})


def install_error_handlers(app):
    from app.api.auth import safe_validation_error
    app.add_exception_handler(RequestValidationError, safe_validation_error)
    app.add_exception_handler(SQLAlchemyError, database_failure)
