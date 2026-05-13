"""
DiscordWebhookService - Persistencia y resolución de webhooks por servidor (guild).
"""

from datetime import datetime, timezone
from typing import Any, cast

from app.database.mongodb import get_database


class DiscordWebhookService:
    """Gestiona webhooks de Discord almacenados en MongoDB."""

    @property
    def collection(self):
        return get_database().discord_webhooks

    async def upsert_webhook(self, webhook_data: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza el webhook activo para un guild_id."""
        guild_id = webhook_data.get('guild_id')
        if not guild_id:
            raise ValueError('guild_id es requerido para guardar webhook')

        now = datetime.now(timezone.utc)
        data = {
            **webhook_data,
            'guild_id': str(guild_id),
            'active': webhook_data.get('active', True),
            'updated_at': now,
        }

        existing = await self.collection.find_one({'guild_id': str(guild_id)})
        if existing is None:
            data['created_at'] = now

        await self.collection.update_one(
            {'guild_id': str(guild_id)},
            {'$set': data},
            upsert=True,
        )

        stored = cast(
            dict[str, Any] | None,
            await self.collection.find_one({'guild_id': str(guild_id)}),
        )
        if not stored:
            raise ValueError(f'No se pudo persistir webhook para guild {guild_id}')

        stored['_id'] = str(stored['_id'])
        return stored

    async def get_webhook_by_guild_id(self, guild_id: str) -> dict[str, Any] | None:
        """Obtiene webhook activo por guild_id."""
        webhook = cast(
            dict[str, Any] | None,
            await self.collection.find_one({'guild_id': str(guild_id), 'active': True}),
        )
        if webhook:
            webhook['_id'] = str(webhook['_id'])
        return webhook

    async def resolve_webhook_url(self, guild_id: str | None) -> str | None:
        """Resuelve URL de webhook para un servidor."""
        if not guild_id:
            return None
        webhook = await self.get_webhook_by_guild_id(guild_id)
        if not webhook:
            return None
        return webhook.get('webhook_url')

    async def deactivate_webhook(self, guild_id: str, reason: str | None = None) -> None:
        """Marca webhook de un guild como inactivo."""
        update_data: dict[str, Any] = {
            'active': False,
            'updated_at': datetime.now(timezone.utc),
        }
        if reason:
            update_data['deactivated_reason'] = reason
        await self.collection.update_one(
            {'guild_id': str(guild_id)},
            {'$set': update_data},
        )


_discord_webhook_service_instance: DiscordWebhookService | None = None


def get_discord_webhook_service() -> DiscordWebhookService:
    """Factory singleton de DiscordWebhookService."""
    global _discord_webhook_service_instance
    if _discord_webhook_service_instance is None:
        _discord_webhook_service_instance = DiscordWebhookService()
    return _discord_webhook_service_instance
