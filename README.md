# 🦺 Sistema de Reporte Diario de Mantenimiento & RACS

> Digitalización del reporte diario de mantenimiento minero y Reporte de Actos y Condiciones Subestándar (RACS) — Formato P-SSO-09.F1 V2.

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Capturas de Pantalla](#-capturas-de-pantalla)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación Local](#-instalación-local)
- [Configuración](#-configuración)
- [Despliegue en Render](#-despliegue-en-render)
- [API Endpoints](#-api-endpoints)
- [Módulo RACS](#-módulo-racs)
- [Administración](#-administración)
- [Roadmap](#-roadmap)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)

---

## 📖 Descripción General

Sistema web diseñado para **reemplazar los reportes en papel** en la Unidad Minera Soledad (Inversiones Prosol). Permite:

- **📝 Reporte diario de mantenimiento** con checklist de equipos, personal, horas trabajadas, producción y acciones correctivas
- **🦺 RACS (Reporte de Actos y Condiciones Subestándar)** conforme al formato P-SSO-09.F1 V2, con checklist visual de 42 ítems
- **📊 Dashboards profesionales** con KPIs, OKRs, gráficos de distribución, tendencias y rendimiento por trabajador
- **📱 Integración WhatsApp** — apertura automática del mensaje completo al enviar un reporte
- **📥 Exportación Excel** — individual por reporte y base de datos completa descargable
- **⚙️ Administración** — gestión dinámica de personal, grupos, guardias A/B/C con ciclo 20×10

### Beneficios

| Antes (papel) | Ahora (digital) |
|--------------|----------------|
| Reportes se perdían o deterioraban | Todo guardado en base de datos |
| Sin visibilidad de cumplimiento | Dashboard con KPIs en tiempo real |
| Difícil consolidar datos | Excel descargable con 1 clic |
| Sin control de quienes reportan | Seguimiento por trabajador y guardia |
| Comunicación lenta | WhatsApp automático al enviar |

---

## 📸 Capturas de Pantalla

| Pantalla | Vista |
|----------|-------|
| **Formulario RACS** | Formulario visual tipo P-SSO-09 con header corporativo, datos generales, categoría, turno, nivel dinámico, checklist 42 ítems, selección de riesgo (Alto/Medio/Bajo) |
| **Dashboard RACS** | KPIs (Total, Cumplimiento %, Riesgo Alto, Trabajadores activos), gráficos de distribución, OKRs con anillos de progreso, rendimiento por trabajador |
| **Admin — Personal** | Gestión de trabajadores: agregar, editar nombre/grupo/cargo/guardia, visualización dinámica de ciclos de guardia |
| **Dashboard General** | KPIs de producción, disponibilidad de equipos, asistencia, tendencias |

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| **Backend** | Python 3.11+ · FastAPI · SQLAlchemy 2.0 |
| **Frontend** | HTML5 · CSS3 · JavaScript · Bootstrap 5 · Bootstrap Icons |
| **Base de Datos** | PostgreSQL (producción) · SQLite (desarrollo local) |
| **Templating** | Jinja2 (server-side rendering) |
| **Exportación** | OpenPyXL (Excel .xlsx) |
| **Imágenes** | Pillow |
| **Autenticación** | JWT · Passlib (bcrypt) |
| **Monitoreo** | Sentry · Logging estructurado |
| **Hosting** | Render (cloud) — SSL incluido |
| **CI/CD** | GitHub Actions |
| **Control de Versiones** | Git · GitHub |

---

## 📁 Estructura del Proyecto

```
📂 proyecto/
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── 📂 core/               # Configuración, DB, seguridad
│   │   │   ├── __init__.py
│   │   │   ├── config.py          # Settings (pydantic-settings)
│   │   │   ├── database.py        # Engine, sesión, Base
│   │   │   └── security.py        # JWT, password hashing
│   │   ├── 📂 routers/            # Endpoints por módulo
│   │   │   ├── __init__.py
│   │   │   ├── reportes.py        # CRUD reportes, imágenes, export
│   │   │   ├── dashboard.py       # KPIs, stats, OKRs
│   │   │   ├── admin.py           # Admin CRUD config entities
│   │   │   ├── racs.py            # RACS: form, workers, dashboard, excel
│   │   │   └── guardias.py        # Guardia phases, worker assignments
│   │   ├── 📂 services/           # Lógica de negocio
│   │   │   ├── __init__.py
│   │   │   └── racs_service.py    # Períodos, guardias, workers
│   │   ├── 📂 repositories/       # Consultas DB (futuro)
│   │   │   └── __init__.py
│   │   ├── 📂 schemas/            # Schemas Pydantic
│   │   │   └── __init__.py
│   │   ├── 📂 templates/          # Plantillas HTML (Jinja2)
│   │   │   ├── index.html
│   │   │   ├── dashboard.html
│   │   │   ├── racs_form.html
│   │   │   ├── racs_dashboard.html
│   │   │   └── admin.html
│   │   ├── main.py                # Punto de entrada (~160 líneas)
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # (redirige a schemas/__init__.py)
│   │   ├── config.py              # (redirige a core/config.py)
│   │   ├── database.py            # (redirige a core/database.py)
│   │   ├── daily_report.py
│   │   └── excel_export.py
│   ├── run.py                     # Iniciar servidor local
│   ├── start.py                   # Iniciar sin reload
│   └── mantenimiento.db           # SQLite (dev)
├── 📂 static/
│   ├── 📂 css/
│   │   └── style.css
│   ├── 📂 js/
│   │   ├── app.js
│   │   ├── dashboard.js
│   │   ├── admin.js
│   │   └── racs.js
│   ├── favicon.ico
│   ├── favicon.png
│   └── favicon-192.png
├── requirements.txt
├── config_seed.json               # Seed data versionada
├── render.yaml                    # Config Render
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI/CD pipeline
└── README.md
```

---

## 🚀 Instalación Local

### Requisitos

- Python 3.11 o superior
- Git
- (Opcional) PostgreSQL para pruebas en producción

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/CesarFarfan07/Formulario-Mantenimiento.git
cd Formulario-Mantenimiento

# 2. Crear entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor (con recarga automática)
python backend/run.py

# 5. Abrir en el navegador
# http://localhost:8000
```

### Credenciales por defecto

| Rol | Usuario | Contraseña |
|-----|---------|-----------|
| Admin | — | `Mantt.1` |
| DNI eliminación | — | `70212352` |

> ⚠️ **IMPORTANTE**: Cambiar estas credenciales en producción mediante variables de entorno.

---

## ⚙️ Configuración

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de datos (default: SQLite)
DATABASE_URL=sqlite:///./backend/mantenimiento.db

# Para PostgreSQL en producción:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# Seguridad
SECRET_KEY=mi-clave-secreta-cambiame
ADMIN_PASSWORD=Mantt.1
ADMIN_DNI=70212352

# Monitoreo (opcional)
SENTRY_DSN=https://xxx@sentry.io/xxx
ENVIRONMENT=production

# Upload
MAX_IMAGE_SIZE_MB=10
```

### Seed Data

La aplicación se siembra automáticamente con datos por defecto (turnos, niveles, macroprocesos, equipos, etc.) la primera vez que se ejecuta con la base de datos vacía.

Para personalizar, editar `config_seed.json` en la raíz del proyecto.

---

## ☁️ Despliegue en Render

El proyecto incluye `render.yaml` para despliegue automatizado en Render.

1. Conectar repositorio de GitHub a Render
2. Seleccionar "Blueprint" (usa `render.yaml`)
3. Render configura automáticamente:
   - Servicio Web (FastAPI + Uvicorn)
   - Base de datos PostgreSQL
   - Variables de entorno
   - SSL automatizado
   - Auto-deploy desde GitHub

**URL de producción:** `https://formulario-mantenimiento-ybv4.onrender.com`

---

## 🔌 API Endpoints

### Reportes Diarios

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Página principal del formulario |
| `GET` | `/dashboard` | Dashboard general |
| `POST` | `/reports` | Crear reporte diario |
| `GET` | `/reports` | Listar reportes (paginado) |
| `GET` | `/reports/{id}` | Obtener reporte por ID |
| `DELETE` | `/reports/{id}` | Eliminar reporte (protegido) |
| `GET` | `/reports/export` | Exportar Excel |
| `GET` | `/reports/export-csv` | Exportar CSV |
| `GET` | `/reports/dates` | Fechas con reportes |
| `GET` | `/reports/daily/{date}` | Reporte diario PDF |
| `POST` | `/upload-image/{entry_id}` | Subir imagen a entrada |
| `DELETE` | `/image/{id}` | Eliminar imagen |
| `GET` | `/options/all` | Todas las opciones del formulario |
| `GET` | `/api/equipment/last-reading/{name}` | Última lectura de equipo |

### Dashboard

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/dashboard/summary` | KPIs del período |
| `GET` | `/api/dashboard/kpi-detail` | Detalle de KPI específico |

### RACS

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/racs` | Formulario RACS |
| `GET` | `/racs/dashboard` | Dashboard RACS |
| `GET` | `/api/racs/period` | Período RACS actual |
| `GET` | `/api/racs/workers` | Trabajadores con estado de guardia |
| `POST` | `/api/racs` | Crear reporte RACS |
| `GET` | `/api/racs/list` | Listar RACS del período |
| `GET` | `/api/racs/dashboard-data` | Datos de cumplimiento |
| `GET` | `/api/racs/dashboard-kpi` | KPIs detallados |
| `GET` | `/api/racs/{id}/excel` | Descargar Excel individual |
| `GET` | `/api/racs/database-excel` | Descargar base de datos completa |
| `POST` | `/api/racs/workers/create` | Crear trabajador RACS |
| `PUT` | `/api/racs/workers/{id}` | Actualizar trabajador |
| `DELETE` | `/api/racs/workers/{id}` | Desactivar trabajador |
| `GET` | `/api/racs/groups` | Grupos disponibles |

### Admin

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/admin` | Página de administración |
| `POST` | `/api/admin/verify` | Verificar contraseña admin |
| `GET` | `/api/admin/list` | Listar entidad de configuración |
| `POST` | `/api/admin/create` | Crear registro |
| `PUT` | `/api/admin/update` | Actualizar registro |
| `DELETE` | `/api/admin/delete` | Eliminar registro |

### Guardias

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/guardias` | Listar guardias con trabajadores |
| `POST` | `/api/guardias/update` | Actualizar fase o asignación |

### Salud

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check del sistema |

---

## 🦺 Módulo RACS

### Período Semanal

- **Inicio:** Domingo 20:00 horas
- **Fin:** Domingo siguiente 18:00 horas
- **Mínimo:** 2 reportes por trabajador por semana

### Guardias (Ciclo 20×10)

- **Guardia A:** 20 días en unidad + 10 días de descanso
- **Guardia B:** Desfasada 10 días de A
- **Guardia C:** Desfasada 20 días de A
- El ciclo se calcula automáticamente según la fecha de inicio configurada

### Formulario P-SSO-09.F1 V2

El formulario de RACS sigue el formato oficial de la plantilla P-SSO-09.F1 V2:

- ✅ Header con código, versión y página
- ✅ Datos generales del reporte
- ✅ Categoría (Seguridad / Medio Ambiente)
- ✅ Tipo (Acto / Condición Subestándar)
- ✅ Turno (Día / Noche)
- ✅ Nivel dinámico (desde configuración del admin)
- ✅ Checklist de 42 ítems (single-select)
- ✅ Riesgo (Alto / Medio / Bajo) con indicador visual
- ✅ Referencia obligatoria
- ✅ Descripción obligatoria
- ✅ Acción correctiva obligatoria
- ✅ Foto opcional
- ✅ WhatsApp automático al enviar

---

## ⚙️ Administración

Acceso protegido con contraseña (`/admin`). Funcionalidades:

- **Gestión de Personal RACS**: Agregar, editar y desactivar trabajadores
- **Grupos dinámicos**: Los grupos se obtienen de la base de datos
- **Guardias A/B/C**: Configuración de fechas de inicio, visualización dinámica del estado (en unidad / descanso)
- **Cargos**: Asignación de cargo por trabajador
- **Configuración**: CRUD de turnos, niveles, macroprocesos, equipos, etc.
- **Protección**: Eliminación protegida por DNI del administrador

---

## 🗺️ Roadmap

### Fase 1 — Refactor (✔ Completado)
- [x] Separar `main.py` en routers, services y core
- [x] Migrar config/database a `core/`
- [x] Schemas Pydantic en paquete propio
- [x] Logging estructurado

### Fase 2 — Próximos
- [ ] Autenticación JWT con roles (Admin / Supervisor / Usuario)
- [ ] Tests automatizados con pytest (>80% coverage)
- [ ] README profesional y documentación de API

### Fase 3 — Frontend
- [ ] Migrar a React + TypeScript + Tailwind CSS
- [ ] Dashboard interactivo con WebSockets
- [ ] Notificaciones en tiempo real
- [ ] PWA — modo offline

### Fase 4 — DevOps
- [ ] Docker + Docker Compose
- [ ] CI/CD con GitHub Actions (✔ Completado)
- [ ] Monitoreo con Sentry (✔ Integrado)
- [ ] Backups automáticos diarios
- [ ] Reportes PDF automáticos por email

### Fase 5 — Avanzado
- [ ] Gamificación (medallas, ranking, rachas)
- [ ] App móvil (PWA)
- [ ] Asistente IA para análisis de datos
- [ ] BI Analytics — exportación a Power BI

---

## 🤝 Contribuir

1. Hacer fork del repositorio
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Hacer cambios y commits
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

### Convenciones

- Commits en español, imperativo: "Agrega autenticación JWT"
- Usar Ruff para linting de Python
- Mantener las rutas de API con prefijo `/api/`
- Documentar endpoints nuevos en esta misma sección

---

## 📄 Licencia

**Uso interno — Inversiones Prosol S.A.C.**

Desarrollado por Cesar Farfan para la Unidad Minera Soledad.

---

<p align="center">
  <strong>Inversiones Prosol</strong> · Unidad Minera Soledad<br>
  <sub>Versión 2.0.0 — Julio 2026</sub>
</p>
