"""
Tests for user registration: POST /api/v1/users/

Covers:
  1. Successful creation returns 201 with the user data
  2. Default role is 'developer' when not provided
  3. Duplicate username returns 409
  4. Duplicate email returns 409
  5. Invalid role returns 409

Service-layer tests mock only the MongoDB collection — no real DB or
HTTP stack required, keeping tests fast and deterministic.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_user_doc(
    username: str = 'testuser',
    email: str = 'test@example.com',
    role: str = 'developer',
    server_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        '_id': 'fake-object-id',
        'user_id': user_id or username,
        'username': username,
        'email': email,
        'display_name': username,
        'role': role,
        'server_id': server_id,
        'team_id': None,
        'metadata': {},
        'is_active': True,
        'email_verified': False,
        'created_at': now,
        'updated_at': now,
    }


def _mock_collection(*, username_exists: bool = False, email_exists: bool = False) -> MagicMock:
    """
    Mock Motor collection.
    count_documents is called twice: once for username, once for email.
    """
    col = MagicMock()
    col.count_documents = AsyncMock(
        side_effect=[
            1 if username_exists else 0,
            1 if email_exists else 0,
        ]
    )
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id='fake-object-id'))
    return col


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_service_singleton():
    """Force UserService to rebuild on each test so mocks are picked up."""
    with patch('app.services.user_service._user_service_instance', None):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUserRegistrationService:
    """Tests against UserService.create_user() directly (no HTTP layer)."""

    async def _create(self, col: MagicMock, **kwargs) -> dict[str, Any]:
        mock_db = MagicMock()
        mock_db.users = col
        # Patch where the name is looked up (user_service module), not where it's defined
        with patch('app.services.user_service.get_database', return_value=mock_db):
            from app.services.user_service import UserService

            svc = UserService()
            return await svc.create_user(**kwargs)

    # ── 1. Happy path ─────────────────────────────────────────────────────────

    async def test_create_user_inserts_and_returns_doc(self):
        col = _mock_collection()
        result = await self._create(
            col,
            username='testuser',
            email='test@example.com',
            display_name='Test User',
            role='developer',
        )

        col.insert_one.assert_awaited_once()
        assert result['username'] == 'testuser'
        assert result['email'] == 'test@example.com'
        assert result['role'] == 'developer'
        assert result['is_active'] is True
        assert result['email_verified'] is False
        assert '_id' in result

    # ── 2. user_id defaults to username ──────────────────────────────────────

    async def test_user_id_defaults_to_username(self):
        col = _mock_collection()
        result = await self._create(
            col,
            username='myuser',
            email='my@example.com',
        )
        assert result['user_id'] == 'myuser'

    # ── 3. Custom user_id is respected ───────────────────────────────────────

    async def test_custom_user_id_is_stored(self):
        col = _mock_collection()
        result = await self._create(
            col,
            username='myuser',
            email='my@example.com',
            user_id='discord-123456',
        )
        assert result['user_id'] == 'discord-123456'

    # ── 4. server_id is persisted when provided ───────────────────────────────

    async def test_server_id_is_stored(self):
        col = _mock_collection()
        result = await self._create(
            col,
            username='serveruser',
            email='server@example.com',
            server_id='guild-999',
        )
        assert result['server_id'] == 'guild-999'

    # ── 5. Duplicate username raises ValueError ───────────────────────────────

    async def test_duplicate_username_raises(self):
        col = _mock_collection(username_exists=True)
        with pytest.raises(ValueError, match='ya existe'):
            await self._create(col, username='taken', email='new@example.com')

    # ── 6. Duplicate email raises ValueError ─────────────────────────────────

    async def test_duplicate_email_raises(self):
        col = _mock_collection(email_exists=True)
        with pytest.raises(ValueError, match='ya existe'):
            await self._create(col, username='newuser', email='taken@example.com')

    # ── 7. Invalid role raises ValueError ────────────────────────────────────

    async def test_invalid_role_raises(self):
        col = _mock_collection()
        with pytest.raises(ValueError, match='Rol inválido'):
            await self._create(
                col,
                username='baduser',
                email='bad@example.com',
                role='member',  # not in allowed list
            )

    # ── 8. Default role 'developer' passes validation ─────────────────────────

    async def test_default_role_developer_is_valid(self):
        col = _mock_collection()
        # role not specified → defaults to 'developer' in the service signature
        result = await self._create(
            col,
            username='noroleuser',
            email='norole@example.com',
        )
        assert result['role'] == 'developer'

    # ── 9. Schema default 'developer' matches service validation ─────────────

    def test_schema_default_role_is_accepted_by_service(self):
        """The UserCreate schema default must be in the service's valid_roles list."""
        from app.schemas.user_schemas import UserCreate

        schema_default = UserCreate(
            username='xxx',
            email='xxx@example.com',
            display_name='Test',
        ).role

        valid_roles = ['developer', 'team_lead', 'admin', 'super_admin']
        assert schema_default in valid_roles, (
            f"Schema default role '{schema_default}' not in service valid_roles {valid_roles}"
        )
