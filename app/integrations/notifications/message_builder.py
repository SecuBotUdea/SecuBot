# -*- coding: utf-8 -*-
"""
Message Builder - Construye mensajes formateados para Slack usando Block Kit
"""

from datetime import datetime
from typing import Any

from app.models.alert import Alert
from app.models.remediation import Remediation


class MessageBuilder:
    """Construye mensajes de Slack con formato Block Kit"""

    # Emojis por severidad (usando nombres de emoji de Slack)
    SEVERITY_EMOJI = {
        'CRITICAL': ':red_circle:',
        'HIGH': ':large_orange_circle:',
        'MEDIUM': ':large_yellow_circle:',
        'LOW': ':large_blue_circle:',
        'INFO': ':white_circle:',
    }

    # Colores para attachments
    SEVERITY_COLOR = {
        'CRITICAL': '#FF0000',
        'HIGH': '#FF6B00',
        'MEDIUM': '#FFB800',
        'LOW': '#36A64F',
        'INFO': '#808080',
    }

    @staticmethod
    def _format_timestamp(dt: datetime) -> str:
        """Formatea timestamp para Slack (epoch)"""
        return f'<!date^{int(dt.timestamp())}^{{date_short_pretty}} {{time}}|{dt.isoformat()}>'

    def build_alert_message(self, alert: Alert) -> dict[str, Any]:
        """
        Construye mensaje para nueva alerta de seguridad

        Args:
            alert: Objeto Alert del modelo

        Returns:
            dict: Mensaje formateado para Slack
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, ':warning:')
        color = self.SEVERITY_COLOR.get(severity, '#808080')

        # Texto fallback
        fallback_text = f'{emoji} Nueva alerta {severity} detectada en {alert.component}'

        # Header block
        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'{emoji} Nueva Alerta de Seguridad',
                    'emoji': True,
                },
            },
            {'type': 'divider'},
        ]

        # Informacion principal
        fields = [
            {'type': 'mrkdwn', 'text': f'*Severidad:*\n{severity}'},
            {'type': 'mrkdwn', 'text': f'*Componente:*\n{alert.component}'},
            {
                'type': 'mrkdwn',
                'text': f'*Estado:*\n{alert.status.replace("_", " ").title()}',
            },
            {'type': 'mrkdwn', 'text': f'*Calidad:*\n{alert.quality.title()}'},
        ]

        blocks.append({'type': 'section', 'fields': fields})

        # Timestamp
        blocks.append(
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': f'Detectada: {self._format_timestamp(alert.first_seen)}',
                    }
                ],
            }
        )

        # Informacion adicional del payload si existe
        if alert.normalized_payload:
            description = alert.normalized_payload.get('description', '')
            if description:
                blocks.append(
                    {
                        'type': 'section',
                        'text': {'type': 'mrkdwn', 'text': f'*Descripcion:*\n{description[:200]}'},
                    }
                )

        # Footer con ID
        blocks.append(
            {
                'type': 'context',
                'elements': [
                    {'type': 'mrkdwn', 'text': f'Alert ID: `{alert.alert_id}`'},
                    {'type': 'mrkdwn', 'text': f'Signature: `{alert.signature[:16]}...`'},
                ],
            }
        )

        return {
            'text': fallback_text,
            'blocks': blocks,
            'attachments': [{'color': color, 'fallback': fallback_text}],
        }

    def build_remediation_verified_message(
        self, alert: Alert, remediation: Remediation, points_earned: int
    ) -> dict[str, Any]:
        """
        Construye mensaje para remediacion verificada exitosamente

        Args:
            alert: Alerta que fue remediada
            remediation: Objeto Remediation
            points_earned: Puntos ganados

        Returns:
            dict: Mensaje formateado para Slack
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, ':warning:')

        fallback_text = (
            f':white_check_mark: Remediacion verificada: {alert.component} - +{points_earned} puntos'
        )

        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': ':white_check_mark: Remediacion Verificada',
                    'emoji': True,
                },
            },
            {'type': 'divider'},
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'La vulnerabilidad *{severity}* en `{alert.component}` ha sido verificada como resuelta.',
                },
            },
        ]

        # Informacion de puntos
        fields = [
            {'type': 'mrkdwn', 'text': f'*Puntos Ganados:*\n+{points_earned} :dart:'},
            {'type': 'mrkdwn', 'text': f'*Severidad:*\n{emoji} {severity}'},
            {
                'type': 'mrkdwn',
                'text': f'*Usuario:*\n<@{remediation.user_id}>',
            },
        ]

        blocks.append({'type': 'section', 'fields': fields})

        # Celebracion
        blocks.append(
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': ':tada: Excelente trabajo en seguridad del codigo!',
                    }
                ],
            }
        )

        return {'text': fallback_text, 'blocks': blocks}

    def build_remediation_failed_message(
        self, alert: Alert, remediation: Remediation, penalty_points: int
    ) -> dict[str, Any]:
        """
        Construye mensaje cuando rescan detecta que la vulnerabilidad persiste

        Args:
            alert: Alerta que supuestamente fue remediada
            remediation: Objeto Remediation
            penalty_points: Puntos de penalizacion

        Returns:
            dict: Mensaje formateado para Slack
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, ':warning:')

        fallback_text = (
            f':x: Remediacion no verificada: {alert.component} - {penalty_points} puntos'
        )

        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': ':x: Remediacion No Verificada',
                    'emoji': True,
                },
            },
            {'type': 'divider'},
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'El rescan detecto que la vulnerabilidad *{severity}* en `{alert.component}` aun esta presente.',
                },
            },
        ]

        # Informacion de penalizacion
        fields = [
            {'type': 'mrkdwn', 'text': f'*Penalizacion:*\n{penalty_points} puntos'},
            {'type': 'mrkdwn', 'text': f'*Severidad:*\n{emoji} {severity}'},
            {'type': 'mrkdwn', 'text': f'*Usuario:*\n<@{remediation.user_id}>'},
        ]

        blocks.append({'type': 'section', 'fields': fields})

        # Consejo
        blocks.append(
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': ':bulb: *Siguiente paso:* Revisar la correccion y ejecutar verificacion local antes de marcar como arreglada.',
                },
            }
        )

        return {'text': fallback_text, 'blocks': blocks, 'attachments': [{'color': '#FF0000'}]}

    def build_alert_reopened_message(self, alert: Alert) -> dict[str, Any]:
        """
        Construye mensaje cuando una alerta previamente cerrada reaparece

        Args:
            alert: Alerta que fue reabierta

        Returns:
            dict: Mensaje formateado para Slack
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, ':warning:')

        fallback_text = f':arrows_counterclockwise: Alerta reabierta: {alert.component} ({severity})'

        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': ':arrows_counterclockwise: Alerta Reabierta',
                    'emoji': True,
                },
            },
            {'type': 'divider'},
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'Una vulnerabilidad previamente resuelta ha reaparecido en `{alert.component}`',
                },
            },
        ]

        fields = [
            {'type': 'mrkdwn', 'text': f'*Severidad:*\n{emoji} {severity}'},
            {'type': 'mrkdwn', 'text': f'*Reaperturas:*\n{alert.reopen_count}'},
        ]

        blocks.append({'type': 'section', 'fields': fields})

        blocks.append(
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': ':warning: Esto puede indicar una regresion en el codigo o un fix incompleto.',
                    }
                ],
            }
        )

        return {
            'text': fallback_text,
            'blocks': blocks,
            'attachments': [{'color': '#FFA500'}],
        }


# Singleton instance
message_builder = MessageBuilder()
