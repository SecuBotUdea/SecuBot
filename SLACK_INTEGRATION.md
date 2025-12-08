# 🚀 Guía de Integración con Slack - SecuBot

## 📋 Resumen

SecuBot ahora puede enviar notificaciones automáticas a Slack cuando ocurren eventos importantes:

- 🚨 **Nuevas alertas** de seguridad detectadas
- ✅ **Remediaciones verificadas** exitosamente
- ❌ **Remediaciones fallidas** (vulnerabilidad persiste)
- 🔄 **Alertas reabiertas** (regresiones)

---

## 🔧 Configuración Inicial

### 1. Crear Incoming Webhook en Slack

1. Ve a https://api.slack.com/messaging/webhooks
2. Click en **"Create your Slack app"**
3. Selecciona **"From scratch"**
4. Nombre: `SecuBot`
5. Workspace: Tu workspace
6. En la sidebar, ve a **"Incoming Webhooks"**
7. Activa **"Activate Incoming Webhooks"**
8. Click en **"Add New Webhook to Workspace"**
9. Selecciona el canal (ej: `#security-alerts`)
10. **Copia la Webhook URL** (se ve así: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`)

### 2. Configurar .env

Actualiza tu archivo `.env`:

```bash
# Slack Integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TU_WEBHOOK_AQUI
SLACK_NOTIFICATIONS_ENABLED=true
```

**IMPORTANTE:** Cambia `SLACK_NOTIFICATIONS_ENABLED` a `true` para activar las notificaciones.

---

## 🏃 Iniciar el Servidor

```bash
# Activar entorno virtual
.\venv\Scripts\activate

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Deberías ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

---

## 🧪 Probar la Integración

### Opción 1: Swagger UI (Recomendado)

1. Ve a http://localhost:8000/docs
2. Verás 5 endpoints de prueba en la sección **"Notifications"**

#### **Test Simple**
1. Expande `POST /api/v1/notifications/test`
2. Click en **"Try it out"**
3. Edita el JSON:
   ```json
   {
     "message": "Hola desde SecuBot!"
   }
   ```
4. Click en **"Execute"**
5. Revisa tu canal de Slack - deberías ver: `🧪 Test: Hola desde SecuBot!`

#### **Test Alerta de Seguridad**
1. Expande `POST /api/v1/notifications/test-alert`
2. Click en **"Try it out"**
3. Edita el JSON:
   ```json
   {
     "severity": "CRITICAL",
     "component": "authentication-service",
     "alert_id": "test-001"
   }
   ```
4. Click en **"Execute"**
5. Verás en Slack un mensaje formateado con:
   - 🔴 Nueva Alerta de Seguridad
   - Severidad: CRITICAL
   - Componente: authentication-service
   - Color rojo en el borde

#### **Test Remediación Verificada**
1. Expande `POST /api/v1/notifications/test-remediation-verified`
2. Click en **"Try it out"** → **"Execute"**
3. Verás en Slack:
   - ✅ Remediación Verificada
   - +100 puntos 🎯
   - Celebración de trabajo bien hecho

#### **Test Remediación Fallida**
1. Expande `POST /api/v1/notifications/test-remediation-failed`
2. Click en **"Try it out"** → **"Execute"**
3. Verás en Slack:
   - ❌ Remediación No Verificada
   - -25 puntos de penalización
   - Consejo para siguiente paso

#### **Test Alerta Reabierta**
1. Expande `POST /api/v1/notifications/test-alert-reopened`
2. Click en **"Try it out"** → **"Execute"**
3. Verás en Slack:
   - 🔄 Alerta Reabierta
   - Contador de reaperturas
   - Advertencia sobre posible regresión

---

### Opción 2: cURL (Terminal)

```bash
# Test simple
curl -X POST http://localhost:8000/api/v1/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test desde cURL"}'

# Test alerta
curl -X POST http://localhost:8000/api/v1/notifications/test-alert \
  -H "Content-Type: application/json" \
  -d '{"severity": "HIGH", "component": "api-gateway", "alert_id": "test-002"}'

# Test remediación verificada
curl -X POST http://localhost:8000/api/v1/notifications/test-remediation-verified

# Test remediación fallida
curl -X POST http://localhost:8000/api/v1/notifications/test-remediation-failed

# Test alerta reabierta
curl -X POST http://localhost:8000/api/v1/notifications/test-alert-reopened
```

---

## 📊 Ejemplo de Mensajes en Slack

### Alerta CRITICAL
```
🔴 Nueva Alerta de Seguridad
━━━━━━━━━━━━━━━━━━━━━━━━━

Severidad: CRITICAL      Componente: users-service
Estado: Open             Calidad: High

Detectada: Dec 7, 2025 at 3:45 PM

Descripción:
SQL Injection vulnerability detected in authentication endpoint

Alert ID: `alert-12345`
Signature: `abc123def456...`
```

### Remediación Verificada
```
✅ Remediación Verificada
━━━━━━━━━━━━━━━━━━━━━━━━━

La vulnerabilidad CRITICAL en `authentication-service` ha sido verificada como resuelta.

Puntos Ganados: +100 🎯    Severidad: 🔴 CRITICAL
Usuario: @jose.cruz

🎉 Excelente trabajo en seguridad del código!
```

---

## 🔍 Troubleshooting

### ❌ Error: "Failed to send notification"

**Posibles causas:**

1. **Webhook URL incorrecta**
   - Verifica que la URL en `.env` sea correcta
   - No debe tener espacios al inicio/final
   - Debe empezar con `https://hooks.slack.com/services/`

2. **Notificaciones deshabilitadas**
   - Verifica: `SLACK_NOTIFICATIONS_ENABLED=true` en `.env`
   - Reinicia el servidor después de cambiar

3. **Problema de red**
   - Verifica conexión a internet
   - Prueba la URL directamente:
     ```bash
     curl -X POST TU_WEBHOOK_URL \
       -H 'Content-Type: application/json' \
       -d '{"text": "Test directo"}'
     ```

4. **Webhook revocado**
   - Si cambiaste algo en Slack, el webhook puede haberse invalidado
   - Crea uno nuevo y actualiza `.env`

---

## 📝 Logs

Los logs te ayudan a debuggear:

```bash
# Logs de éxito
2025-12-07 15:30:45 - slack_client - INFO - Slack message sent successfully
2025-12-07 15:30:46 - notification_service - INFO - Notification sent for new alert: test-001

# Logs de error
2025-12-07 15:31:20 - slack_client - ERROR - Failed to send Slack message: 404 - Not Found
2025-12-07 15:31:21 - notification_service - WARNING - Failed to send notification for alert: test-002
```

---

## 🎯 Próximos Pasos

Una vez que la integración funcione, puedes:

1. **Integrar con el flujo real de alertas**
   - Cuando `alert_service.py` cree una alerta, llamar:
     ```python
     await notification_service.notify_new_alert(alert)
     ```

2. **Integrar con remediaciones**
   - Después de verificar con rescan:
     ```python
     if rescan_result.present == False:
         await notification_service.notify_remediation_verified(alert, remediation, points)
     else:
         await notification_service.notify_remediation_failed(alert, remediation, penalty)
     ```

3. **Personalizar mensajes**
   - Edita `message_builder.py` para ajustar formato, colores, emojis

4. **Agregar más tipos de notificaciones**
   - Badges ganados
   - Leaderboard semanal
   - Alertas timeout

---

## 📚 Recursos

- **Slack Block Kit Builder:** https://app.slack.com/block-kit-builder
- **Slack API Docs:** https://api.slack.com/messaging/webhooks
- **FastAPI Docs:** https://fastapi.tiangolo.com/

---

## ✅ Checklist

- [ ] Webhook creado en Slack
- [ ] `.env` actualizado con webhook URL
- [ ] `SLACK_NOTIFICATIONS_ENABLED=true` en `.env`
- [ ] Servidor iniciado (`uvicorn app.main:app --reload`)
- [ ] Test simple funcionando
- [ ] Test alerta funcionando
- [ ] Test remediación funcionando
- [ ] Mensajes llegando al canal correcto de Slack

---

**¿Problemas?** Revisa los logs en la consola del servidor y verifica la configuración del .env.

**¡Listo!** 🎉 La integración con Slack está funcionando.
