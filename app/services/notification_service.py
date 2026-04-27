"""
Notification Service - Orquesta el envio de notificaciones a Discord
"""

from app.integrations.discord.discord_client import discord_client
from app.integrations.discord.message_builder import discord_message_builder
from app.models.alert import Alert
from app.models.remediation import Remediation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Servicio para enviar notificaciones de eventos del sistema via Discord"""

    def __init__(self):
        self.discord = discord_client
        self.builder = discord_message_builder

    async def notify_new_alert(self, alert: Alert) -> bool:
        """
        Notifica sobre una nueva alerta de seguridad detectada

        Args:
            alert: Objeto Alert con los datos de la alerta

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            success = await self.discord.send_message(self.builder.build_alert_embed(alert))

            if success:
                logger.info(f'Notification sent for new alert: {alert.alert_id}')
            else:
                logger.warning(f'Failed to send notification for alert: {alert.alert_id}')

            return success

        except Exception as e:
            logger.error(f'Error notifying new alert {alert.alert_id}: {type(e).__name__}: {e}')
            return False

    async def notify_remediation_verified(
        self, alert: Alert, remediation: Remediation, points_earned: int
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
            success = await self.discord.send_message(
                self.builder.build_remediation_verified_embed(alert, remediation, points_earned)
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
        self, alert: Alert, remediation: Remediation, penalty_points: int
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
            success = await self.discord.send_message(
                self.builder.build_remediation_failed_embed(alert, remediation, penalty_points)
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

    async def notify_alert_reopened(self, alert: Alert) -> bool:
        """
        Notifica que una alerta previamente cerrada ha reaparecido

        Args:
            alert: Alerta que fue reabierta

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            success = await self.discord.send_message(
                self.builder.build_alert_reopened_embed(alert)
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

    async def send_test_notification(self, message: str) -> bool:
        """
        Envia una notificacion de prueba simple

        Args:
            message: Mensaje de texto a enviar

        Returns:
            bool: True si se envio correctamente
        """
        try:
            success = await self.discord.send_simple_message(f'🧪 Test: {message}')

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
