"""
SecuBot - FastAPI Application
Sistema de orquestacion DevSecOps con gamificacion verificada
"""
# Force reload

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import alerts, discord_oauth, gamification, notifications, remediations, users
from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo
from app.tasks.scheduler import get_scheduler
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: startup and shutdown"""
    # Startup
    await connect_to_mongo()
    await create_indexes()

    scheduler = get_scheduler()
    scheduler.start()

    # Start Discord bot as a background task (only if token is configured)
    discord_task = None
    if settings.discord_bot_token:
        from app.integrations.discord.discord_bot import start_bot

        discord_task = asyncio.create_task(start_bot())

    yield

    # Shutdown
    if discord_task is not None:
        from app.integrations.discord.discord_bot import stop_bot

        await stop_bot()
        discord_task.cancel()
        try:
            await discord_task
        except asyncio.CancelledError:
            pass

    scheduler.shutdown(wait=False)
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description='Sistema de gamificacion verificada para DevSecOps',
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# Health check endpoint
@app.get('/health', tags=['Health'])
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            'status': 'healthy',
            'app': settings.app_name,
            'version': settings.app_version,
            'discord_enabled': settings.discord_notifications_enabled,
        }
    )


# Include routers
app.include_router(notifications.router, prefix='/api/v1', tags=['Notifications'])
app.include_router(discord_oauth.router, prefix='/api/v1', tags=['Discord OAuth'])
app.include_router(alerts.router, prefix='/api/v1/alerts', tags=['Alerts'])
app.include_router(users.router, prefix='/api/v1/users', tags=['Users'])
app.include_router(remediations.router, prefix='/api/v1/remediations', tags=['Remediations'])
app.include_router(gamification.router, prefix='/api/v1/gamification', tags=['Gamification'])


# Root endpoint
@app.get('/', tags=['Root'])
async def root():
    return {'message': 'Welcome to SecuBot'}
