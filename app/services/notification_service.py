"""
Notification Service - Orquesta el envio de notificaciones a Discord
"""

from app.integrations.discord.discord_client import discord_client
from app.integrations.discord.message_builder import discord_message_builder
from app.models.alert import Alert
from app.models.remediation import Remediation
from app.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class NotificationService:
    """Servicio para enviar notificaciones de eventos del sistema via Discord"""

    def __init__(self):
        self.discord = discord_client
        self.builder = discord_message_builder
        self.bot_username = settings.app_name

    def _extract_guild_id(self, *objects: dict | None) -> str | None:
        """
        Extrae guild_id desde múltiples objetos de contexto.

        Revisa en orden:
        1) Campos directos: discord_guild_id / guild_id
        2) Campos en metadata: metadata.discord_guild_id / metadata.guild_id
        3) Campos en normalized_payload: normalized_payload.discord_guild_id / normalized_payload.guild_id

        Retorna el primer valor encontrado o None si no existe.
        """
        for obj in objects:
            if not obj:
                continue

            direct = obj.get('discord_guild_id') or obj.get('guild_id')
            if direct:
                return str(direct)

            metadata = obj.get('metadata')
            if isinstance(metadata, dict):
                metadata_guild = metadata.get('discord_guild_id') or metadata.get('guild_id')
                if metadata_guild:
                    return str(metadata_guild)

            normalized_payload = obj.get('normalized_payload')
            if isinstance(normalized_payload, dict):
                payload_guild = normalized_payload.get(
                    'discord_guild_id'
                ) or normalized_payload.get('guild_id')
                if payload_guild:
                    return str(payload_guild)

        return None

    async def notify_new_alert(self, alert: Alert, guild_id: str | None = None) -> bool:
        """
        Notifica sobre una nueva alerta de seguridad detectada

        Args:
            alert: Objeto Alert con los datos de la alerta

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            alert_data = alert.model_dump()
            effective_guild_id = guild_id or self._extract_guild_id(alert_data)
            success = await self.discord.send_message(
                self.builder.build_alert_embed(alert),
                guild_id=effective_guild_id,
            )

            if success:
                logger.info(f'Notification sent for new alert: {alert.alert_id}')
            else:
                logger.warning(f'Failed to send notification for alert: {alert.alert_id}')

            return success

        except Exception as e:
            logger.error(f'Error notifying new alert {alert.alert_id}: {type(e).__name__}: {e}')
            return False

    async def notify_remediation_verified(
        self,
        alert: Alert,
        remediation: Remediation,
        points_earned: int,
        guild_id: str | None = None,
    ) -> bool:
        """
        Notifica que una remediacion fue verificada exitosamente

        Args:
            alert: Alerta que fue remediada
            remediation: Objeto Remediation
            points_earned: Puntos ganados por la remediacion

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            alert_data = alert.model_dump()
            remediation_data = remediation.model_dump()
            effective_guild_id = guild_id or self._extract_guild_id(alert_data, remediation_data)
            success = await self.discord.send_message(
                self.builder.build_remediation_verified_embed(alert, remediation, points_earned),
                guild_id=effective_guild_id,
            )

            if success:
                logger.info(
                    f'Notification sent for verified remediation: {remediation.id} (+{points_earned} points)'
                )
            else:
                logger.warning(f'Failed to send notification for remediation: {remediation.id}')

            return success

        except Exception as e:
            logger.error(
                f'Error notifying remediation verification {remediation.id}: {type(e).__name__}: {e}'
            )
            return False

    async def notify_remediation_failed(
        self,
        alert: Alert,
        remediation: Remediation,
        penalty_points: int,
        guild_id: str | None = None,
    ) -> bool:
        """
        Notifica que un rescan detecto que la vulnerabilidad persiste

        Args:
            alert: Alerta que supuestamente fue remediada
            remediation: Objeto Remediation
            penalty_points: Puntos de penalizacion

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            alert_data = alert.model_dump()
            remediation_data = remediation.model_dump()
            effective_guild_id = guild_id or self._extract_guild_id(alert_data, remediation_data)
            success = await self.discord.send_message(
                self.builder.build_remediation_failed_embed(
                    alert,
                    remediation,
                    penalty_points,
                ),
                guild_id=effective_guild_id,
            )

            if success:
                logger.info(
                    f'Notification sent for failed remediation: {remediation.id} ({penalty_points} penalty)'
                )
            else:
                logger.warning(
                    f'Failed to send notification for failed remediation: {remediation.id}'
                )

            return success

        except Exception as e:
            logger.error(
                f'Error notifying failed remediation {remediation.id}: {type(e).__name__}: {e}'
            )
            return False

    async def notify_alert_reopened(self, alert: Alert, guild_id: str | None = None) -> bool:
        """
        Notifica que una alerta previamente cerrada ha reaparecido

        Args:
            alert: Alerta que fue reabierta

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            alert_data = alert.model_dump()
            effective_guild_id = guild_id or self._extract_guild_id(alert_data)
            success = await self.discord.send_message(
                self.builder.build_alert_reopened_embed(alert),
                guild_id=effective_guild_id,
            )

            if success:
                logger.info(f'Notification sent for reopened alert: {alert.alert_id}')
            else:
                logger.warning(f'Failed to send notification for reopened alert: {alert.alert_id}')

            return success

        except Exception as e:
            logger.error(
                f'Error notifying reopened alert {alert.alert_id}: {type(e).__name__}: {e}'
            )
            return False

    async def send_test_notification(self, message: str, guild_id: str | None = None) -> bool:
        """
        Envia una notificacion de prueba simple

        Args:
            message: Mensaje de texto a enviar

        Returns:
            bool: True si se envio correctamente
        """
        try:
            payload = {'content': f'🧪 Test: {message}', 'username': self.bot_username}
            success = await self.discord.send_message(payload, guild_id=guild_id)

            if success:
                logger.info('Test notification sent successfully')
            else:
                logger.warning('Failed to send test notification')

            return success

        except Exception as e:
            logger.error(f'Error sending test notification: {type(e).__name__}: {e}')
            return False


# Singleton instance
notification_service = NotificationService()
