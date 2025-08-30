from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db import get_db

app = FastAPI(title="SecureScribeBE")


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Welcome to SecureScribeBE API"}


@app.get("/health")
def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint that tests database connection
    """
    try:
        # Test database connection with a simple query
        db.execute(text("SELECT 1"))
        db.commit()

        return {
            "status": "healthy",
            "database": "connected",
            "server": settings.POSTGRES_SERVER,
            "database_name": settings.POSTGRES_DB,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "server": settings.POSTGRES_SERVER,
                "database_name": settings.POSTGRES_DB,
            },
        )
