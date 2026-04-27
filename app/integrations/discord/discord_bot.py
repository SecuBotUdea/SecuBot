# -*- coding: utf-8 -*-
"""
Discord Bot - Recibe el comando !rescan desde Discord y ejecuta el re-escaneo

Comandos disponibles:
    !rescan <alert_id>  - Verifica si una vulnerabilidad sigue presente
"""

import asyncio
from typing import Optional

import discord
from discord.ext import commands

from app.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


def _make_bot() -> commands.Bot:
    """Crea la instancia del bot con los intents necesarios"""
    intents = discord.Intents.default()
    intents.message_content = True  # Necesario para leer el contenido de mensajes
    return commands.Bot(command_prefix='!', intents=intents)


bot = _make_bot()


@bot.event
async def on_ready() -> None:
    logger.info(f'Discord bot conectado como {bot.user} (ID: {bot.user.id if bot.user else "?"})')


@bot.command(name='rescan')
async def rescan_command(ctx: commands.Context, alert_id: Optional[str] = None) -> None:
    """
    Verifica si una vulnerabilidad sigue presente consultando el normalizador.

    Uso: !rescan <alert_id>

    Ejemplo: !rescan alert_abc123
    """
    if not alert_id:
        await ctx.send(
            '⚠️ Debes proporcionar un `alert_id`.\n'
            'Uso: `!rescan <alert_id>`\n'
            'Ejemplo: `!rescan alert_abc123`'
        )
        return

    # Lazy import para evitar dependencias circulares en tiempo de importación
    from app.services.alert_service import get_alert_service
    from app.services.rescan_service import get_rescan_service
    from app.integrations.discord.message_builder import discord_message_builder

    await ctx.send(f'🔍 Ejecutando rescan para `{alert_id}`...')

    try:
        # 1. Obtener la alerta de MongoDB
        alert_service = get_alert_service()
        alert_data = await alert_service.get_alert(alert_id)

        if not alert_data:
            await ctx.send(f'❌ Alerta `{alert_id}` no encontrada en la base de datos.')
            return

        local_reopen_count = alert_data.get('reopen_count', 0)

        # 2. Ejecutar el rescan contra el normalizador
        rescan_service = get_rescan_service()
        result = await rescan_service.check_alert_exists(
            alert_id=alert_id,
            local_reopen_count=local_reopen_count,
        )

        # 3. Construir y enviar embed con el resultado
        payload = discord_message_builder.build_rescan_result_embed(
            alert_id=result.alert_id,
            still_exists=result.still_exists,
            local_reopen_count=result.local_reopen_count,
            normalizer_reopen_count=result.normalizer_reopen_count,
        )

        embed_data = payload['embeds'][0]
        embed = discord.Embed(
            title=embed_data.get('title', ''),
            description=embed_data.get('description', ''),
            color=embed_data.get('color', 0x808080),
        )
        for field in embed_data.get('fields', []):
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', True),
            )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f'Error ejecutando rescan para {alert_id}: {type(e).__name__}: {e}')
        await ctx.send(
            f'❌ Error al ejecutar rescan para `{alert_id}`: {e}\n'
            'Revisa los logs del servidor para mas detalles.'
        )


@rescan_command.error
async def rescan_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """Maneja errores del comando rescan"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            '⚠️ Falta el `alert_id`.\nUso: `!rescan <alert_id>`'
        )
    else:
        logger.error(f'Error en comando rescan: {type(error).__name__}: {error}')
        await ctx.send(f'❌ Error inesperado: {error}')


async def start_bot() -> None:
    """
    Inicia el bot de Discord.
    Llamar con asyncio.create_task() desde el lifespan de FastAPI.
    """
    token = settings.discord_bot_token
    if not token:
        logger.warning(
            'DISCORD_BOT_TOKEN no configurado. El bot de Discord no se iniciará.'
        )
        return

    try:
        logger.info('Iniciando bot de Discord...')
        await bot.start(token)
    except discord.LoginFailure:
        logger.error('Token de Discord inválido. Verifica DISCORD_BOT_TOKEN en .env')
    except asyncio.CancelledError:
        logger.info('Bot de Discord detenido.')
    except Exception as e:
        logger.error(f'Error iniciando bot de Discord: {type(e).__name__}: {e}')


async def stop_bot() -> None:
    """Detiene el bot de Discord limpiamente"""
    if not bot.is_closed():
        logger.info('Cerrando conexion del bot de Discord...')
        await bot.close()
