"""
Scheduler - APScheduler para tareas periódicas de SecuBot.

Tareas programadas:
- Cada hora: check_timed_out_remediations() → penaliza remediaciones expiradas
- Cada domingo a las 00:00 UTC: actualizar snapshot de leaderboard semanal en DB
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Wrappers síncronos que corren coroutines en el event-loop del scheduler
# ─────────────────────────────────────────────────────────────────────────────


async def _run_timeout_checker() -> None:
    """Detecta y penaliza remediaciones que superaron el periodo de gracia."""
    from app.tasks.timeout_checker import check_timed_out_remediations

    try:
        results = await check_timed_out_remediations()
        logger.info(f'Scheduler[timeout_checker]: {len(results)} remediations processed.')
    except Exception as e:
        logger.error(f'Scheduler[timeout_checker]: unexpected error — {e}', exc_info=True)


async def _run_leaderboard_snapshot() -> None:
    """Guarda un snapshot semanal del leaderboard en la colección leaderboard_snapshots."""
    try:
        from datetime import datetime, timezone

        from app.database.mongodb import get_database
        from app.services.gamification_service import get_gamification_service

        service = get_gamification_service()
        db = get_database()

        entries = await service.get_leaderboard(limit=100, timeframe='weekly')
        snapshot = {
            'snapshot_at': datetime.now(timezone.utc),
            'period': 'weekly',
            'entries': entries,
        }
        await db.leaderboard_snapshots.insert_one(snapshot)
        logger.info(
            f'Scheduler[leaderboard_snapshot]: saved weekly snapshot with {len(entries)} entries.'
        )
    except Exception as e:
        logger.error(f'Scheduler[leaderboard_snapshot]: unexpected error — {e}', exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton del scheduler
# ─────────────────────────────────────────────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Retorna (y construye si necesario) la instancia global del scheduler.

    El scheduler utiliza AsyncIOScheduler de APScheduler que se integra
    directamente con el event loop de asyncio que usa FastAPI/uvicorn.
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone='UTC')

    # ── Tarea 1: Timeout checker — cada hora ──────────────────────────────
    _scheduler.add_job(
        _run_timeout_checker,
        trigger=IntervalTrigger(hours=1),
        id='timeout_checker',
        name='Check timed-out remediations',
        replace_existing=True,
        misfire_grace_time=300,  # 5 min de tolerancia si el servidor estaba caído
    )

    # ── Tarea 2: Leaderboard snapshot — cada domingo a medianoche UTC ─────
    _scheduler.add_job(
        _run_leaderboard_snapshot,
        trigger=CronTrigger(day_of_week='sun', hour=0, minute=0, second=0),
        id='leaderboard_snapshot',
        name='Weekly leaderboard snapshot',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        'Scheduler configured with 2 jobs: timeout_checker (hourly), leaderboard_snapshot (weekly).'
    )
    return _scheduler
