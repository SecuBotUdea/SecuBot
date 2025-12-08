"""
Notification Service - Orquesta el envio de notificaciones a Slack
"""

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
        self.message_builder = message_builder

    async def notify_new_alert(self, alert: Alert) -> bool:
        """
        Notifica sobre una nueva alerta de seguridad detectada

        Args:
            alert: Objeto Alert con los datos de la alerta

        Returns:
            bool: True si la notificacion se envio correctamente
        """
        try:
            # Construir mensaje
            message = self.message_builder.build_alert_message(alert)

            # Enviar a Slack
            success = await self.slack.send_message(message)

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
            # Construir mensaje
            message = self.message_builder.build_remediation_verified_message(
                alert, remediation, points_earned
            )

            # Enviar a Slack
            success = await self.slack.send_message(message)

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
            bool: True si la notificacion se envio correctamente
        """
        try:
            # Construir mensaje
            message = self.message_builder.build_remediation_failed_message(
                alert, remediation, penalty_points
            )

            # Enviar a Slack
            success = await self.slack.send_message(message)

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
            # Construir mensaje
            message = self.message_builder.build_alert_reopened_message(alert)

            # Enviar a Slack
            success = await self.slack.send_message(message)

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
            success = await self.slack.send_simple_message(f'🧪 Test: {message}')

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
