import os
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import api_router
from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.db import get_db
from app.utils.auth import get_current_user_from_token


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    Custom function to generate unique operation IDs for OpenAPI schema.
    This creates cleaner method names for generated client code.
    """
    if route.tags:
        # Use first tag + operation name for better organization
        return f"{route.tags[0]}_{route.name}"
    return route.name


def custom_openapi():
    """
    Custom OpenAPI schema generator with additional metadata and extensions.
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
        "altText": "SecureScribe API Logo",
    }

    # Add custom servers for different environments
    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.securescribe.com", "description": "Production server"},
    ]

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authorization header using the Bearer scheme.",
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Cache the schema
    app.openapi_schema = openapi_schema
    return openapi_schema


app = FastAPI(
    title="SecureScribeBE",
    version="1.0.0",
    contact={
        "name": "SecureScribe Team",
        "email": "support@securescribe.com",
    },
    license_info={
        "name": "MIT",
    },
    # Custom operation ID generation for better client code
    generate_unique_id_function=custom_generate_unique_id,
)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🚀 Application started successfully")

    # Start WebSocket manager Redis listener
    from app.services.websocket_manager import websocket_manager

    await websocket_manager.start_redis_listener()
    print("🔌 WebSocket Redis listener started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    # Stop WebSocket manager Redis listener
    from app.services.websocket_manager import websocket_manager

    await websocket_manager.stop_redis_listener()
    print("🔌 WebSocket Redis listener stopped")

    print("🛑 Application shutdown")


# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[REQUEST] {request.method} {request.url}")
    print(f"[HEADERS] {dict(request.headers)}")
    response = await call_next(request)
    print(f"[RESPONSE] {response.status_code}")
    return response


# Override the default OpenAPI schema generator
app.openapi = custom_openapi

# Configure CORS for cross-origin requests with Authorization headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
        if settings.BACKEND_CORS_ORIGINS
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],  # Explicitly allow methods
    allow_headers=["*"],  # Allow all headers including Authorization
    expose_headers=["*"],  # Expose all headers for EventSource
)

# Mount API router FIRST (important for routing precedence)
app.include_router(api_router)

# Mount static files AFTER API router to avoid conflicts
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/firebase-messaging-sw.js")
def get_firebase_service_worker():
    """Serve Firebase service worker file"""
    file_path = "firebase-messaging-sw.js"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="Service worker not found")


# Mount service worker at root for Firebase
app.mount(
    "/firebase-messaging-sw.js", StaticFiles(directory="app/static"), name="firebase-sw"
)

# Initialize Firebase SDK
initialize_firebase()


@app.get("/test-auth")
def test_auth_endpoint(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("authorization", "")

    if not auth_header:
        return {
            "message": "No Authorization header found",
            "usage": "Add 'Authorization: Bearer <token>' to your request headers",
            "example": "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        }

    if not auth_header.lower().startswith("bearer "):
        return {
            "message": "Invalid Authorization header format",
            "usage": "Header must start with 'Bearer '",
            "example": "Authorization: Bearer <your_jwt_token>",
        }

    token = (
        auth_header[len("bearer ") :]
        if auth_header.lower().startswith("bearer ")
        else auth_header[len("Bearer ") :]
    )
    user_id = get_current_user_from_token(token)

    if not user_id:
        return {
            "message": "Invalid or expired token",
            "token_valid": False,
            "user_id": None,
        }

    return {
        "message": "Token validated successfully",
        "token_valid": True,
        "user_id": user_id,
        "token_preview": token[:20] + "..." if len(token) > 20 else token,
    }


@app.get("/celery-test")
def get_celery_test_page():
    """Serve the Celery task test page"""
    return FileResponse("app/static/celery-test.html", media_type="text/html")


@app.get("/search-test")
def get_search_test_page():
    """Serve the Search service test page"""
    return FileResponse("app/static/search-test.html", media_type="text/html")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint that tests all services
    """
    health_data = {
        "timestamp": "2025-09-10T12:00:00Z",
        "status": "healthy",
        "services": {},
    }

    # Test database connection
    try:
        db.query(text("SELECT 1"))
        db.commit()
        health_data["services"]["database"] = {
            "status": "connected",
            "server": settings.POSTGRES_SERVER,
            "database": settings.POSTGRES_DB,
        }
    except Exception as e:
        health_data["services"]["database"] = {
            "status": "disconnected",
            "error": str(e),
        }
        health_data["status"] = "degraded"

    # Test Redis connection
    try:
        from app.utils.redis import get_redis_client

        redis_client = get_redis_client()
        redis_client.ping()
        redis_info = redis_client.info()
        health_data["services"]["redis"] = {
            "status": "connected",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "version": redis_info.get("redis_version", "unknown"),
        }
    except Exception as e:
        health_data["services"]["redis"] = {"status": "disconnected", "error": str(e)}
        health_data["status"] = "degraded"

    # Test Qdrant connection
    try:
        from app.utils.qdrant import get_collection_info, health_check

        qdrant_healthy = health_check()
        if qdrant_healthy:
            collection_info = get_collection_info()
            health_data["services"]["qdrant"] = {
                "status": "connected",
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
                "collection": settings.QDRANT_COLLECTION_NAME,
                "vectors_count": collection_info.get("points_count", 0)
                if collection_info
                else 0,
            }
        else:
            health_data["services"]["qdrant"] = {"status": "disconnected"}
            health_data["status"] = "degraded"
    except Exception as e:
        health_data["services"]["qdrant"] = {"status": "error", "error": str(e)}
        health_data["status"] = "degraded"

    # Test MinIO connection
    try:
        from app.utils.minio import health_check as minio_health_check

        minio_healthy = minio_health_check()
        if minio_healthy:
            health_data["services"]["minio"] = {
                "status": "connected",
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET_NAME,
                "public_bucket": settings.MINIO_PUBLIC_BUCKET_NAME,
                "secure": settings.MINIO_SECURE,
            }
        else:
            health_data["services"]["minio"] = {"status": "disconnected"}
            health_data["status"] = "degraded"
    except Exception as e:
        health_data["services"]["minio"] = {"status": "error", "error": str(e)}
        health_data["status"] = "degraded"

    # Raise error if any critical service is down
    critical_services = ["database", "redis"]
    for service in critical_services:
        if health_data["services"].get(service, {}).get("status") != "connected":
            raise HTTPException(status_code=503, detail=health_data)

    return health_data


@app.get("/health/database")
def health_database(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Database health check endpoint
    """
    try:
        # Test database connection with a simple query
        db.query(text("SELECT 1"))
        db.commit()

        # Get database info
        result = db.execute(text("SELECT version(), current_database(), current_user"))
        version, database, user = result.fetchone()

        return {
            "status": "connected",
            "database": database,
            "user": user,
            "version": version,
            "server": settings.POSTGRES_SERVER,
            "port": settings.POSTGRES_PORT,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "disconnected",
                "error": str(e),
                "database": settings.POSTGRES_DB,
                "server": settings.POSTGRES_SERVER,
            },
        )


@app.get("/health/redis")
def health_redis() -> Dict[str, Any]:
    """
    Redis health check endpoint
    """
    try:
        from app.utils.redis import get_redis_client

        redis_client = get_redis_client()

        # Test connection
        redis_client.ping()

        # Get Redis info
        info = redis_client.info()
        memory_info = redis_client.info("memory")

        return {
            "status": "connected",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "connected_clients": info.get("connected_clients", 0),
            "memory_used": memory_info.get("used_memory_human", "unknown"),
            "memory_peak": memory_info.get("used_memory_peak_human", "unknown"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "disconnected",
                "error": str(e),
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
            },
        )


@app.get("/health/qdrant")
def health_qdrant() -> Dict[str, Any]:
    """
    Qdrant health check endpoint
    """
    try:
        from app.utils.qdrant import get_collection_info, health_check

        # Test connection
        qdrant_healthy = health_check()
        if not qdrant_healthy:
            raise Exception("Qdrant health check failed")

        # Get collection info
        collection_info = get_collection_info()

        return {
            "status": "connected",
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
            "collection": settings.QDRANT_COLLECTION_NAME,
            "vectors_count": collection_info.get("points_count", 0)
            if collection_info
            else 0,
            "collection_status": collection_info.get("status", "unknown")
            if collection_info
            else "not_found",
            "collection_size": collection_info.get("disk_size", 0)
            if collection_info
            else 0,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "disconnected",
                "error": str(e),
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
                "collection": settings.QDRANT_COLLECTION_NAME,
            },
        )


