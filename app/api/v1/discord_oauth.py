"""
Discord OAuth2 Router - Onboarding automático de webhooks por servidor.
"""

from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.discord_webhook_service import get_discord_webhook_service
from config.settings import settings

router = APIRouter()
WEBHOOK_URL_TEMPLATE = 'https://discord.com/api/webhooks/{webhook_id}/{webhook_token}'


def _validate_oauth_settings(require_secret: bool = False) -> None:
    if not settings.discord_oauth_client_id or not settings.discord_oauth_redirect_uri:
        raise HTTPException(
            status_code=500,
            detail=(
                'Discord OAuth2 no está configurado. '
                'Define DISCORD_OAUTH_CLIENT_ID y DISCORD_OAUTH_REDIRECT_URI.'
            ),
        )

    if require_secret and not settings.discord_oauth_client_secret:
        raise HTTPException(
            status_code=500,
            detail='Falta DISCORD_OAUTH_CLIENT_SECRET para completar OAuth2 callback.',
        )


@router.get('/discord/oauth/install-url', summary='Generar URL de autorización OAuth2 de Discord')
async def get_discord_oauth_install_url(
    guild_id: str | None = Query(default=None, description='Guild ID a preseleccionar'),
    state: str | None = Query(default=None, description='Estado opcional para correlación'),
    disable_guild_select: bool = Query(
        default=False,
        description='Si true, bloquea la selección de guild en la pantalla OAuth2',
    ),
):
    """Retorna URL OAuth2 para instalar bot y crear webhook incoming automáticamente."""
    _validate_oauth_settings()

    params = {
        'client_id': settings.discord_oauth_client_id,
        'response_type': 'code',
        'redirect_uri': settings.discord_oauth_redirect_uri,
        'scope': settings.discord_oauth_scopes,
    }

    if settings.discord_oauth_permissions and 'bot' in settings.discord_oauth_scopes:
        params['permissions'] = settings.discord_oauth_permissions
    if guild_id:
        params['guild_id'] = guild_id
    if disable_guild_select:
        params['disable_guild_select'] = 'true'
    if state:
        params['state'] = state

    authorize_url = f'https://discord.com/api/oauth2/authorize?{urlencode(params)}'
    return {
        'success': True,
        'authorize_url': authorize_url,
        'scopes': settings.discord_oauth_scopes,
    }


@router.get('/discord/oauth/callback', summary='Callback OAuth2 para capturar webhook de Discord')
async def discord_oauth_callback(
    code: str = Query(..., description='Authorization code entregado por Discord'),
    state: str | None = Query(default=None, description='Estado devuelto por Discord'),
):
    """
    Intercambia code por token OAuth2 y persiste el webhook incoming por guild_id.
    """
    _validate_oauth_settings(require_secret=True)

    payload = {
        'client_id': settings.discord_oauth_client_id,
        'client_secret': settings.discord_oauth_client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.discord_oauth_redirect_uri,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://discord.com/api/v10/oauth2/token',
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=15.0,
            )
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504, detail='Timeout comunicando con Discord OAuth2.'
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f'Error de red al consumir Discord OAuth2: {type(e).__name__}: {e}',
        ) from e

    if response.status_code >= 400:
        response_detail = response.text[:500] if response.text else 'Sin detalle'
        raise HTTPException(
            status_code=400,
            detail=(
                f'Error de Discord OAuth2 token endpoint: {response.status_code}. '
                f'Detalle: {response_detail}'
            ),
        )

    token_data = response.json()
    webhook = token_data.get('webhook')
    if not webhook or not isinstance(webhook, dict):
        raise HTTPException(
            status_code=400,
            detail=(
                'Discord no retornó webhook en la respuesta OAuth2. '
                'Asegura scope webhook.incoming y autorización sobre un canal.'
            ),
        )

    guild = token_data.get('guild') or {}
    guild_id = webhook.get('guild_id') or guild.get('id')
    if not guild_id:
        raise HTTPException(status_code=400, detail='No se pudo determinar guild_id del webhook.')

    webhook_id = webhook.get('id')
    webhook_token = webhook.get('token')
    webhook_url = webhook.get('url')
    if not webhook_url and webhook_id and webhook_token:
        webhook_url = WEBHOOK_URL_TEMPLATE.format(
            webhook_id=webhook_id,
            webhook_token=webhook_token,
        )

    if not webhook_url:
        raise HTTPException(status_code=400, detail='No se pudo determinar URL del webhook.')

    webhook_service = get_discord_webhook_service()
    stored = await webhook_service.upsert_webhook(
        {
            'server_id': str(guild_id),
            'guild_id': str(guild_id),
            'guild_name': guild.get('name'),
            'channel_id': str(webhook.get('channel_id')) if webhook.get('channel_id') else None,
            'webhook_id': str(webhook_id) if webhook_id else None,
            'webhook_url': webhook_url,
            'webhook_name': webhook.get('name'),
            'webhook_type': webhook.get('type'),
            'application_id': str(webhook.get('application_id'))
            if webhook.get('application_id')
            else None,
            'oauth_scope': token_data.get('scope'),
            'oauth_state': state,
            'last_validated_at': datetime.now(timezone.utc),
            'active': True,
        }
    )

    return {
        'success': True,
        'message': f'Webhook registrado para servidor {stored["server_id"]}',
        'server_id': stored['server_id'],
        'guild_id': stored['guild_id'],
        'channel_id': stored.get('channel_id'),
        'webhook_id': stored.get('webhook_id'),
    }
