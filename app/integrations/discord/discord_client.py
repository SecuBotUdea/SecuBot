# -*- coding: utf-8 -*-
"""
Discord Client - Envia notificaciones a Discord usando Incoming Webhooks
"""

from typing import Any

import httpx

from app.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class DiscordClient:
    """Cliente para enviar mensajes a Discord via Incoming Webhooks"""

    def __init__(self) -> None:
        self.webhook_url = settings.discord_webhook_url
        self.enabled = settings.discord_notifications_enabled

    async def send_message(self, payload: dict[str, Any]) -> bool:
        """
        Envia un payload JSON al webhook de Discord

        Args:
            payload: Diccionario con el payload (debe incluir 'content' o 'embeds')

        Returns:
            bool: True si el mensaje se envio correctamente, False en caso contrario
        """
        if not self.enabled:
            logger.debug('Discord notifications disabled, skipping message send')
            return False

        if not self.webhook_url:
            logger.error('Discord webhook URL not configured')
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )

                # Discord returns 204 No Content on success
                if response.status_code in (200, 204):
                    logger.info('Discord message sent successfully')
                    return True
                else:
                    logger.error(
                        f'Failed to send Discord message: {response.status_code} - {response.text}'
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