@app.get("/health/minio")
def health_minio() -> Dict[str, Any]:
    """
    MinIO health check endpoint
    """
    try:
        from app.utils.minio import get_minio_client

        # Test connection by listing buckets
        minio_client = get_minio_client()
        try:
            buckets = minio_client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]

            # Check if our buckets exist
            main_bucket_exists = settings.MINIO_BUCKET_NAME in bucket_names
            public_bucket_exists = settings.MINIO_PUBLIC_BUCKET_NAME in bucket_names

            return {
                "status": "connected",
                "endpoint": settings.MINIO_ENDPOINT,
                "secure": settings.MINIO_SECURE,
                "main_bucket": {
                    "name": settings.MINIO_BUCKET_NAME,
                    "exists": main_bucket_exists,
                },
                "public_bucket": {
                    "name": settings.MINIO_PUBLIC_BUCKET_NAME,
                    "exists": public_bucket_exists,
                },
                "total_buckets": len(bucket_names),
                "bucket_names": bucket_names[:10],  # Limit to first 10 for brevity
            }
        except Exception as bucket_error:
            return {
                "status": "connected",
                "endpoint": settings.MINIO_ENDPOINT,
                "secure": settings.MINIO_SECURE,
                "bucket_check_error": str(bucket_error),
            }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "disconnected",
                "error": str(e),
                "endpoint": settings.MINIO_ENDPOINT,
                "secure": settings.MINIO_SECURE,
            },
        )


@app.get("/health/services")
def health_services(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Quick overview of all services status
    """
    services_status = {}

    # Database
    try:
        db.query(text("SELECT 1"))
        services_status["database"] = "✅ connected"
    except Exception:
        services_status["database"] = "❌ disconnected"

    # Redis
    try:
        from app.utils.redis import get_redis_client

        get_redis_client().ping()
        services_status["redis"] = "✅ connected"
    except Exception:
        services_status["redis"] = "❌ disconnected"

    # Qdrant
    try:
        from app.utils.qdrant import health_check

        if health_check():
            services_status["qdrant"] = "✅ connected"
        else:
            services_status["qdrant"] = "❌ disconnected"
    except Exception:
        services_status["qdrant"] = "❌ error"

    # MinIO
    try:
        from app.utils.minio import get_minio_client

        client = get_minio_client()
        client.list_buckets()  # thử kết nối
        services_status["minio"] = "✅ connected"
    except Exception as e:
        services_status["minio"] = f"❌ disconnected ({e})"

    return {
        "timestamp": "2025-09-10T12:00:00Z",
        "services": services_status,
        "overall_status": "healthy"
        if all("✅" in status for status in services_status.values())
        else "degraded",
    }
