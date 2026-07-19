"""Application entry point — configures FastAPI and mounts all routers."""
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .core.database import engine, SessionLocal, Base
from .core.config import settings, BASE_DIR

# ─── Create all tables ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─── Seed data (only if tables empty) ───────────────────────────────
def _seed_hardcoded():
    from .models import Turno, Nivel, Macroprocess, WorkType, Action, Collaborator, EquipmentCategory, EquipmentSubitem
    db = SessionLocal()
    try:
        if db.query(Turno).count() > 0:
            return
        for i, t in enumerate(["Día", "Noche"]):
            db.add(Turno(name=t, position=i))
        for i, n in enumerate(["Nivel 05","Nivel 04","Nivel 03","Nivel 02","Nivel 01","Nivel 0","Nivel -01","Nivel -02","Nivel -03","Nivel -04","Nivel -05","Campamento","PTAR"]):
            db.add(Nivel(name=n, position=i))
        for i, m in enumerate(["Perforación", "Voladura", "Carguío", "Transporte", "Chancado", "Mantenimiento", "Servicios Auxiliares", "Seguridad", "Medio Ambiente"]):
            db.add(Macroprocess(name=m, position=i))
        for i, wt in enumerate(["Correctivo", "Preventivo", "Predictivo", "Mejora"]):
            db.add(WorkType(name=wt, position=i))
        for i, a in enumerate(["Reparar", "Inspeccionar", "Lubricar", "Cambiar", "Ajustar", "Limpiar", "Soldar", "Probar", "Calibrar", "Instalar", "Desmontar", "Montar", "Reportar", "Solicitar", "Otro"]):
            db.add(Action(name=a, position=i))
        for i, c in enumerate(["MECANICO A", "MECANICO B", "MECANICO C", "MECANICO D", "SOLDADOR", "ELECTRICISTA", "AYUDANTE", "OPERADOR", "SUPERVISOR", "INGENIERO", "JEFE DE GUARDIA", "OTRO"]):
            db.add(Collaborator(name=c, position=i))
        equipos_data = [
            ("JUMBO", ["JUMBO DD311", "JUMBO DD210", "JUMBO DD320"]),
            ("SIMBA", ["SIMBA S7", "SIMBA ST"]),
            ("BOLTER", ["BOLTER B32"]),
            ("ROBOLT", ["ROBOLT RC60"]),
            ("SCALER", ["SCALER"]),
            ("CARGADOR DE ANFO", ["CARGADOR DE ANFO"]),
            ("LOCOMOTORA", ["LOCOMOTORA 3TN", "LOCOMOTORA 6TN", "LOCOMOTORA 12TN"]),
            ("CARRIL MINERO", ["CARROS MINEROS 4M3", "CARROS MINEROS 6M3"]),
            ("CAMION BAJO PERFIL", ["CAMION BAJO PERFIL 20TN", "CAMION BAJO PERFIL 30TN", "CAMION BAJO PERFIL 40TN"]),
            ("CAMIONETA", ["CAMIONETA 4X4"]),
            ("VOLQUETE", ["VOLQUETE 8M3"]),
            ("SCOOP", ["SCOOP 2.2YD", "SCOOP 4.2YD", "SCOOP 6.2YD"]),
            ("COMPRESORA", ["COMPRESORA PORTATIL"]),
            ("VENTILADOR", ["VENTILADOR PRINCIPAL", "VENTILADOR SECUNDARIO"]),
            ("ELECTROBOMBA", ["ELECTROBOMBA SUMERGIBLE"]),
            ("GENERADOR", ["GENERADOR ELECTRICO"]),
            ("TRANSFORMADOR", ["TRANSFORMADOR SECO", "TRANSFORMADOR ACEITE"]),
            ("CABINA DE SOLDAR", ["CABINA DE SOLDAR"]),
            ("CAMION GRUA", ["CAMION GRUA"]),
            ("CAMION LUBRICADOR", ["CAMION LUBRICADOR"]),
            ("CAMION COMBUSTIBLE", ["CAMION COMBUSTIBLE"]),
            ("CAMION AGUA", ["CAMION AGUA"]),
            ("CAMION CAMILLA", ["CAMION CAMILLA"]),
            ("CAMION PERSONAL", ["CAMION PERSONAL"]),
            ("OTROS", ["OTROS"]),
        ]
        for pos, (cat, subs) in enumerate(equipos_data):
            ec = EquipmentCategory(name=cat, position=pos)
            db.add(ec)
            db.flush()
            for si_pos, si_name in enumerate(subs):
                db.add(EquipmentSubitem(category_id=ec.id, name=si_name, position=si_pos))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error: {e}")
    finally:
        db.close()

def _apply_seed_from_json():
    """Seed from config_seed.json if it exists and DB is empty."""
    import json
    json_path = os.path.join(BASE_DIR, "config_seed.json")
    if not os.path.exists(json_path):
        return
    from .models import Turno as T, Nivel as N, Macroprocess as M, WorkType as W, Action as A, Collaborator as C, EquipmentCategory as EC, EquipmentSubitem as ES
    db = SessionLocal()
    try:
        if db.query(T).count() > 0:
            return
        with open(json_path, "r", encoding="utf-8") as f:
            seed = json.load(f)
        for i, name in enumerate(seed.get("turnos", [])):
            db.add(T(name=name, position=i))
        for i, name in enumerate(seed.get("niveles", [])):
            db.add(N(name=name, position=i))
        for i, name in enumerate(seed.get("macroprocesos", [])):
            db.add(M(name=name, position=i))
        for i, name in enumerate(seed.get("work_types", [])):
            db.add(W(name=name, position=i))
        for i, name in enumerate(seed.get("acciones", [])):
            db.add(A(name=name, position=i))
        for i, name in enumerate(seed.get("colaboradores", [])):
            db.add(C(name=name, position=i))
        for cat_data in seed.get("equipos", []):
            ec = EC(name=cat_data["name"], position=cat_data.get("position", 0))
            db.add(ec)
            db.flush()
            for si_data in cat_data.get("subitems", []):
                db.add(ES(category_id=ec.id, name=si_data["name"], position=si_data.get("position", 0)))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Seed JSON] Error: {e}")
    finally:
        db.close()

# Run seeds
_seed_hardcoded()
_apply_seed_from_json()

# ─── FastAPI app ────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(BASE_DIR)  # project root (parent of backend/)
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

app = FastAPI(title="Reporte Diario de Mantenimiento", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─── Observability ──────────────────────────────────────────────────
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
        print(f"[Sentry] Enabled ({settings.environment})")
    except ImportError:
        print("[Sentry] sentry_sdk not installed, skipping")

# Logging setup
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("racs")

# ─── Health check ───────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

# ─── Include routers ────────────────────────────────────────────────
from .routers import reportes, dashboard, admin, racs, guardias

app.include_router(reportes.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(racs.router)
app.include_router(guardias.router)

logger.info("App started — routers loaded: reportes, dashboard, admin, racs, guardias")
