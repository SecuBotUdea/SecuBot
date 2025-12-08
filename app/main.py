"""
SecuBot - FastAPI Application
Sistema de orquestacion DevSecOps con gamificacion verificada
"""
# Force reload

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1 import alerts, notifications, remediations, users
from app.database.connection import close_db_connection, init_db_connection
from app.database.indexes import create_indexes
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: startup and shutdown"""
    # Startup
    await init_db_connection()
    await create_indexes()
    yield
    # Shutdown
    await close_db_connection()

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
            'slack_enabled': settings.slack_notifications_enabled,
        }
    )


# Include routers
app.include_router(notifications.router, prefix='/api/v1', tags=['Notifications'])
app.include_router(alerts.router, prefix='/api/v1/alerts', tags=['Alerts'])
app.include_router(users.router, prefix='/api/v1/users', tags=['Users'])
app.include_router(remediations.router, prefix='/api/v1/remediations', tags=['Remediations'])


# Root endpoint
@app.get('/', tags=['Root'])
async def root():
    return {"message": "Welcome to SecuBot"}
