"""
Notification Service - Orquesta el envio de notificaciones a Slack y Discord
"""

from app.integrations.discord.discord_client import discord_client
from app.integrations.discord.message_builder import discord_message_builder
from app.integrations.notifications.message_builder import message_builder
from app.integrations.notifications.slack_client import slack_client
from app.models.alert import Alert
from app.models.remediation import Remediation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Servicio para enviar notificaciones de eventos del sistema"""

    def __init__(self):
        self.slack = slack_client
        self.discord = discord_client
        self.message_builder = message_builder
        self.discord_builder = discord_message_builder

    async def notify_new_alert(self, alert: Alert) -> bool:
        """
        Notifica sobre una nueva alerta de seguridad detectada

        Args:
            alert: Objeto Alert con los datos de la alerta

        Returns:
            bool: True si al menos una notificacion se envio correctamente
        """
        try:
            slack_ok = await self.slack.send_message(self.message_builder.build_alert_message(alert))
            discord_ok = await self.discord.send_message(
                self.discord_builder.build_alert_embed(alert)
            )

            success = slack_ok or discord_ok
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
            bool: True si al menos una notificacion se envio correctamente
        """
        try:
            slack_ok = await self.slack.send_message(
                self.message_builder.build_remediation_verified_message(
                    alert, remediation, points_earned
                )
            )
            discord_ok = await self.discord.send_message(
                self.discord_builder.build_remediation_verified_embed(
                    alert, remediation, points_earned
                )
            )

            success = slack_ok or discord_ok
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
        Notifica que un rescan detecto que la vulnerabilidad persiste (remediacion falsa)

        Args:
            alert: Alerta que supuestamente fue remediada
            remediation: Objeto Remediation
            penalty_points: Puntos de penalizacion

        Returns:
            bool: True si al menos una notificacion se envio correctamente
        """
        try:
            slack_ok = await self.slack.send_message(
                self.message_builder.build_remediation_failed_message(
                    alert, remediation, penalty_points
                )
            )
            discord_ok = await self.discord.send_message(
                self.discord_builder.build_remediation_failed_embed(
                    alert, remediation, penalty_points
                )
            )

            success = slack_ok or discord_ok
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
            bool: True si al menos una notificacion se envio correctamente
        """
        try:
            slack_ok = await self.slack.send_message(
                self.message_builder.build_alert_reopened_message(alert)
            )
            discord_ok = await self.discord.send_message(
                self.discord_builder.build_alert_reopened_embed(alert)
            )

            success = slack_ok or discord_ok
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
            bool: True si al menos un canal recibio el mensaje
        """
        try:
            slack_ok = await self.slack.send_simple_message(f'🧪 Test: {message}')
            discord_ok = await self.discord.send_simple_message(f'🧪 Test: {message}')

            success = slack_ok or discord_ok
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
