"""
SecuBot - FastAPI Application (Minimal Version for Slack Integration Testing)
Sistema de orquestacion DevSecOps con gamificacion verificada
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import notifications
from config.settings import settings

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description='Sistema de gamificacion verificada para DevSecOps',
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


# Root endpoint
@app.get('/', tags=['Root'])
async def root():
    """Root endpoint with API information"""
    return {
        'message': f'Welcome to {settings.app_name}',
        'version': settings.app_version,
        'docs': '/docs',
        'health': '/health',
        'features': {
            'slack_integration': settings.slack_notifications_enabled,
        },
    }
