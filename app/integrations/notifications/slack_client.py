# -*- coding: utf-8 -*-
"""
Slack Client - Envia notificaciones a Slack usando Incoming Webhooks
"""

import httpx
from typing import Any

from config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SlackClient:
    """Cliente para enviar mensajes a Slack via Incoming Webhooks"""

    def __init__(self):
        self.webhook_url = settings.slack_webhook_url
        self.enabled = settings.slack_notifications_enabled

    async def send_message(self, message: dict[str, Any]) -> bool:
        """
        Envia un mensaje a Slack

        Args:
            message: Diccionario con el payload del mensaje (debe incluir 'text' o 'blocks')

        Returns:
            bool: True si el mensaje se envio correctamente, False en caso contrario

        Example:
            message = {
                "text": "Alerta nueva detectada",
                "blocks": [...]
            }
        """
        if not self.enabled:
            logger.debug('Slack notifications disabled, skipping message send')
            return False

        if not self.webhook_url:
            logger.error('Slack webhook URL not configured')
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url, json=message, timeout=10.0
                )

                if response.status_code == 200:
                    logger.info('Slack message sent successfully')
                    return True
                else:
                    logger.error(
                        f'Failed to send Slack message: {response.status_code} - {response.text}'
                    )
                    return False

        except httpx.TimeoutException:
            logger.error('Timeout while sending Slack message')
            return False
        except Exception as e:
            logger.error(f'Error sending Slack message: {type(e).__name__}: {e}')
            return False

    async def send_simple_message(self, text: str) -> bool:
        """
        Envia un mensaje de texto simple a Slack

        Args:
            text: Texto del mensaje

        Returns:
            bool: True si el mensaje se envio correctamente
        """
        message = {'text': text}
        return await self.send_message(message)

    async def send_formatted_message(
        self, text: str, blocks: list[dict[str, Any]], attachments: list[dict[str, Any]] | None = None
    ) -> bool:
        """
        Envia un mensaje formateado con blocks de Slack

        Args:
            text: Texto fallback (para notificaciones)
            blocks: Lista de bloques de Slack Block Kit
            attachments: Lista de attachments (opcional, legacy)

        Returns:
            bool: True si el mensaje se envio correctamente
        """
        message = {'text': text, 'blocks': blocks}

        if attachments:
            message['attachments'] = attachments

        return await self.send_message(message)


# Singleton instance
slack_client = SlackClient()
