"""
TimeoutChecker - Penaliza remediaciones pendientes que superaron el periodo de gracia.

Flujo:
1. Busca todas las remediaciones con status="pending" cuyo action_ts supera
   el grace_period_hours configurado en rules.yaml.
2. Para cada una construye el contexto { Alert, Remediation } y dispara el
   evento "grace_period_expired" en el GamificationService.
3. El RuleEngine aplica PEN-001 (penalización por timeout).
4. Actualiza el status de la remediación a "timeout" y el de la alerta a "open".
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from app.database.mongodb import get_database
from app.engines.rule_engine import get_rule_loader
from app.services.gamification_service import get_gamification_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def check_timed_out_remediations() -> List[Dict[str, Any]]:
    """
    Detecta y penaliza remediaciones que superaron el periodo de gracia.

    Returns:
        Lista de resultados por remediación procesada.
    """
    db = get_database()
    rule_loader = get_rule_loader()
    gamification_service = get_gamification_service()

    # Obtener grace_period_hours desde la configuración de rules.yaml
    config = rule_loader.get_config()
    grace_period_hours = config.verification.get('grace_period_hours', 72)

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=grace_period_hours)

    # Buscar remediaciones pendientes que ya superaron el plazo
    pending = await db.remediations.find(
        {
            'status': 'pending',
            'action_ts': {'$lte': cutoff_time},
        }
    ).to_list(length=None)

    if not pending:
        logger.info('TimeoutChecker: no pending remediations timed out.')
        return []

    results: List[Dict[str, Any]] = []

    for remediation in pending:
        remediation_id = remediation.get('remediation_id', str(remediation.get('_id', '')))
        alert_id = remediation.get('alert_id', '')

        try:
            # Obtener la alerta asociada
            alert = await db.alerts.find_one({'alert_id': alert_id})
            if not alert:
                logger.warning(
                    f'TimeoutChecker: alert {alert_id} not found for '
                    f'remediation {remediation_id}, skipping.'
                )
                continue

            # Convertir _id a str para evitar problemas de serialización
            alert['_id'] = str(alert.get('_id', ''))
            remediation['_id'] = str(remediation.get('_id', ''))

            # Construir contexto para el RuleEngine
            context: Dict[str, Any] = {
                'Alert': alert,
                'Remediation': remediation,
                'current_time': datetime.now(timezone.utc),
            }

            # Disparar evento grace_period_expired → RuleEngine aplica PEN-001
            result = await gamification_service.process_event('grace_period_expired', context)

            # Actualizar status de la remediación a "timeout"
            now = datetime.now(timezone.utc)
            await db.remediations.update_one(
                {'remediation_id': remediation_id},
                {
                    '$set': {
                        'status': 'timeout',
                        'updated_at': now,
                        'timeout_at': now,
                    }
                },
            )

            # Restaurar la alerta a "open" si estaba en pending_verification
            if alert.get('status') == 'pending_verification':
                await db.alerts.update_one(
                    {'alert_id': alert_id},
                    {
                        '$set': {'status': 'open', 'updated_at': now},
                        '$push': {
                            'lifecycle_history': {
                                'timestamp': now,
                                'old_status': 'pending_verification',
                                'new_status': 'open',
                                'metadata': {
                                    'event': 'grace_period_expired',
                                    'remediation_id': remediation_id,
                                },
                            }
                        },
                    },
                )

            logger.info(
                f'TimeoutChecker: remediation {remediation_id} timed out — '
                f'rules_triggered={result.get("rules_triggered", 0)}'
            )
            results.append(
                {
                    'remediation_id': remediation_id,
                    'alert_id': alert_id,
                    'status': 'timeout',
                    'gamification_result': result,
                }
            )

        except Exception as e:
            logger.error(
                f'TimeoutChecker: error processing remediation {remediation_id}: {e}',
                exc_info=True,
            )
            results.append(
                {
                    'remediation_id': remediation_id,
                    'alert_id': alert_id,
                    'status': 'error',
                    'error': str(e),
                }
            )

    logger.info(
        f'TimeoutChecker: processed {len(results)} timed-out remediations '
        f'(grace_period={grace_period_hours}h, cutoff={cutoff_time.isoformat()})'
    )
    return results
