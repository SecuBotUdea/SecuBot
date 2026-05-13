from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.discord_oauth import discord_oauth_callback, get_discord_oauth_install_url
from app.services.discord_webhook_service import DiscordWebhookService
from config.settings import settings


@pytest.mark.asyncio
async def test_discord_webhook_service_resolves_url_by_guild():
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(
        return_value={
            '_id': 'mongo-id',
            'guild_id': '123456',
            'webhook_url': 'https://discord.com/api/webhooks/123/token',
            'active': True,
        }
    )
    mock_db = MagicMock()
    mock_db.discord_webhooks = mock_collection

    with patch('app.services.discord_webhook_service.get_database', return_value=mock_db):
        service = DiscordWebhookService()
        webhook_url = await service.resolve_webhook_url('123456')

    assert webhook_url == 'https://discord.com/api/webhooks/123/token'


@pytest.mark.asyncio
async def test_install_url_contains_required_oauth_params(monkeypatch):
    monkeypatch.setattr(settings, 'discord_oauth_client_id', 'client-123')
    monkeypatch.setattr(settings, 'discord_oauth_redirect_uri', 'https://secubot.test/callback')
    monkeypatch.setattr(settings, 'discord_oauth_scopes', 'bot webhook.incoming')
    monkeypatch.setattr(settings, 'discord_oauth_permissions', '0')

    result = await get_discord_oauth_install_url(guild_id='777', state='abc')

    assert result['success'] is True
    assert 'client_id=client-123' in result['authorize_url']
    assert 'scope=bot+webhook.incoming' in result['authorize_url']
    assert 'guild_id=777' in result['authorize_url']
    assert 'state=abc' in result['authorize_url']


@pytest.mark.asyncio
async def test_oauth_callback_persists_webhook(monkeypatch):
    monkeypatch.setattr(settings, 'discord_oauth_client_id', 'client-123')
    monkeypatch.setattr(settings, 'discord_oauth_client_secret', 'secret-456')
    monkeypatch.setattr(settings, 'discord_oauth_redirect_uri', 'https://secubot.test/callback')

    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        'scope': 'bot webhook.incoming',
        'guild': {'id': '98765', 'name': 'SecuBot Guild'},
        'webhook': {
            'id': '112233',
            'channel_id': '445566',
            'token': 'webhook-token',
            'name': 'SecuBot Incoming',
        },
    }

    mock_http_client = MagicMock()
    mock_http_client.post = AsyncMock(return_value=token_response)

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    mock_webhook_service = MagicMock()
    mock_webhook_service.upsert_webhook = AsyncMock(
        return_value={
            'guild_id': '98765',
            'channel_id': '445566',
            'webhook_id': '112233',
        }
    )

    with (
        patch('app.api.v1.discord_oauth.httpx.AsyncClient', return_value=mock_async_client),
        patch(
            'app.api.v1.discord_oauth.get_discord_webhook_service',
            return_value=mock_webhook_service,
        ),
    ):
        result = await discord_oauth_callback(code='oauth-code', state='state-1')

    assert result['success'] is True
    assert result['guild_id'] == '98765'
    mock_webhook_service.upsert_webhook.assert_awaited_once()


@pytest.mark.asyncio
async def test_discord_oauth_callback_rejects_missing_webhook(monkeypatch):
    monkeypatch.setattr(settings, 'discord_oauth_client_id', 'client-123')
    monkeypatch.setattr(settings, 'discord_oauth_client_secret', 'secret-456')
    monkeypatch.setattr(settings, 'discord_oauth_redirect_uri', 'https://secubot.test/callback')

    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {'scope': 'bot webhook.incoming'}

    mock_http_client = MagicMock()
    mock_http_client.post = AsyncMock(return_value=token_response)
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch('app.api.v1.discord_oauth.httpx.AsyncClient', return_value=mock_async_client):
        with pytest.raises(HTTPException) as exc_info:
            await discord_oauth_callback(code='oauth-code')

    assert exc_info.value.status_code == 400
