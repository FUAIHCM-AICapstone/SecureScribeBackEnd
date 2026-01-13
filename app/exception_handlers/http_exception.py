from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas.common import ApiResponse

# ============================================================================
# Custom Exception inheriting from HTTPException
# ============================================================================


class AppException(HTTPException):
    """
    Custom exception class that inherits from FastAPI's HTTPException.
    Supports status_code, message, error_code, and data in the response.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        self.message = message
        self.data = data
        detail = {
            "message": message,
            "data": data,
        }
        super().__init__(status_code=status_code, detail=detail, headers=headers)


# ============================================================================
# Exception Handlers
# ============================================================================


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and exc.detail == "Not authenticated":
        return JSONResponse(status_code=401, content=ApiResponse(message="You are not logged in or your session has expired. Please log in again.", success=False, data=None).model_dump())

    if exc.status_code == 403 and exc.detail == "Not authenticated":
        return JSONResponse(status_code=401, content=ApiResponse(message="You are not logged in or your session has expired. Please log in again.", success=False, data=None).model_dump())

    # Extract error code, message, and data from AppException
    error_code = None
    message = exc.detail
    data = None

    if isinstance(exc, AppException):
        message = exc.message
        data = exc.data
    elif isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        data = exc.detail.get("data")

    return JSONResponse(status_code=exc.status_code, content=ApiResponse(message=message, success=False, data=data).model_dump())


async def custom_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content=ApiResponse(message=str(exc), success=False, data=None).model_dump())
