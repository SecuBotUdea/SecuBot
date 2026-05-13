# -*- coding: utf-8 -*-
"""
Discord Client - Envia notificaciones a Discord usando Incoming Webhooks
"""

from typing import Any

import httpx

from app.services.discord_webhook_service import get_discord_webhook_service
from app.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class DiscordClient:
    """Cliente para enviar mensajes a Discord via Incoming Webhooks"""

    def __init__(self) -> None:
        self.enabled = settings.discord_notifications_enabled
        self.default_webhook_url = settings.discord_webhook_url
        self.webhook_service = get_discord_webhook_service()

    async def _resolve_webhook_url(self, guild_id: str | None) -> tuple[str | None, bool]:
        """Resuelve URL de webhook, priorizando guild_id si está disponible."""
        if guild_id:
            try:
                webhook_url = await self.webhook_service.resolve_webhook_url(guild_id)
                if webhook_url:
                    return webhook_url, True
            except Exception as e:
                logger.error(f'Error resolving guild webhook for {guild_id}: {type(e).__name__}: {e}')

        return self.default_webhook_url, False

    async def send_message(self, payload: dict[str, Any], guild_id: str | None = None) -> bool:
        """
        Envia un payload JSON al webhook de Discord

        Args:
            payload: Diccionario con el payload (debe incluir 'content' o 'embeds')
            guild_id: ID del servidor Discord para resolver webhook específico

        Returns:
            bool: True si el mensaje se envio correctamente, False en caso contrario
        """
        if not self.enabled:
            logger.debug('Discord notifications disabled, skipping message send')
            return False

        webhook_url, using_guild_webhook = await self._resolve_webhook_url(guild_id)

        if not webhook_url:
            logger.error('Discord webhook URL not configured')
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0,
                )

                # Discord returns 204 No Content on success
                if response.status_code in (200, 204):
                    logger.info('Discord message sent successfully')
                    return True

                logger.error(
                    f'Failed to send Discord message: {response.status_code} - {response.text}'
                )
                if (
                    using_guild_webhook
                    and guild_id
                    and response.status_code in (401, 403, 404)
                ):
                    await self.webhook_service.deactivate_webhook(
                        guild_id,
                        reason=f'Webhook invalid ({response.status_code})',
                    )
                return False

        except httpx.TimeoutException:
            logger.error('Timeout while sending Discord message')
            return False
        except Exception as e:
            logger.error(f'Error sending Discord message: {type(e).__name__}: {e}')
            return False

    async def send_simple_message(self, text: str) -> bool:
        """
        Envia un mensaje de texto simple a Discord

        Args:
            text: Texto del mensaje

        Returns:
            bool: True si el mensaje se envio correctamente
        """
        payload = {'content': text, 'username': 'SecuBot'}
        return await self.send_message(payload)


# Singleton instance
discord_client = DiscordClient()
