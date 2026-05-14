"""
Integration tests for the SecuBot gamification flow.

Covers:
  1. RescanResult.to_dict() exposes 'present' field
  2. RuleEngine.process_event() for rescan_completed (points & penalties)
  3. GamificationService queries (available_rules, balance, badges)
  4. TimeoutChecker detects timed-out remediations and fires grace_period_expired
  5. Scheduler exposes the expected APScheduler jobs
  6. BadgeRule model has a tier field with sensible default

All tests that touch app code mock the database layer so that no real
MongoDB connection is required.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Test-data factories
# ─────────────────────────────────────────────────────────────────────────────


def make_alert(
    alert_id: str = 'ALT-001',
    severity: str = 'CRITICAL',
    quality: str = 'high',
    status: str = 'pending_verification',
    reopen_count: int = 0,
) -> dict[str, Any]:
    return {
        'alert_id': alert_id,
        'signature': f'sig-{alert_id}',
        'source_id': 'sast-scanner',
        'severity': severity,
        'component': 'api-gateway',
        'status': status,
        'quality': quality,
        'first_seen': datetime.now(timezone.utc) - timedelta(hours=2),
        'last_seen': datetime.now(timezone.utc),
        'reopen_count': reopen_count,
        'normalized_payload': {},
        'lifecycle_history': [],
    }


def make_remediation(
    remediation_id: str = 'REM-001',
    alert_id: str = 'ALT-001',
    user_id: str = 'user-abc',
    team_id: str = 'team-x',
    action_ts: datetime | None = None,
    status: str = 'pending',
) -> dict[str, Any]:
    return {
        'remediation_id': remediation_id,
        'alert_id': alert_id,
        'user_id': user_id,
        'team_id': team_id,
        'type': 'user_mark',
        'action_ts': action_ts or (datetime.now(timezone.utc) - timedelta(hours=1)),
        'status': status,
        'notes': None,
        'metadata': {},
    }


def make_rescan_result(still_exists: bool = False) -> dict[str, Any]:
    """Dict representation used as RescanResult context value."""
    return {
        'alert_id': 'ALT-001',
        'still_exists': still_exists,
        'present': still_exists,
        'reopen_count_changed': still_exists,
        'local_reopen_count': 0,
        'normalizer_reopen_count': 1 if still_exists else 0,
        'scan_timestamp': datetime.now(timezone.utc).isoformat(),
        'metadata': {'rescan_id': 'rescan_abc123'},
    }


def _make_mock_db() -> MagicMock:
    """Return a MagicMock that mimics the Motor MongoDB client surface."""
    mock_db = MagicMock()

    # Default aggregate cursor → empty result (user has 0 points → level 1)
    agg_cursor = MagicMock()
    agg_cursor.to_list = AsyncMock(return_value=[])
    mock_db.point_transactions.aggregate.return_value = agg_cursor

    # Default insert_one
    mock_db.point_transactions.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id='fake-txn-id')
    )

    # Awards collection
    mock_db.awards.find_one = AsyncMock(return_value=None)
    mock_db.awards.insert_one = AsyncMock(return_value=MagicMock(inserted_id='fake-award-id'))

    # Alerts / remediations for side-effects
    mock_db.alerts.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    mock_db.remediations.update_one = AsyncMock(return_value=MagicMock(matched_count=1))

    # count_documents / distinct used by badge_evaluator on all entity collections
    for col in ('point_transactions', 'alerts', 'remediations', 'rescan_results'):
        getattr(mock_db, col).count_documents = AsyncMock(return_value=0)
        getattr(mock_db, col).distinct = AsyncMock(return_value=[])
        agg = MagicMock()
        agg.to_list = AsyncMock(return_value=[])
        getattr(mock_db, col).aggregate.return_value = agg

    return mock_db


# ─────────────────────────────────────────────────────────────────────────────
# 1. RescanResult.to_dict() must expose "present"
# ─────────────────────────────────────────────────────────────────────────────


class TestRescanResultDict:
    def test_present_is_false_when_resolved(self):
        from app.services.rescan_service import RescanResult

        r = RescanResult(
            alert_id='A1',
            still_exists=False,
            reopen_count_changed=False,
            local_reopen_count=0,
            normalizer_reopen_count=0,
            scan_timestamp=datetime.now(timezone.utc),
        )
        d = r.to_dict()
        assert 'present' in d
        assert d['present'] is False
        assert d['still_exists'] is False

    def test_present_is_true_when_persists(self):
        from app.services.rescan_service import RescanResult

        r = RescanResult(
            alert_id='A2',
            still_exists=True,
            reopen_count_changed=True,
            local_reopen_count=0,
            normalizer_reopen_count=1,
            scan_timestamp=datetime.now(timezone.utc),
        )
        d = r.to_dict()
        assert d['present'] is True
        assert d['still_exists'] is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. RuleEngine – process_event("rescan_completed")
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRuleEngine:
    """Tests for the RuleEngine with a mocked MongoDB client."""

    async def test_awards_points_for_critical_resolved(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = _make_mock_db()
        engine = RuleEngine(mock_db)

        result = await engine.process_event(
            'rescan_completed',
            {
                'Alert': make_alert(severity='CRITICAL', quality='high'),
                'Remediation': make_remediation(),
                'RescanResult': make_rescan_result(still_exists=False),
                'current_time': datetime.now(timezone.utc),
            },
        )

        assert result['rules_evaluated'] > 0
        assert result['rules_triggered'] >= 1
        assert len(result['points_awarded']) >= 1
        assert result['points_awarded'][0]['points'] > 0

    async def test_applies_penalty_when_vulnerability_persists(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = _make_mock_db()
        engine = RuleEngine(mock_db)

        result = await engine.process_event(
            'rescan_completed',
            {
                'Alert': make_alert(
                    severity='CRITICAL', quality='high', status='pending_verification'
                ),
                'Remediation': make_remediation(),
                'RescanResult': make_rescan_result(still_exists=True),
                'current_time': datetime.now(timezone.utc),
            },
        )

        assert result['rules_triggered'] >= 1
        assert len(result['penalties_applied']) >= 1
        assert result['penalties_applied'][0]['points'] < 0

    async def test_low_quality_alert_is_excluded(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = _make_mock_db()
        engine = RuleEngine(mock_db)

        result = await engine.process_event(
            'rescan_completed',
            {
                'Alert': make_alert(quality='low'),
                'Remediation': make_remediation(),
                'RescanResult': make_rescan_result(still_exists=False),
                'current_time': datetime.now(timezone.utc),
            },
        )

        # EXC-001 must block gamification
        assert len(result['exclusions']) >= 1
        assert result['rules_triggered'] == 0
        assert result['points_awarded'] == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. GamificationService – available_rules, balance, badges
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGamificationService:
    """Tests for GamificationService using mocked DB and the real RuleLoader."""

    # ------------------------------------------------------------------
    # Helper: build a GamificationService with mocked DB but real rules.
    # We use patch as a decorator-style context to ensure the mocks are
    # active during __init__, then keep the object references after exit.
    # ------------------------------------------------------------------
    def _build_service(self):
        from app.engines.rule_engine.loader.singleton import get_rule_loader as _real_loader
        from app.services.gamification_service import GamificationService

        mock_db = _make_mock_db()
        real_loader = _real_loader()

        with (
            patch(
                'app.services.gamification_service.get_database',
                return_value=mock_db,
            ),
            patch(
                'app.services.gamification_service.get_rule_loader',
                return_value=real_loader,
            ),
            patch(
                'app.engines.rule_engine.engine.get_rule_loader',
                return_value=real_loader,
            ),
        ):
            svc = GamificationService()

        # Ensure collection references point at mock_db
        svc.db = mock_db
        svc.point_txns = mock_db.point_transactions
        svc.awards = mock_db.awards
        svc.users = mock_db.users

        return svc, mock_db

    # ------------------------------------------------------------------

    async def test_get_available_rules_returns_all_types(self):
        svc, _ = self._build_service()
        rules = await svc.get_available_rules()

        assert 'point_rules' in rules
        assert 'penalty_rules' in rules
        assert 'badge_rules' in rules
        assert len(rules['point_rules']) > 0
        assert len(rules['penalty_rules']) > 0
        for badge in rules['badge_rules']:
            assert 'badge_id' in badge
            assert 'name' in badge
            assert 'tier' in badge

    async def test_get_user_balance_returns_zero_for_new_user(self):
        svc, mock_db = self._build_service()

        # Aggregate returns nothing → zero points
        empty_agg = MagicMock()
        empty_agg.to_list = AsyncMock(return_value=[])
        mock_db.point_transactions.aggregate.return_value = empty_agg
        # Also wire rule_engine to use same mock
        svc.rule_engine.db = mock_db

        balance = await svc.get_user_balance('user-new')

        assert balance['total_points'] == 0
        assert balance['level'] == 1

    async def test_get_user_badges_returns_stringified_id(self):
        svc, mock_db = self._build_service()

        award_doc = {
            '_id': 'oid1',
            'badge_id': 'BDG-001',
            'user_id': 'user-abc',
            'awarded_at': datetime.now(timezone.utc),
            'evidence_refs': [],
        }

        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=[award_doc])
        mock_db.awards.find.return_value = cursor

        badges = await svc.get_user_badges('user-abc')

        assert len(badges) == 1
        assert badges[0]['badge_id'] == 'BDG-001'
        assert isinstance(badges[0]['_id'], str)


# ─────────────────────────────────────────────────────────────────────────────
# 4. TimeoutChecker
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTimeoutChecker:
    async def test_returns_empty_when_nothing_pending(self):
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[])
        mock_db.remediations.find.return_value = cursor

        mock_loader = MagicMock()
        mock_loader.get_config.return_value = MagicMock(verification={'grace_period_hours': 72})

        with (
            patch('app.tasks.timeout_checker.get_database', return_value=mock_db),
            patch('app.tasks.timeout_checker.get_rule_loader', return_value=mock_loader),
            patch('app.tasks.timeout_checker.get_gamification_service'),
        ):
            from app.tasks.timeout_checker import check_timed_out_remediations

            results = await check_timed_out_remediations()

        assert results == []

    async def test_expired_remediation_triggers_penalty_and_db_update(self):
        expired = make_remediation(
            action_ts=datetime.now(timezone.utc) - timedelta(hours=100),
            status='pending',
        )
        alert_doc = {**make_alert(status='pending_verification'), '_id': 'oid-alert'}

        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[expired])
        mock_db.remediations.find.return_value = cursor
        mock_db.remediations.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.alerts.find_one = AsyncMock(return_value=alert_doc)
        mock_db.alerts.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        mock_loader = MagicMock()
        mock_loader.get_config.return_value = MagicMock(verification={'grace_period_hours': 72})

        mock_gamification = MagicMock()
        mock_gamification.process_event = AsyncMock(
            return_value={'rules_triggered': 1, 'penalties_applied': [{'points': -30}]}
        )

        with (
            patch('app.tasks.timeout_checker.get_database', return_value=mock_db),
            patch('app.tasks.timeout_checker.get_rule_loader', return_value=mock_loader),
            patch(
                'app.tasks.timeout_checker.get_gamification_service',
                return_value=mock_gamification,
            ),
        ):
            from app.tasks.timeout_checker import check_timed_out_remediations

            results = await check_timed_out_remediations()

        assert len(results) == 1
        assert results[0]['status'] == 'timeout'
        assert results[0]['remediation_id'] == 'REM-001'

        # grace_period_expired event must have been fired
        mock_gamification.process_event.assert_awaited_once()
        assert mock_gamification.process_event.call_args[0][0] == 'grace_period_expired'

        # Remediation must be updated to 'timeout' in the DB
        mock_db.remediations.update_one.assert_called_once()

        # Alert must be restored to 'open'
        mock_db.alerts.update_one.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scheduler configuration
# ─────────────────────────────────────────────────────────────────────────────


class TestScheduler:
    """Verify APScheduler is configured with the required jobs."""

    def _fresh_scheduler(self):
        """Return a fresh scheduler instance (resets the singleton)."""
        import app.tasks.scheduler as mod

        mod._scheduler = None
        from app.tasks.scheduler import get_scheduler

        return get_scheduler(), mod

    def test_required_jobs_are_registered(self):
        scheduler, mod = self._fresh_scheduler()
        try:
            job_ids = {j.id for j in scheduler.get_jobs()}
            assert 'timeout_checker' in job_ids
            assert 'leaderboard_snapshot' in job_ids
        finally:
            mod._scheduler = None

    def test_timeout_checker_uses_interval_trigger(self):
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler, mod = self._fresh_scheduler()
        try:
            job = scheduler.get_job('timeout_checker')
            assert job is not None
            assert isinstance(job.trigger, IntervalTrigger)
        finally:
            mod._scheduler = None

    def test_leaderboard_snapshot_uses_cron_trigger(self):
        from apscheduler.triggers.cron import CronTrigger

        scheduler, mod = self._fresh_scheduler()
        try:
            job = scheduler.get_job('leaderboard_snapshot')
            assert job is not None
            assert isinstance(job.trigger, CronTrigger)
        finally:
            mod._scheduler = None


# ─────────────────────────────────────────────────────────────────────────────
# 6. BadgeRule Pydantic model includes a tier field
# ─────────────────────────────────────────────────────────────────────────────


class TestBadgeRuleModel:
    def _make_rule(self, **kwargs):
        from app.engines.rule_engine.loader.models import (
            BadgeAwardTrigger,
            BadgeCriteria,
            BadgeRule,
        )

        defaults = {
            'badge_id': 'BDG-TEST',
            'name': 'Test Badge',
            'description': 'desc',
            'category': 'test',
            'icon_url': '/test.svg',
            'active': True,
            'version': 1,
            'criteria': BadgeCriteria(type='individual', conditions=[]),
            'award_trigger': BadgeAwardTrigger(event='rescan_completed'),
        }
        defaults.update(kwargs)
        return BadgeRule(**defaults)

    def test_default_tier_is_bronze(self):
        rule = self._make_rule()
        assert rule.tier == 'bronze'

    def test_tier_can_be_overridden(self):
        for tier in ('silver', 'gold', 'platinum'):
            rule = self._make_rule(badge_id=f'BDG-{tier}', tier=tier)
            assert rule.tier == tier


# ─────────────────────────────────────────────────────────────────────────────
# 7. BadgeRule loader merges badges.yaml into rules.yaml
# ─────────────────────────────────────────────────────────────────────────────


class TestBadgeLoader:
    def test_badges_yaml_loaded_into_rule_loader(self):
        """
        After load_badges(), the loader must expose additional BDG-xxx
        entries that are defined only in badges.yaml (BDG-101+).
        """
        from app.engines.rule_engine.loader.singleton import get_rule_loader

        loader = get_rule_loader()
        all_badges = loader.get_all_active_badges()
        badge_ids = {b.badge_id for b in all_badges}

        # rules.yaml defines BDG-001..BDG-006
        assert 'BDG-001' in badge_ids

        # badges.yaml adds BDG-101+ ; at least one should be present
        extra = {bid for bid in badge_ids if bid >= 'BDG-101'}
        assert len(extra) > 0, 'No supplementary badges from badges.yaml were loaded'

    def test_all_badges_have_tier_field(self):
        from app.engines.rule_engine.loader.singleton import get_rule_loader

        loader = get_rule_loader()
        for badge in loader.get_all_active_badges():
            assert hasattr(badge, 'tier'), f"{badge.badge_id} missing 'tier'"
            assert badge.tier in (
                'bronze',
                'silver',
                'gold',
                'platinum',
            ), f"{badge.badge_id} has unexpected tier '{badge.tier}'"
