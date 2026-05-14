"""
Discord Message Builder - Construye embeds de Discord para notificaciones de seguridad
"""

from datetime import datetime, timezone
from typing import Any

from app.models.alert import Alert
from app.models.remediation import Remediation


class DiscordMessageBuilder:
    """Construye mensajes de Discord con formato de embeds"""

    # Colores de embed por severidad (enteros en formato decimal)
    SEVERITY_COLOR = {
        'CRITICAL': 0xFF0000,  # Rojo
        'HIGH': 0xFF6B00,      # Naranja
        'MEDIUM': 0xFFB800,    # Amarillo
        'LOW': 0x36A64F,       # Verde
        'INFO': 0x808080,      # Gris
    }

    # Emojis por severidad
    SEVERITY_EMOJI = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🔵',
        'INFO': '⚪',
    }

    @staticmethod
    def _format_timestamp(dt: datetime) -> str:
        """Formatea timestamp en formato ISO para Discord"""
        return f'<t:{int(dt.timestamp())}:f>'

    def build_alert_embed(self, alert: Alert) -> dict[str, Any]:
        """
        Construye embed para nueva alerta de seguridad

        Args:
            alert: Objeto Alert del modelo

        Returns:
            dict: Payload JSON con el embed para Discord webhook
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, '⚠️')
        color = self.SEVERITY_COLOR.get(severity, 0x808080)

        description = ''
        if alert.normalized_payload:
            description = alert.normalized_payload.get('description', '')
            if description:
                description = description[:200]

        embed: dict[str, Any] = {
            'title': f'{emoji} Nueva Alerta de Seguridad',
            'color': color,
            'fields': [
                {'name': 'Severidad', 'value': severity, 'inline': True},
                {'name': 'Componente', 'value': alert.component, 'inline': True},
                {
                    'name': 'Estado',
                    'value': alert.status.replace('_', ' ').title(),
                    'inline': True,
                },
                {'name': 'Calidad', 'value': alert.quality.title(), 'inline': True},
            ],
            'footer': {
                'text': f'Alert ID: {alert.alert_id} | Signature: {alert.signature[:16]}...'
            },
            'timestamp': alert.first_seen.isoformat(),
        }

        if description:
            embed['description'] = description

        return {
            'embeds': [embed],
            'username': 'SecuBot',
        }

    def build_remediation_verified_embed(
        self, alert: Alert, remediation: Remediation, points_earned: int
    ) -> dict[str, Any]:
        """
        Construye embed para remediacion verificada exitosamente

        Args:
            alert: Alerta que fue remediada
            remediation: Objeto Remediation
            points_earned: Puntos ganados

        Returns:
            dict: Payload JSON para Discord webhook
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, '⚠️')

        embed: dict[str, Any] = {
            'title': '✅ Remediacion Verificada',
            'description': (
                f'La vulnerabilidad **{severity}** en `{alert.component}` '
                'ha sido verificada como resuelta.'
            ),
            'color': 0x36A64F,
            'fields': [
                {'name': 'Puntos Ganados', 'value': f'+{points_earned} 🎯', 'inline': True},
                {'name': 'Severidad', 'value': f'{emoji} {severity}', 'inline': True},
                {'name': 'Usuario', 'value': remediation.user_id, 'inline': True},
            ],
            'footer': {'text': '🎉 Excelente trabajo en seguridad del codigo!'},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return {'embeds': [embed], 'username': 'SecuBot'}

    def build_remediation_failed_embed(
        self, alert: Alert, remediation: Remediation, penalty_points: int
    ) -> dict[str, Any]:
        """
        Construye embed cuando rescan detecta que la vulnerabilidad persiste

        Args:
            alert: Alerta que supuestamente fue remediada
            remediation: Objeto Remediation
            penalty_points: Puntos de penalizacion (negativo)

        Returns:
            dict: Payload JSON para Discord webhook
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, '⚠️')

        embed: dict[str, Any] = {
            'title': '❌ Remediacion No Verificada',
            'description': (
                f'El rescan detecto que la vulnerabilidad **{severity}** '
                f'en `{alert.component}` aun esta presente.'
            ),
            'color': 0xFF0000,
            'fields': [
                {'name': 'Penalizacion', 'value': f'{penalty_points} puntos', 'inline': True},
                {'name': 'Severidad', 'value': f'{emoji} {severity}', 'inline': True},
                {'name': 'Usuario', 'value': remediation.user_id, 'inline': True},
            ],
            'footer': {
                'text': '💡 Revisar la correccion y ejecutar verificacion local antes de marcar como arreglada.'
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return {'embeds': [embed], 'username': 'SecuBot'}

    def build_alert_reopened_embed(self, alert: Alert) -> dict[str, Any]:
        """
        Construye embed cuando una alerta previamente cerrada reaparece

        Args:
            alert: Alerta que fue reabierta

        Returns:
            dict: Payload JSON para Discord webhook
        """
        severity = alert.severity.upper()
        emoji = self.SEVERITY_EMOJI.get(severity, '⚠️')

        embed: dict[str, Any] = {
            'title': '🔁 Alerta Reabierta',
            'description': (
                f'Una vulnerabilidad previamente resuelta ha reaparecido '
                f'en `{alert.component}`'
            ),
            'color': 0xFFA500,
            'fields': [
                {'name': 'Severidad', 'value': f'{emoji} {severity}', 'inline': True},
                {'name': 'Reaperturas', 'value': str(alert.reopen_count), 'inline': True},
            ],
            'footer': {
                'text': '⚠️ Esto puede indicar una regresion en el codigo o un fix incompleto.'
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return {'embeds': [embed], 'username': 'SecuBot'}

    def build_rescan_result_embed(
        self,
        alert_id: str,
        still_exists: bool,
        local_reopen_count: int,
        normalizer_reopen_count: int,
    ) -> dict[str, Any]:
        """
        Construye embed con el resultado de un rescan solicitado por Discord

        Args:
            alert_id: ID de la alerta escaneada
            still_exists: ¿La vulnerabilidad sigue presente?
            local_reopen_count: Contador local de reaperturas
            normalizer_reopen_count: Contador del normalizador

        Returns:
            dict: Payload JSON para Discord
        """
        if still_exists:
            title = '🔴 Vulnerabilidad Persiste'
            color = 0xFF0000
            status_text = 'La vulnerabilidad **AUN EXISTE** segun el normalizador.'
        else:
            title = '✅ Vulnerabilidad Resuelta'
            color = 0x36A64F
            status_text = 'La vulnerabilidad ha sido **REMEDIADA** correctamente.'

        embed: dict[str, Any] = {
            'title': title,
            'description': status_text,
            'color': color,
            'fields': [
                {'name': 'Alert ID', 'value': alert_id, 'inline': False},
                {
                    'name': 'Reopen Count Local',
                    'value': str(local_reopen_count),
                    'inline': True,
                },
                {
                    'name': 'Reopen Count Normalizador',
                    'value': str(normalizer_reopen_count),
                    'inline': True,
                },
            ],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return {'embeds': [embed], 'username': 'SecuBot'}


# Singleton instance
discord_message_builder = DiscordMessageBuilder()
