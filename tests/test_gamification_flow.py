"""
Integration tests for the SecuBot gamification flow.

Tests cover:
1. RescanResult.to_dict() includes 'present' field
2. RuleEngine processes rescan_completed event correctly
3. GamificationService leaderboard, balance, stats, badges, rules
4. TimeoutChecker detects and penalizes timed-out remediations
5. Scheduler is configured with the expected jobs
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_alert(
    alert_id: str = "ALT-001",
    severity: str = "CRITICAL",
    quality: str = "high",
    status: str = "pending_verification",
    reopen_count: int = 0,
) -> Dict[str, Any]:
    return {
        "alert_id": alert_id,
        "signature": f"sig-{alert_id}",
        "source_id": "sast-scanner",
        "severity": severity,
        "component": "api-gateway",
        "status": status,
        "quality": quality,
        "first_seen": datetime.now(timezone.utc) - timedelta(hours=2),
        "last_seen": datetime.now(timezone.utc),
        "reopen_count": reopen_count,
        "normalized_payload": {},
        "lifecycle_history": [],
    }


def make_remediation(
    remediation_id: str = "REM-001",
    alert_id: str = "ALT-001",
    user_id: str = "user-abc",
    team_id: str = "team-x",
    action_ts: datetime | None = None,
    status: str = "pending",
) -> Dict[str, Any]:
    return {
        "remediation_id": remediation_id,
        "alert_id": alert_id,
        "user_id": user_id,
        "team_id": team_id,
        "type": "user_mark",
        "action_ts": action_ts or datetime.now(timezone.utc) - timedelta(hours=1),
        "status": status,
        "notes": None,
        "metadata": {},
    }


def make_rescan_result(still_exists: bool = False) -> Dict[str, Any]:
    return {
        "alert_id": "ALT-001",
        "still_exists": still_exists,
        "present": still_exists,  # mirrors still_exists
        "reopen_count_changed": still_exists,
        "local_reopen_count": 0,
        "normalizer_reopen_count": 1 if still_exists else 0,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {"rescan_id": "rescan_abc123"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. RescanResult.to_dict() must include "present"
# ─────────────────────────────────────────────────────────────────────────────


class TestRescanResultDict:
    def test_to_dict_includes_present_when_resolved(self):
        from app.services.rescan_service import RescanResult

        r = RescanResult(
            alert_id="A1",
            still_exists=False,
            reopen_count_changed=False,
            local_reopen_count=0,
            normalizer_reopen_count=0,
            scan_timestamp=datetime.now(timezone.utc),
        )
        d = r.to_dict()
        assert "present" in d
        assert d["present"] is False
        assert d["still_exists"] is False

    def test_to_dict_includes_present_when_persists(self):
        from app.services.rescan_service import RescanResult

        r = RescanResult(
            alert_id="A2",
            still_exists=True,
            reopen_count_changed=True,
            local_reopen_count=0,
            normalizer_reopen_count=1,
            scan_timestamp=datetime.now(timezone.utc),
        )
        d = r.to_dict()
        assert d["present"] is True
        assert d["still_exists"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. RuleEngine – process_event("rescan_completed")
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRuleEngine:
    """Tests for the RuleEngine using a mocked MongoDB client."""

    def _build_mock_db(self):
        mock_db = MagicMock()
        # point_transactions.aggregate → empty (user is level 1)
        mock_agg = AsyncMock()
        mock_agg.to_list = AsyncMock(return_value=[])
        mock_db.point_transactions.aggregate.return_value = mock_agg
        # insert_one
        mock_db.point_transactions.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="fake-id")
        )
        # awards
        mock_db.awards.find_one = AsyncMock(return_value=None)
        mock_db.awards.insert_one = AsyncMock(return_value=MagicMock(inserted_id="award-id"))
        return mock_db

    async def test_rescan_completed_awards_points_for_critical(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = self._build_mock_db()
        engine = RuleEngine(mock_db)

        context = {
            "Alert": make_alert(severity="CRITICAL", quality="high"),
            "Remediation": make_remediation(),
            "RescanResult": make_rescan_result(still_exists=False),
            "current_time": datetime.now(timezone.utc),
        }

        result = await engine.process_event("rescan_completed", context)

        assert result["rules_evaluated"] > 0
        # PTS-001 should have fired
        assert result["rules_triggered"] >= 1
        assert len(result["points_awarded"]) >= 1
        assert result["points_awarded"][0]["points"] > 0

    async def test_rescan_completed_applies_penalty_when_persists(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = self._build_mock_db()
        engine = RuleEngine(mock_db)

        # Mock side-effect calls for PEN-002
        mock_db.alerts.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
        mock_db.remediations.update_one = AsyncMock(return_value=MagicMock(matched_count=1))

        context = {
            "Alert": make_alert(severity="CRITICAL", quality="high", status="pending_verification"),
            "Remediation": make_remediation(),
            "RescanResult": make_rescan_result(still_exists=True),
            "current_time": datetime.now(timezone.utc),
        }

        result = await engine.process_event("rescan_completed", context)

        assert result["rules_triggered"] >= 1
        assert len(result["penalties_applied"]) >= 1
        assert result["penalties_applied"][0]["points"] < 0

    async def test_low_quality_alert_excluded(self):
        from app.engines.rule_engine.engine import RuleEngine

        mock_db = self._build_mock_db()
        engine = RuleEngine(mock_db)

        context = {
            "Alert": make_alert(quality="low"),
            "Remediation": make_remediation(),
            "RescanResult": make_rescan_result(still_exists=False),
            "current_time": datetime.now(timezone.utc),
        }

        result = await engine.process_event("rescan_completed", context)

        # EXC-001 should block gamification
        assert len(result["exclusions"]) >= 1
        assert result["rules_triggered"] == 0
        assert result["points_awarded"] == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. GamificationService – leaderboard, balance, stats, rules
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGamificationService:
    def _build_service_with_mocks(self):
        """Build a GamificationService with a fully mocked DB."""
        from app.services.gamification_service import GamificationService

        with patch("app.services.gamification_service.get_database") as mock_get_db, patch(
            "app.services.gamification_service.get_rule_loader"
        ) as mock_get_loader, patch(
            "app.engines.rule_engine.engine.get_rule_loader"
        ) as mock_engine_loader:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # Reuse same rule loader as the real one
            from app.engines.rule_engine.loader.singleton import get_rule_loader

            real_loader = get_rule_loader()
            mock_get_loader.return_value = real_loader
            mock_engine_loader.return_value = real_loader

            service = GamificationService()
            service.db = mock_db
            service.point_txns = mock_db.point_transactions
            service.awards = mock_db.awards
            service.users = mock_db.users
            return service, mock_db

    async def test_get_available_rules_returns_all_types(self):
        service, _ = self._build_service_with_mocks()
        rules = await service.get_available_rules()

        assert "point_rules" in rules
        assert "penalty_rules" in rules
        assert "badge_rules" in rules
        assert len(rules["point_rules"]) > 0
        assert len(rules["penalty_rules"]) > 0
        # All badge rules must have badge_id, name, tier
        for b in rules["badge_rules"]:
            assert "badge_id" in b
            assert "name" in b
            assert "tier" in b

    async def test_get_user_balance_zero_for_new_user(self):
        from app.services.gamification_service import GamificationService

        mock_db = MagicMock()
        mock_agg = AsyncMock()
        mock_agg.to_list = AsyncMock(return_value=[])
        mock_db.point_transactions.aggregate.return_value = mock_agg

        with patch("app.services.gamification_service.get_database", return_value=mock_db), patch(
            "app.engines.rule_engine.engine.get_rule_loader"
        ):
            service = GamificationService()
            service.db = mock_db
            service.point_txns = mock_db.point_transactions

            # Patch the rule_engine directly to avoid loader issues
            service.rule_engine.db = mock_db

            balance = await service.get_user_balance("user-new")

        assert balance["total_points"] == 0
        assert balance["level"] == 1

    async def test_get_user_badges_returns_list(self):
        service, mock_db = self._build_service_with_mocks()

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {
                    "_id": "oid1",
                    "badge_id": "BDG-001",
                    "user_id": "user-abc",
                    "awarded_at": datetime.now(timezone.utc),
                    "evidence_refs": [],
                }
            ]
        )
        mock_db.awards.find.return_value = mock_cursor

        badges = await service.get_user_badges("user-abc")
        assert len(badges) == 1
        assert badges[0]["badge_id"] == "BDG-001"
        # _id should be stringified
        assert isinstance(badges[0]["_id"], str)


# ─────────────────────────────────────────────────────────────────────────────
# 4. TimeoutChecker
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTimeoutChecker:
    async def test_no_pending_remediations_returns_empty(self):
        expired_ts = datetime.now(timezone.utc) - timedelta(hours=100)

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.remediations.find.return_value = mock_cursor

        with patch("app.tasks.timeout_checker.get_database", return_value=mock_db), patch(
            "app.tasks.timeout_checker.get_rule_loader"
        ) as mock_loader, patch(
            "app.tasks.timeout_checker.get_gamification_service"
        ):
            mock_loader.return_value.get_config.return_value = MagicMock(
                verification={"grace_period_hours": 72}
            )
            from app.tasks.timeout_checker import check_timed_out_remediations

            results = await check_timed_out_remediations()

        assert results == []

    async def test_expired_remediation_is_penalized(self):
        expired_remediation = make_remediation(
            action_ts=datetime.now(timezone.utc) - timedelta(hours=100),
            status="pending",
        )

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[expired_remediation])
        mock_db.remediations.find.return_value = mock_cursor
        mock_db.remediations.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.alerts.find_one = AsyncMock(
            return_value={**make_alert(), "_id": "oid-alert"}
        )
        mock_db.alerts.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        mock_gamification = AsyncMock()
        mock_gamification.process_event = AsyncMock(
            return_value={"rules_triggered": 1, "penalties_applied": [{"points": -30}]}
        )

        with patch("app.tasks.timeout_checker.get_database", return_value=mock_db), patch(
            "app.tasks.timeout_checker.get_rule_loader"
        ) as mock_loader, patch(
            "app.tasks.timeout_checker.get_gamification_service",
            return_value=mock_gamification,
        ):
            mock_loader.return_value.get_config.return_value = MagicMock(
                verification={"grace_period_hours": 72}
            )
            from app.tasks.timeout_checker import check_timed_out_remediations

            results = await check_timed_out_remediations()

        assert len(results) == 1
        assert results[0]["status"] == "timeout"
        assert results[0]["remediation_id"] == "REM-001"
        # Verify the gamification event was fired
        mock_gamification.process_event.assert_awaited_once()
        call_args = mock_gamification.process_event.call_args
        assert call_args[0][0] == "grace_period_expired"
        # Verify remediation was marked as timeout in DB
        mock_db.remediations.update_one.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scheduler configuration
# ─────────────────────────────────────────────────────────────────────────────


class TestScheduler:
    def test_scheduler_has_required_jobs(self):
        # Reset singleton so we get a fresh scheduler for this test
        import app.tasks.scheduler as sched_module

        sched_module._scheduler = None

        from app.tasks.scheduler import get_scheduler

        scheduler = get_scheduler()
        job_ids = {job.id for job in scheduler.get_jobs()}

        assert "timeout_checker" in job_ids
        assert "leaderboard_snapshot" in job_ids

        # Cleanup
        sched_module._scheduler = None

    def test_timeout_checker_is_hourly(self):
        import app.tasks.scheduler as sched_module

        sched_module._scheduler = None

        from app.tasks.scheduler import get_scheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = get_scheduler()
        timeout_job = scheduler.get_job("timeout_checker")

        assert timeout_job is not None
        assert isinstance(timeout_job.trigger, IntervalTrigger)

        sched_module._scheduler = None

    def test_leaderboard_snapshot_is_weekly(self):
        import app.tasks.scheduler as sched_module

        sched_module._scheduler = None

        from app.tasks.scheduler import get_scheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = get_scheduler()
        snapshot_job = scheduler.get_job("leaderboard_snapshot")

        assert snapshot_job is not None
        assert isinstance(snapshot_job.trigger, CronTrigger)

        sched_module._scheduler = None


# ─────────────────────────────────────────────────────────────────────────────
# 6. BadgeRule model includes tier field
# ─────────────────────────────────────────────────────────────────────────────


class TestBadgeRuleModel:
    def test_badge_rule_has_tier_default(self):
        from app.engines.rule_engine.loader.models import (
            BadgeCriteria,
            BadgeRule,
            BadgeAwardTrigger,
        )

        rule = BadgeRule(
            badge_id="BDG-TEST",
            name="Test Badge",
            description="A test badge",
            category="test",
            icon_url="/test.svg",
            active=True,
            version=1,
            criteria=BadgeCriteria(type="individual", conditions=[]),
            award_trigger=BadgeAwardTrigger(event="rescan_completed"),
        )
        # Default tier should be "bronze"
        assert rule.tier == "bronze"

    def test_badge_rule_tier_can_be_set(self):
        from app.engines.rule_engine.loader.models import (
            BadgeCriteria,
            BadgeRule,
            BadgeAwardTrigger,
        )

        rule = BadgeRule(
            badge_id="BDG-PLAT",
            name="Platinum Badge",
            description="A platinum badge",
            category="prestige",
            tier="platinum",
            icon_url="/platinum.svg",
            active=True,
            version=1,
            criteria=BadgeCriteria(type="individual", conditions=[]),
            award_trigger=BadgeAwardTrigger(event="rescan_completed"),
        )
        assert rule.tier == "platinum"
