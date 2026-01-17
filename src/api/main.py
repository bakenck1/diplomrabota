"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from src.api.routers import auth, voice, admin, comparison
from src.api.schemas import ErrorResponse
from src.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup - create demo user and tables
    from src.models.database import engine, Base
    from src.models.entities import User
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create demo user
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        demo_user_id = "00000000-0000-0000-0000-000000000001"
        query = select(User).where(User.id == demo_user_id)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if not existing:
            from src.api.auth import get_password_hash
            demo_user = User(
                id=demo_user_id,
                name="Demo User",
                email="demo@example.com",
                hashed_password=get_password_hash("demo123"),
                role="senior",
                language="ru",
                stt_provider="openai",
                tts_provider="openai",
            )
            session.add(demo_user)
            await session.commit()
            print("Demo user created")

    yield
    # Shutdown


def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with detailed documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Voice Assistant Pipeline API",
        version="1.0.0",
        description="""
## Voice Assistant Pipeline API

API для голосового ассистента для пожилых пользователей с поддержкой нескольких STT/TTS провайдеров.

### Основные возможности:
- **Голосовой ввод**: Запись и распознавание речи (STT)
- **Нормализация**: Автоматическое исправление ошибок распознавания
- **Генерация ответа**: Синтез речи (TTS)
- **Администрирование**: Управление пользователями, диалогами, словарём
- **Сравнительный анализ**: Тестирование разных алгоритмов STT (OpenAI, Google)

### Аутентификация:
Используется JWT Bearer токен. Получите токен через `/api/auth/login`.

### Провайдеры:
- **OpenAI**: Whisper (STT), TTS API
- **Google**: Cloud Speech-to-Text, Cloud Text-to-Speech

### Ошибки:
| Код | Описание |
|-----|----------|
| E001 | Unauthorized - требуется аутентификация |
| E002 | Forbidden - недостаточно прав |
| E003 | Invalid audio - неверный формат аудио |
| E004 | Provider error - ошибка провайдера |
| E005 | Session not found - сессия не найдена |
| E006 | Rate limited - превышен лимит запросов |
| E999 | Internal error - внутренняя ошибка |
        """,
        routes=app.routes,
        tags=[
            {
                "name": "auth",
                "description": "Аутентификация и авторизация пользователей",
            },
            {
                "name": "voice",
                "description": "Голосовые сессии: запись, распознавание, синтез речи",
            },
            {
                "name": "comparison",
                "description": "Сравнительный анализ алгоритмов распознавания речи",
            },
            {
                "name": "admin",
                "description": "Административные функции: пользователи, диалоги, словарь, аналитика",
            },
        ],
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT токен, полученный через /api/auth/login",
        }
    }

    # Add examples
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Voice Assistant Pipeline API for elderly users",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(voice.router)
    app.include_router(comparison.router)
    app.include_router(admin.router)

    # Custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code="E999",
                message="Internal server error",
                request_id=request_id,
            ).model_dump(),
        )

    # Health check
    @app.get("/health", tags=["system"])
    async def health_check():
        """Проверка работоспособности сервиса."""
        return {"status": "healthy"}

    # Audio file serving endpoint
    @app.get("/api/audio/{path:path}", tags=["system"])
    async def serve_audio(path: str):
        """Serve audio files from local storage."""
        from fastapi.responses import Response
        from src.services.storage import StorageService

        storage = StorageService()
        audio_data = storage.get_local_file(path)

        if audio_data is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Audio file not found"},
            )

        # Determine content type
        content_type = "audio/mpeg" if path.endswith(".mp3") else "audio/wav"

        return Response(
            content=audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={path.split('/')[-1]}",
            },
        )

    return app


app = create_app()
