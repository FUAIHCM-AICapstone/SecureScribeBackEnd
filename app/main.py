from typing import Any, Dict

from fastapi import Depends, FastAPI, FileResponse, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import api_router
from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.db import get_db
from app.events.listeners.notification_listener import NotificationListener
from app.events.listeners.websocket_listener import WebSocketListener
from app.services.event_manager import EventManager
from app.utils.throttling import ThrottlingMiddleware


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
        {"url": "http://localhost:8081/be", "description": "Development server"},
        {"url": "https://securescribe.wc504.io.vn/be", "description": "Production server"},
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
    root_path="/be",
    # Custom operation ID generation for better client code
    generate_unique_id_function=custom_generate_unique_id,
)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""

    # Initialize database and create tables if needed
    from app.db import init_database

    init_database()

    EventManager.register(NotificationListener())
    EventManager.register(WebSocketListener())

    # Start WebSocket manager Redis listener
    from app.services.websocket_manager import websocket_manager

    await websocket_manager.start_redis_listener()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    # Stop WebSocket manager Redis listener
    from app.services.websocket_manager import websocket_manager

    await websocket_manager.stop_redis_listener()


# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[REQUEST] {request.method} {request.url}")
    response = await call_next(request)
    print(f"\033[92m[RESPONSE]\033[0m {response.__class__.__name__}({response.status_code if hasattr(response, 'status_code') else 'streaming'}, {getattr(response, 'media_type', 'unknown')})")

    try:
        if hasattr(response, "body"):
            body_content = response.body.decode("utf-8", errors="ignore")
            # Limit body size to avoid flooding logs
            if len(body_content) > 500:
                body_content = body_content[:500] + "..."
            print(f"\033[93m[RESPONSE BODY]\033[0m {body_content}")
        elif hasattr(response, "content") and response.content:
            body_content = response.content.decode("utf-8", errors="ignore")
            if len(body_content) > 500:
                body_content = body_content[:500] + "..."
            print(f"\033[93m[RESPONSE BODY]\033[0m {body_content}")
    except Exception as e:
        print(f"\033[91m[BODY LOG ERROR]\033[0m Could not read response body: {e}")

    return response


app.openapi = custom_openapi


app.add_middleware(
    CORSMiddleware,
    allow_origins=(["*"]),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add throttling middleware for rate limiting
app.add_middleware(ThrottlingMiddleware)

app.include_router(api_router)

initialize_firebase()


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
                "vectors_count": collection_info.get("points_count", 0) if collection_info else 0,
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
            "vectors_count": collection_info.get("points_count", 0) if collection_info else 0,
            "collection_status": collection_info.get("status", "unknown") if collection_info else "not_found",
            "collection_size": collection_info.get("disk_size", 0) if collection_info else 0,
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
        "overall_status": "healthy" if all("✅" in status for status in services_status.values()) else "degraded",
    }


@app.get("/download")
def download_file(object_name: str):
    from app.utils.minio import download_file_from_minio
    
    file_bytes = download_file_from_minio(settings.MINIO_BUCKET_NAME, object_name)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        iter([file_bytes]),
        media_type="application/octet-stream",
        filename=object_name.split("/")[-1]
    )
