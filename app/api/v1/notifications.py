"""
Notifications API Endpoints - Para probar la integración con Slack
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.alert import Alert
from app.models.remediation import Remediation
from app.services.notification_service import notification_service

router = APIRouter()


class TestNotificationRequest(BaseModel):
    """Request para enviar notificación de prueba"""

    message: str = Field(..., description='Mensaje de prueba a enviar', min_length=1)


class TestAlertRequest(BaseModel):
    """Request para enviar alerta de prueba"""

    severity: str = Field(default='HIGH', description='Severidad de la alerta')
    component: str = Field(default='test-service', description='Componente afectado')
    alert_id: str = Field(default='test-alert-001', description='ID de la alerta')


@router.post('/notifications/test', summary='Enviar notificación de prueba simple')
async def send_test_notification(request: TestNotificationRequest):
    """
    Envía una notificación de prueba simple a Slack

    Útil para verificar que la configuración del webhook funciona correctamente
    """
    success = await notification_service.send_test_notification(request.message)

    if not success:
        raise HTTPException(
            status_code=500,
            detail='Failed to send notification. Check Slack configuration and logs.',
        )

    return {
        'success': True,
        'message': 'Test notification sent successfully',
        'sent_message': request.message,
    }


@router.post('/notifications/test-alert', summary='Enviar alerta de prueba')
async def send_test_alert(request: TestAlertRequest):
    """
    Envía una alerta de seguridad de prueba a Slack

    Esto crea un objeto Alert ficticio y envía la notificación formateada
    """
    # Crear alerta de prueba
    test_alert = Alert(
        alert_id=request.alert_id,
        signature=f'test-sig-{datetime.utcnow().timestamp()}',
        source_id='test-source',
        severity=request.severity,
        component=request.component,
        status='open',
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        quality='high',
        normalized_payload={
            'description': 'Esta es una alerta de prueba generada desde el endpoint de testing',
            'cvss_score': 7.5,
        },
    )

    success = await notification_service.notify_new_alert(test_alert)

    if not success:
        raise HTTPException(
            status_code=500,
            detail='Failed to send alert notification. Check Slack configuration and logs.',
        )

    return {
        'success': True,
        'message': 'Alert notification sent successfully',
        'alert': {
            'alert_id': test_alert.alert_id,
            'severity': test_alert.severity,
            'component': test_alert.component,
        },
    }


@router.post(
    '/notifications/test-remediation-verified', summary='Enviar remediación verificada de prueba'
)
async def send_test_remediation_verified():
    """
    Envía una notificación de remediación verificada de prueba

    Simula el flujo completo de una vulnerabilidad siendo arreglada y verificada
    """
    # Crear alerta y remediación de prueba
    test_alert = Alert(
        alert_id='test-alert-remediated',
        signature='test-sig-remediated',
        source_id='test-source',
        severity='CRITICAL',
        component='authentication-service',
        status='verified',
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        quality='high',
        normalized_payload={
            'description': 'SQL Injection vulnerability in login endpoint',
        },
    )

    test_remediation = Remediation(
        remediation_id='test-rem-001',
        alert_id=test_alert.alert_id,
        user_id='U12345678',  # Slack user ID format
        team_id='team-001',
        type='user_mark',
        action_ts=datetime.utcnow(),
        status='verified',
    )

    points_earned = 100  # Puntos por CRITICAL

    success = await notification_service.notify_remediation_verified(
        test_alert, test_remediation, points_earned
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail='Failed to send remediation notification. Check Slack configuration.',
        )

    return {
        'success': True,
        'message': 'Remediation verified notification sent successfully',
        'points_earned': points_earned,
    }


@router.post(
    '/notifications/test-remediation-failed', summary='Enviar remediación fallida de prueba'
)
async def send_test_remediation_failed():
    """
    Envía una notificación de remediación fallida de prueba

    Simula cuando un rescan detecta que la vulnerabilidad persiste
    """
    # Crear alerta y remediación de prueba
    test_alert = Alert(
        alert_id='test-alert-failed',
        signature='test-sig-failed',
        source_id='test-source',
        severity='HIGH',
        component='api-gateway',
        status='reopened',
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        quality='high',
    )

    test_remediation = Remediation(
        remediation_id='test-rem-failed-001',
        alert_id=test_alert.alert_id,
        user_id='U12345678',
        team_id='team-001',
        type='user_mark',
        action_ts=datetime.utcnow(),
        status='failed',
    )

    penalty_points = -25  # Penalizacion por false remediation

    success = await notification_service.notify_remediation_failed(
        test_alert, test_remediation, penalty_points
    )

    if not success:
        raise HTTPException(
            status_code=500, detail='Failed to send failed remediation notification.'
        )

    return {
        'success': True,
        'message': 'Remediation failed notification sent successfully',
        'penalty_points': penalty_points,
    }


@router.post('/notifications/test-alert-reopened', summary='Enviar alerta reabierta de prueba')
async def send_test_alert_reopened():
    """
    Envía una notificación de alerta reabierta

    Simula cuando una vulnerabilidad previamente cerrada reaparece
    """
    test_alert = Alert(
        alert_id='test-alert-reopened',
        signature='test-sig-reopened',
        source_id='test-source',
        severity='MEDIUM',
        component='user-service',
        status='reopened',
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        quality='high',
        reopen_count=2,  # Segunda vez que reaparece
        last_reopened_at=datetime.utcnow(),
    )

    success = await notification_service.notify_alert_reopened(test_alert)

    if not success:
        raise HTTPException(
            status_code=500, detail='Failed to send reopened alert notification.'
        )

    return {
        'success': True,
        'message': 'Alert reopened notification sent successfully',
        'reopen_count': test_alert.reopen_count,
    }
