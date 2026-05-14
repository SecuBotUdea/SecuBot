"""
Discord Bot - Recibe el comando !rescan desde Discord y ejecuta el re-escaneo

Comandos disponibles:
    !rescan <alert_id>  - Verifica si una vulnerabilidad sigue presente
"""

import asyncio

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
async def rescan_command(
    ctx: commands.Context, alert_id: str | None = None, user_id: str | None = None
) -> None:
    """
    Ejecuta el flujo completo de re-verificación para una alerta (incluye gamificación).

    Uso: !rescan <alert_id> [user_id]

    Ejemplos:
      !rescan alert_abc123
      !rescan alert_abc123 user-dev-001
    """
    if not alert_id:
        await ctx.send(
            '⚠️ Debes proporcionar un `alert_id`.\n'
            'Uso: `!rescan <alert_id> [user_id]`\n'
            'Ejemplo: `!rescan alert_abc123 user-dev-001`'
        )
        return

    # Lazy import para evitar dependencias circulares en tiempo de importación
    from app.services.alert_service import get_alert_service
    from app.services.remediation_service import get_remediation_service
    from app.services.user_service import get_user_service

    await ctx.send(f'🔍 Ejecutando rescan para `{alert_id}`...')

    try:
        # 1. Verificar que la alerta existe en MongoDB
        alert_service = get_alert_service()
        alert_data = await alert_service.get_alert(alert_id)

        if not alert_data:
            await ctx.send(f'❌ Alerta `{alert_id}` no encontrada en la base de datos.')
            return

        alert_status = alert_data.get('status')
        if alert_status == 'pending_verification':
            await ctx.send(
                f'⏳ La alerta `{alert_id}` ya tiene un rescan en curso. '
                'Espera a que termine antes de lanzar otro.'
            )
            return
        if alert_status not in ('open', 'reopened', 'verified_persists'):
            await ctx.send(
                f'⚠️ La alerta `{alert_id}` tiene status `{alert_status}` y no puede ser rescaneada.'
            )
            return

        remediation_service = get_remediation_service()

        # 2. Validar user_id si fue proporcionado
        effective_user_id = f'discord:{ctx.author.id}'
        if user_id:
            user_service = get_user_service()
            user_data = await user_service.get_user_by_user_id(user_id)
            if not user_data:
                await ctx.send(
                    f'⚠️ El usuario `{user_id}` no existe en SecuBot. '
                    'Verifica el ID con `GET /api/v1/users/`.'
                )
                return
            effective_user_id = user_id

        # 3. Adquirir lock atómico para evitar rescans simultáneos
        lock_acquired = await alert_service.acquire_rescan_lock(
            alert_id=alert_id,
            locked_by=effective_user_id,
        )
        if not lock_acquired:
            await ctx.send(
                f'⏳ Otro rescan para `{alert_id}` ya está en ejecución. '
                'Intenta de nuevo en unos minutos.'
            )
            return

        try:
            # 4. Buscar remediación pendiente; si no existe, crear una desde Discord
            remediations = await remediation_service.get_remediations_by_alert(alert_id)
            pending = next((r for r in remediations if r['status'] == 'pending'), None)

            if not pending:
                new_rem = await remediation_service.create_remediation(
                    alert_id=alert_id,
                    user_id=effective_user_id,
                    remediation_type='user_mark',
                    notes=f'Rescan solicitado desde Discord por {ctx.author.display_name}',
                    auto_trigger_rescan=False,
                )
                pending = new_rem

            # 5. Ejecutar rescan completo: normalizer + gamificación + notificación Discord
            gamification_result = await remediation_service.trigger_rescan_for_remediation(
                remediation_id=pending['remediation_id']
            )

            # 6. Leer remediación actualizada para conocer el veredicto final
            updated = await remediation_service.get_remediation(pending['remediation_id'])
            still_exists = updated['status'] == 'failed_verification'

            points_awarded = sum(
                p.get('points', 0) for p in gamification_result.get('points_awarded', [])
            )
            penalties = abs(
                sum(p.get('points', 0) for p in gamification_result.get('penalties_applied', []))
            )

            if still_exists:
                await ctx.send(
                    f'🔴 **Vulnerabilidad persiste** en `{alert_id}`.\n'
                    f'Penalización: `{penalties}` puntos. '
                    'Revisa el canal de notificaciones para el detalle completo.'
                )
            else:
                await ctx.send(
                    f'✅ **Vulnerabilidad resuelta** en `{alert_id}`.\n'
                    f'Puntos ganados: `+{points_awarded}`. '
                    'Revisa el canal de notificaciones para el detalle completo.'
                )

        finally:
            await alert_service.release_rescan_lock(alert_id)

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
        await ctx.send('⚠️ Falta el `alert_id`.\nUso: `!rescan <alert_id>`')
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
        logger.warning('DISCORD_BOT_TOKEN no configurado. El bot de Discord no se iniciará.')
        return

    try:
        logger.info('Iniciando bot de Discord...')
        await bot.start(token)
    except discord.LoginFailure:
        logger.error('Token de Discord inválido. Verifica DISCORD_BOT_TOKEN en .env')
    except discord.PrivilegedIntentsRequired:
        logger.warning(
            'El bot de Discord requiere el "Message Content Intent" que no está habilitado. '
            'Para habilitarlo: Discord Developer Portal → tu aplicación → Bot → '
            'Privileged Gateway Intents → activa "MESSAGE CONTENT INTENT". '
            'El bot estará inactivo hasta que se habilite el intent.'
        )
    except asyncio.CancelledError:
        logger.info('Bot de Discord detenido.')
    except Exception as e:
        logger.error(f'Error iniciando bot de Discord: {type(e).__name__}: {e}')


async def stop_bot() -> None:
    """Detiene el bot de Discord limpiamente"""
    if not bot.is_closed():
        logger.info('Cerrando conexion del bot de Discord...')
        await bot.close()
