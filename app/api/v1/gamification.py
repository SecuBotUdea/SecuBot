"""
Gamification API Router - Leaderboard, user stats, badges and available rules
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.gamification_service import get_gamification_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get('/leaderboard', summary='Obtener leaderboard de SecuPoints')
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100, description='Número de entradas a retornar'),
    team_id: str | None = Query(default=None, description='Filtrar por equipo'),
    timeframe: str | None = Query(
        default=None,
        description='Periodo de tiempo: daily | weekly | monthly (omitir para all-time)',
    ),
) -> dict[str, Any]:
    """
    Retorna el ranking de usuarios ordenado por SecuPoints.

    Parámetros opcionales:
    - **limit**: cantidad de posiciones a mostrar (1-100, default 10)
    - **team_id**: filtra el leaderboard a un equipo específico
    - **timeframe**: `daily`, `weekly`, `monthly` — omitir para all-time
    """
    try:
        service = get_gamification_service()
        entries = await service.get_leaderboard(limit=limit, team_id=team_id, timeframe=timeframe)
        return {
            'leaderboard': entries,
            'period': timeframe or 'all-time',
            'limit': limit,
            'team_id': team_id,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f'Error getting leaderboard: {e}')
        raise HTTPException(status_code=500, detail=f'Error al obtener leaderboard: {str(e)}') from e


@router.get('/users/{user_id}/balance', summary='Balance y nivel de un usuario')
async def get_user_balance(user_id: str) -> dict[str, Any]:
    """
    Retorna el balance de SecuPoints, nivel actual y progreso hacia el siguiente nivel.

    El nivel se calcula automáticamente:
    - Nivel 1: 0-499 pts  — Aprendiz de Seguridad
    - Nivel 2: 500-1499 pts — Vigilante del Código
    - Nivel 3: 1500-3999 pts — Guardián DevSecOps
    - Nivel 4: 4000-9999 pts — Centinela Élite
    - Nivel 5: 10000+ pts — Maestro de la Seguridad
    """
    try:
        service = get_gamification_service()
        balance = await service.get_user_balance(user_id)
        return balance
    except Exception as e:
        logger.error(f'Error getting balance for user {user_id}: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al obtener balance del usuario: {str(e)}'
        ) from e


@router.get('/users/{user_id}/stats', summary='Estadísticas completas de un usuario')
async def get_user_stats(user_id: str) -> dict[str, Any]:
    """
    Retorna estadísticas completas de gamificación para un usuario:
    - Balance de puntos y nivel
    - Badges obtenidos (por tier)
    - Estadísticas de puntos ganados/perdidos
    - Transacciones recientes
    """
    try:
        service = get_gamification_service()
        stats = await service.get_user_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f'Error getting stats for user {user_id}: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al obtener estadísticas del usuario: {str(e)}'
        ) from e


@router.get('/users/{user_id}/badges', summary='Badges obtenidos por un usuario')
async def get_user_badges(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200, description='Número máximo de badges'),
) -> dict[str, Any]:
    """
    Retorna los badges (insignias) que ha ganado un usuario, ordenados por fecha de obtención.
    """
    try:
        service = get_gamification_service()
        badges = await service.get_user_badges(user_id, limit=limit)
        return {
            'user_id': user_id,
            'badges': badges,
            'total': len(badges),
        }
    except Exception as e:
        logger.error(f'Error getting badges for user {user_id}: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al obtener badges del usuario: {str(e)}'
        ) from e


@router.get('/rules', summary='Reglas de gamificación activas')
async def get_available_rules() -> dict[str, Any]:
    """
    Retorna todas las reglas activas del sistema de gamificación:
    - Reglas de puntos (PTS-XXX)
    - Reglas de penalización (PEN-XXX)
    - Badges disponibles (BDG-XXX)
    """
    try:
        service = get_gamification_service()
        rules = await service.get_available_rules()
        return rules
    except Exception as e:
        logger.error(f'Error getting available rules: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al obtener reglas de gamificación: {str(e)}'
        ) from e


@router.get('/activity', summary='Actividad reciente del sistema')
async def get_recent_activity(
    limit: int = Query(default=20, ge=1, le=100, description='Número de actividades'),
    user_id: str | None = Query(default=None, description='Filtrar por usuario'),
    team_id: str | None = Query(default=None, description='Filtrar por equipo'),
) -> dict[str, Any]:
    """
    Retorna actividad reciente: transacciones de puntos y badges otorgados.
    Se puede filtrar por usuario o equipo.
    """
    try:
        service = get_gamification_service()
        activities = await service.get_recent_activity(
            limit=limit, user_id=user_id, team_id=team_id
        )
        return {
            'activities': activities,
            'total': len(activities),
            'user_id': user_id,
            'team_id': team_id,
        }
    except Exception as e:
        logger.error(f'Error getting recent activity: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al obtener actividad reciente: {str(e)}'
        ) from e


@router.post(
    '/users/{user_id}/evaluate-badges',
    summary='Evaluar y otorgar badges pendientes para un usuario',
)
async def evaluate_user_badges(user_id: str) -> dict[str, Any]:
    """
    Fuerza la evaluación de todos los criterios de badges para un usuario.
    Útil para verificar si el usuario califica para nuevos badges.

    Retorna la lista de badges recién otorgados (puede ser vacía si ya los tenía todos).
    """
    try:
        service = get_gamification_service()
        awarded = await service.evaluate_user_badges(user_id)
        return {
            'user_id': user_id,
            'newly_awarded': awarded,
            'count': len(awarded),
        }
    except Exception as e:
        logger.error(f'Error evaluating badges for user {user_id}: {e}')
        raise HTTPException(
            status_code=500, detail=f'Error al evaluar badges del usuario: {str(e)}'
        ) from e
