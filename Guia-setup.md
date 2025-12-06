# 🚀 Guía de Configuración SecuBot

## 📋 Pasos para Configurar el Proyecto

### 1. Crear la Estructura de Carpetas

```bash
# Crear todas las carpetas necesarias
mkdir -p app/{api/v1,engines/rule_engine,models,services,db,tasks,utils,schemas}
mkdir -p config tests/{unit,integration} scripts .github/workflows

# Crear archivos __init__.py
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/engines/__init__.py
touch app/engines/rule_engine/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
touch app/db/__init__.py
touch app/tasks/__init__.py
touch app/utils/__init__.py
touch app/schemas/__init__.py
touch config/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

### 2. Copiar Archivos de Configuración

Copia estos archivos en tu proyecto:

- ✅ `pyproject.toml` - Dependencias del proyecto
- ✅ `.env.example` - Template de variables de entorno
- ✅ `.gitignore` - Archivos a ignorar
- ✅ `config/settings.py` - Configuración centralizada
- ✅ `Makefile` - Comandos útiles
- ✅ `README.md` - Documentación
- ✅ `vercel.json` - Configuración de Vercel
- ✅ `pytest.ini` - Configuración de tests
- ✅ `.github/workflows/ci.yml` - CI/CD pipeline
- ✅ `.github/workflows/deploy.yml` - Deploy automático

### 3. Configurar Entorno Virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # macOS/Linux
# o
venv\Scripts\activate     # Windows
```

### 4. Instalar Dependencias

```bash
# Opción 1: Usar Makefile (recomendado)
make setup

# Opción 2: Manual
pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

### 5. Configurar MongoDB

#### Opción A: MongoDB Atlas (Recomendado - FREE)

1. Ir a https://www.mongodb.com/cloud/atlas/register
2. Crear cuenta gratuita
3. Crear cluster M0 (512MB gratis)
4. Configurar acceso:
   - Database Access → Add New Database User
   - Network Access → Add IP Address → Allow Access from Anywhere (0.0.0.0/0)
5. Obtener connection string:
   - Connect → Drivers → Python → Copy connection string
6. Actualizar `.env`:
   ```bash
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=secubot_dev
   ```

#### Opción B: MongoDB Local

```bash
# macOS
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Ubuntu/Debian
sudo apt-get install -y mongodb
sudo systemctl start mongodb

# Verificar
mongosh

# En .env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=secubot_dev
```

### 6. Verificar Configuración

```bash
# Verificar que las dependencias se instalaron
pip list | grep fastapi

# Verificar conexión a MongoDB (crear este script después)
python -c "from pymongo import MongoClient; print(MongoClient('TU_URI').server_info())"
```

### 7. Inicializar Git

```bash
# Inicializar repositorio
git init

# Agregar archivos
git add .

# Primer commit
git commit -m "Initial commit: Project structure and configuration"

# Conectar con GitHub
git remote add origin https://github.com/USERNAME/secubot.git
git branch -M main
git push -u origin main
```

### 8. Configurar GitHub Secrets (para CI/CD)

Ve a tu repositorio en GitHub:

```
Settings → Secrets and variables → Actions → New repository secret
```

Agrega estos secrets:

**Para Tests:**
- `MONGODB_URI_TEST`: URI de MongoDB para tests (puede ser la misma de desarrollo)

**Para Deploy en Vercel (opcional):**
- `VERCEL_TOKEN`: Token de Vercel (obtener en vercel.com/account/tokens)
- `VERCEL_ORG_ID`: ID de tu organización en Vercel
- `VERCEL_PROJECT_ID`: ID del proyecto en Vercel

**Para Notificaciones (opcional):**
- `SLACK_WEBHOOK`: Webhook URL de Slack

### 9. Estructura Final

Tu proyecto debería verse así:

```
secubot/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       └── __init__.py
│   ├── engines/
│   │   ├── __init__.py
│   │   └── rule_engine/
│   │       └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── db/
│   │   └── __init__.py
│   ├── tasks/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── scripts/
├── .env
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
├── pytest.ini
├── README.md
└── vercel.json
```

## ✅ Checklist Final

- [ ] Estructura de carpetas creada
- [ ] Archivos de configuración copiados
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`make setup` o `pip install -e ".[dev]"`)
- [ ] `.env` configurado con MongoDB URI
- [ ] MongoDB configurado (Atlas o local)
- [ ] Repositorio Git inicializado
- [ ] GitHub repository creado
- [ ] GitHub Secrets configurados
- [ ] README.md actualizado con info del proyecto

## 🎯 Próximos Pasos

1. **Crear el entry point**: `app/main.py` con FastAPI básico
2. **Conexión a MongoDB**: `app/db/mongodb.py`
3. **Modelos base**: `app/models/base.py`
4. **Primer endpoint**: `app/api/v1/alerts.py`

¿Listo? Ejecuta:

```bash
make dev
```

Y visita: http://localhost:8000/docs

## 🆘 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'app'"

```bash
# Asegúrate de estar en la raíz del proyecto
pwd

# Reinstala en modo editable
pip install -e .
```

### Error: "Can't connect to MongoDB"

```bash
# Verifica tu URI en .env
cat .env | grep MONGODB_URI

# Prueba la conexión manualmente
python -c "from pymongo import MongoClient; print(MongoClient('TU_URI').server_info())"
```

### Error: "Port 8000 is already in use"

```bash
# Cambia el puerto en .env
echo "PORT=8080" >> .env

# O mata el proceso
lsof -ti:8000 | xargs kill -9  # macOS/Linux
```

### GitHub Actions falla

1. Verifica que los secrets estén configurados
2. Revisa los logs en la pestaña "Actions"
3. Asegúrate que `MONGODB_URI_TEST` esté configurado

## 📚 Recursos

- [MongoDB Atlas Setup](https://www.mongodb.com/docs/atlas/getting-started/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Vercel Deployment](https://vercel.com/docs/concepts/deployments/overview)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)