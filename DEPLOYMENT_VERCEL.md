# 🚀 Despliegue en Vercel - SecuBot

## Configuración lista

✅ `vercel.json` - Configuración de Vercel
✅ `requirements-vercel.txt` - Dependencias optimizadas (9 paquetes vs 196)
✅ `.vercelignore` - Archivos a excluir del build

---

## 📦 Pasos para desplegar

### Opción 1: Desde Vercel Dashboard (Recomendado)

1. Ve a [vercel.com](https://vercel.com)
2. Haz login con GitHub
3. Click "Add New Project"
4. Selecciona el repositorio `SecuBot`
5. Vercel detectará automáticamente `vercel.json`
6. Configura las variables de entorno (ver abajo)
7. Click "Deploy"

### Opción 2: Vercel CLI

```bash
npm install -g vercel
vercel login
vercel
```

---

## 🔐 Variables de entorno requeridas

En Vercel Dashboard → Settings → Environment Variables:

```env
MONGODB_URI=mongodb+srv://...
DATABASE_NAME=secubot_prod
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_NOTIFICATIONS_ENABLED=true
APP_NAME=SecuBot
ENVIRONMENT=production
SECRET_KEY=<generar-clave-segura>
```

---

## ⚠️ Limitaciones en Vercel

**Funciona:**
- ✅ API REST completa
- ✅ Webhooks
- ✅ Notificaciones Slack
- ✅ MongoDB Atlas

**NO funciona:**
- ❌ Tareas programadas (APScheduler)
- ❌ Background workers
- ❌ WebSockets persistentes

**Alternativa:** Railway, Render o Fly.io para funcionalidad completa

---

## 🧪 Verificar despliegue

```bash
curl https://tu-app.vercel.app/health
```

Docs: `https://tu-app.vercel.app/docs`
