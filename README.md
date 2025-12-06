# SecuBot 🤖🔒

Sistema de gamificación verificada para DevSecOps que incentiva la remediación de vulnerabilidades mediante puntos, badges y verificación automática.

## 🚀 Quick Start

### Prerrequisitos

- Python 3.10 o superior
- MongoDB Atlas cuenta gratuita (M0 - 512MB) o MongoDB local
- Git

### Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/USERNAME/secubot.git
cd secubot
```

2. **Configurar el proyecto (automático)**
```bash
make setup
```

Este comando:
- Crea el entorno virtual
- Instala todas las dependencias
- Copia `.env.example` a `.env`

3. **Configurar MongoDB**

**Opción A: MongoDB Atlas (Recomendado - Free)**
1. Crear cuenta en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Crear cluster gratuito M0
3. Obtener connection string
4. Actualizar `MONGODB_URI` en `.env`

**Opción B: MongoDB Local**
1. [Instalar MongoDB](https://www.mongodb.com/docs/manual/installation/)
2. Iniciar MongoDB: `mongod`
3. Usar en `.env`: `MONGODB_URI=mongodb://localhost:27017`

4. **Iniciar el servidor**
```bash
make dev
```

5. **Verificar instalación**
```bash
# En otra terminal
curl http://localhost:8000/health
# Respuesta esperada: {"status":"healthy"}
```

6. **Explorar la API**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📦 Estructura del Proyecto

```
secubot/
├── .github/               # GitHub Actions workflows
│   └── workflows/        
│       ├── ci.yml        # Tests, lint, security
│       └── deploy.yml    # Deploy a Vercel
├── app/                  # Código de la aplicación
│   ├── api/             # Endpoints REST
│   ├── engines/         # Motor de Reglas
│   ├── models/          # Modelos de datos
│   ├── services/        # Lógica de negocio
│   ├── db/              # Configuración de BD
│   ├── tasks/           # Tareas programadas
│   └── utils/           # Utilidades
├── config/              # Archivos de configuración
│   ├── rules.yaml      # Reglas de gamificación
│   ├── badges.yaml     # Definición de badges
│   └── settings.py     # Settings centralizados
├── tests/               # Tests
└── scripts/            # Scripts de utilidad
```

## 🛠️ Comandos de Desarrollo

```bash
# Desarrollo
make dev              # Iniciar servidor con hot-reload
make health           # Verificar que el servidor esté corriendo

# Testing
make test             # Ejecutar tests
make test-cov         # Tests con reporte de cobertura
make test-watch       # Tests en modo watch

# Code Quality
make lint             # Ejecutar linter
make lint-fix         # Auto-corregir errores de lint
make format           # Formatear código
make format-check     # Verificar formato sin modificar
make type-check       # Verificar tipos con mypy
make check            # Ejecutar TODAS las verificaciones (CI local)

# Base de Datos
make seed-db          # Cargar datos de prueba
make reset-db         # Resetear BD (¡CUIDADO!)

# Utilidades
make clean            # Limpiar archivos temporales
make deps-update      # Actualizar dependencias
make deps-list        # Listar dependencias
```

## 🔧 Configuración

### Variables de Entorno Principales

```bash
# Base de Datos (¡IMPORTANTE!)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DATABASE_NAME=secubot_dev

# Aplicación
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Gamificación
RESCAN_DELAY_SECONDS=300
RESCAN_TIMEOUT_HOURS=72
ENABLE_SPEED_BONUS=true
```

Ver `.env.example` para la lista completa.

## 📖 Documentación de la API

Una vez iniciado el servidor:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🧪 Testing

```bash
# Ejecutar todos los tests
make test

# Tests con cobertura
make test-cov

# Ver reporte HTML
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html # Windows

# Tests en modo watch (re-ejecuta al guardar)
make test-watch
```

## 🚀 CI/CD con GitHub Actions

El proyecto incluye workflows automáticos:

### CI (`.github/workflows/ci.yml`)
Se ejecuta en cada push y PR:
- ✅ Lint con Ruff
- ✅ Type checking con MyPy
- ✅ Tests en Python 3.10, 3.11, 3.12
- ✅ Cobertura de código
- ✅ Security scan (Safety + Bandit)

### Deploy (`.github/workflows/deploy.yml`)
Se ejecuta en push a `main`:
- 🚀 Deploy automático a Vercel
- 📢 Notificación a Slack (opcional)

### Configurar GitHub Secrets

Para que los workflows funcionen, configura estos secrets en tu repo:

```
Settings → Secrets and variables → Actions → New repository secret
```

**Requeridos para tests:**
- `MONGODB_URI_TEST`: URI de MongoDB para tests

**Requeridos para deploy:**
- `VERCEL_TOKEN`: Token de Vercel
- `VERCEL_ORG_ID`: Organization ID
- `VERCEL_PROJECT_ID`: Project ID

**Opcionales:**
- `SLACK_WEBHOOK`: Para notificaciones

## 📊 Arquitectura

### Componentes Principales

1. **Motor de Reglas (RuleEngine)**: Evalúa condiciones y ejecuta acciones
2. **API REST**: Interfaz de comunicación (FastAPI)
3. **Task Scheduler**: Tareas programadas (APScheduler)
4. **MongoDB**: Base de datos NoSQL

### Flujos Principales

1. **Remediación Verificada**: Alert → Remediation → Rescan → Puntos
2. **Alerta Reaparece**: Detección de reapertura → Penalización
3. **Otorgamiento de Badges**: Evaluación de criterios → Award

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Ejecuta `make check` para verificar que todo esté bien
4. Commit (`git commit -m 'Add some AmazingFeature'`)
5. Push (`git push origin feature/AmazingFeature`)
6. Abre un Pull Request

## 📝 Reglas de Desarrollo

- ✅ Usar `ruff` para linting y formateo
- ✅ Ejecutar `make check` antes de cada commit
- ✅ Escribir tests para nuevas features
- ✅ Mantener cobertura > 80%
- ✅ Documentar endpoints con docstrings
- ✅ Usar type hints en todo el código

## 🆘 Troubleshooting

### MongoDB no conecta

```bash
# Verificar URI en .env
cat .env | grep MONGODB_URI

# Verificar conexión
python -c "from pymongo import MongoClient; print(MongoClient('TU_URI').server_info())"
```

### Tests fallan por falta de MongoDB

```bash
# Configurar MONGODB_URI_TEST en .env o como variable de entorno
export MONGODB_URI_TEST="mongodb://localhost:27017"
make test
```

### Puerto 8000 ya en uso

```bash
# Opción 1: Cambiar puerto en .env
PORT=8080

# Opción 2: Matar proceso
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows (luego taskkill /PID xxx /F)
```

### Dependencias no se instalan

```bash
# Limpiar e instalar desde cero
make clean
python -m pip install --upgrade pip
make install-dev
```

## 📚 Recursos Adicionales

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Motor (MongoDB async)](https://motor.readthedocs.io/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [Vercel Deployment](https://vercel.com/docs)

## 📄 Licencia

Este proyecto es parte de un trabajo académico de la Universidad de Antioquia.

## 👥 Autores

- Camilo Aguirre - bcamilo.aguirre@udea.edu.co

---

⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!