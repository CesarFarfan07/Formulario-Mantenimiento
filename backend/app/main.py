import os
import uuid
import io
import csv
from io import BytesIO
import shutil
from datetime import date, time, datetime, timedelta
from typing import List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from sqlalchemy import func as _sf, text as _st

from .database import engine, get_db, Base, SessionLocal
from .excel_export import build_excel
from .daily_report import generate_daily_report, list_daily_reports, REPORTS_DIR
from .models import Worker, Report, JobEntry, JobImage
from .models import EquipmentCategory, EquipmentSubitem, Collaborator, Macroprocess, WorkType, Action, Nivel, Turno
from .schemas import (
    ReportCreate, ReportResponse, WorkerResponse, JobImageResponse
)
from .config import settings, BASE_DIR

Base.metadata.create_all(bind=engine)

# ─── Seed config from hardcoded data (only if tables empty) ──────────
def _seed_hardcoded():
    db = SessionLocal()
    try:
        if db.query(Turno).count() > 0:
            return
        for i, t in enumerate(["Día", "Noche"]):
            db.add(Turno(name=t, position=i))
        for i, n in enumerate(["Nivel 05","Nivel 04","Nivel 03","Nivel 02","Nivel 01","Nivel 0","Nivel -01","Nivel -02","Nivel -03","Nivel -04","Nivel -05","Campamento","PTAR"]):
            db.add(Nivel(name=n, position=i))
        for i, (gk, n) in enumerate([
            ("Trackless", "Mantenimiento Mecánico"), ("Trackless", "Mantenimiento Eléctrico"),
            ("Convencional", "Mantenimiento Mecánico"), ("Convencional", "Mantenimiento Eléctrico"), ("Convencional", "Fabricaciones"), ("Convencional", "Instalaciones"),
            ("Electrico", "Mantenimiento Mecánico"), ("Electrico", "Mantenimiento Eléctrico"), ("Electrico", "Fabricaciones"), ("Electrico", "Instalaciones"),
        ]):
            db.add(Macroprocess(group_key=gk, name=n, position=i))
        for i, (tk, n) in enumerate([
            ("Trackless_Mecánico", "Auxilio Mecánico"), ("Trackless_Mecánico", "Bombas y Pistones"), ("Trackless_Mecánico", "Inspección y Correctivos Generales"), ("Trackless_Mecánico", "Inspección y Seguimiento en Labor"), ("Trackless_Mecánico", "Mantenimiento Preventivo PM 1"), ("Trackless_Mecánico", "Mantenimiento Preventivo PM 2"), ("Trackless_Mecánico", "Mantenimiento Preventivo PM 3"), ("Trackless_Mecánico", "Mantenimiento Preventivo PM 4"), ("Trackless_Mecánico", "Neumaticos"), ("Trackless_Mecánico", "Mantenimiento de Perforadora HC50 de Jumbo"), ("Trackless_Mecánico", "Sistemas de Dirección"), ("Trackless_Mecánico", "Sistema de Embrague"), ("Trackless_Mecánico", "Sistema de Frenos"), ("Trackless_Mecánico", "Sistemas Hidraulicos"), ("Trackless_Mecánico", "Sistemas de Suspensión"), ("Trackless_Mecánico", "Trabajos de Metalmecanica"),
            ("Trackless_Eléctrico", "Instalaciones Eléctricas, Iluminacion y Alarmas - Trackless"), ("Trackless_Eléctrico", "Inspecciones Generales y Seguimiento - Trackless"), ("Trackless_Eléctrico", "Mantenimiento Correctivo de Luces - Trackless"),
            ("Convencional_Mecánico", "Inspección y Seguimiento de equipo - General"), ("Convencional_Mecánico", "Correctivos Metalmecánica - Trackless"), ("Convencional_Mecánico", "Correcciones Metalmecánica - Convencional"), ("Convencional_Mecánico", "Mantenimiento Preventivo PM 1"), ("Convencional_Mecánico", "Mantenimiento Preventivo PM 2"), ("Convencional_Mecánico", "Mantenimiento Preventivo PM 3"), ("Convencional_Mecánico", "Mantenimiento Preventivo PM 4"),
            ("Convencional_Eléctrico", "Instalaciones Eléctricas - General"), ("Convencional_Eléctrico", "Mantenimiento Eléctrico - General"), ("Convencional_Eléctrico", "Tendido y Traslado de cables - General"), ("Convencional_Eléctrico", "Mantenimiento Preventivo Eléctrico - Convencional"), ("Convencional_Eléctrico", "Mantenimiento Correctivo Eléctrico - Convencional"), ("Convencional_Eléctrico", "Rebobinado de Motor"), ("Convencional_Eléctrico", "Telefonos"),
            ("Fabricacion_Soldadura", "Fabricaciones en General para Mina"), ("Fabricacion_Soldadura", "Fabricaciones en General para Taller"), ("Fabricacion_Soldadura", "Fabricaciones en General"), ("Fabricacion_Soldadura", "Fabricación de Alcayatas"), ("Fabricacion_Soldadura", "Correcciones de Fabricación - General"), ("Fabricacion_Soldadura", "Mantenimiento Preventivos - Convencional"),
            ("Instalaciones", "Instalaciones de Estructuras en General"), ("Instalaciones", "Instalaciones de Estructuras en Int. Mina"), ("Instalaciones", "Instalaciones de Estructuras en Campamento"), ("Instalaciones", "Telefonos"),
        ]):
            db.add(WorkType(type_key=tk, name=n, position=i))
        for i, (gk, n) in enumerate([
            ("Trackless", "Mantenimiento Preventivo"), ("Trackless", "Mantenimiento Correctivo"), ("Trackless", "Inspección (Liberación Eq.)"),
            ("Convencional_Electrico", "Mantenimiento Preventivo"), ("Convencional_Electrico", "Mantenimiento Correctivo"), ("Convencional_Electrico", "Instalación"), ("Convencional_Electrico", "Fabricación"), ("Convencional_Electrico", "Inspección (Liberación Eq.)"),
        ]):
            db.add(Action(group_key=gk, name=n, position=i))
        colab_data = {
            "Trackless": ["Wilson Apaza","Elvis Avalos","Yoel Castillo","Ronaldo Ccompara","Yordan Elguera","Miguel Espiritu","Jordi Gallegos","Jimy Huaman","Rivaldo Mamani","Ademer Moreto","Eddy Quispe","Felix Quispe","Jesús Quispe","Jesús Ramirez","Edwin Torres","Martin Sillocca"],
            "Convencional": ["Moises de la Cadena","Edgardo del Carpio","Erik Inca","Alan Llanquecha","Diego Machaca","Vlady mamani","Artemio Payehuanca","Fredy Taya","Edgar Zela","Aldair Vilca","Abraham Dionisio"],
            "Electrico": ["Ronaldo Ccompara","Jhonatan Chipane","Koos Coaquira","Wilder Espinal","Markc Huachaca","Jose Huayra","Santiago Huayra","Julio Perez","Wilber Quijahuaman","Rronar Surco"],
        }
        for gk, names in colab_data.items():
            for i, n in enumerate(names):
                db.add(Collaborator(group_name=gk, name=n, position=i))
        equipos_data = [
            ("Alimak", "Trackless", [("Alimak", "fin")]),
            ("Bomba de Pistón", "Trackless", [(f"Electrobomba de Pistón (EB.{i}-P)", "fin") for i in range(10, 17)]),
            ("Camionetas", "Convencional", [("Ambulancia (EUG-360)","kilometraje"),("Camioneta Conejo (VCP-772)","kilometraje"),("Camioneta GER-CORP (VDX-833)","kilometraje"),("Camioneta Gerencia (VDN-931)","kilometraje"),("Camioneta Gerencia (BZM-789)","kilometraje"),("Camioneta Lechera (VEG-809)","kilometraje"),("Camioneta Liebre 2 (VCW-854)","kilometraje"),("Camioneta Liebre 3 (VEE-949)","kilometraje"),("Camioneta Liebre 4 (VEH-817)","kilometraje"),("Camioneta Zorro (VAN-835)","kilometraje"),("Camioneta (VFF-923)","kilometraje"),("Camioneta (ERT-673)","kilometraje")]),
            ("Camioncitos", "Convencional", [("Camión de Azul (VCL-723)","kilometraje"),("Camión Tortuga 1 (VAP-905)","kilometraje"),("Camión Tortuga 2 (VDT-742)","kilometraje"),("Camión Tortuga 3 (VDT-726)","kilometraje"),("Camión Tortuga 4 (VEA-766)","kilometraje"),("Camión Tortuga 5 (VEE-770)","kilometraje"),("Camión Recuperación (VET-885)","kilometraje"),("Camión Rojo (VBR-892)","kilometraje")]),
            ("Cisternas", "Convencional", [("Cisterna de Agua (VDR-883)", "horometro_volquetes,kilometraje")]),
            ("Cargador Frontal", "Convencional", [("Cargador Frontal CAT 966 (CF-01)","horometro_motor"),("Cargador Frontal Liugong 856H","horometro_motor")]),
            ("Compresoras", "Convencional", [("Atlas Copco COE (GA 55)","horometro_motor"),("Atlas Copco (GA 90+) (RP 220)","horometro_motor"),("Atlas Copco (GA 90+) (Asunción)","horometro_motor"),("Atlas Copco (GA 110+)","horometro_motor"),("Atlas Copco (GA 110 VSD+)","horometro_motor"),("Atlas Copco (GA 160 VSD)","horometro_motor"),("Atlas Copco (GA 160 VSD+)","horometro_motor"),("Kaeser (SFC 200) N° 01","horometro_motor"),("Kaeser (SFC 220 N°) 02","horometro_motor")]),
            ("Dumper", "Trackless", [(f"Dumper N° {i:02d}", "fin") for i in range(1, 9)] + [("Dumper N° 10", "fin")]),
            ("Excavadora (CAT336)", "Convencional", [("Excavadora (CAT336)", "horometro_motor")]),
            ("Fabricaciones", "Convencional", [("Fabricaciones", "fin")]),
            ("Grupo Electrógeno", "Convencional", [("(GE-01) Asunción QAS 550","horometro_motor"),("(GE-02) Asunción QAS 550","horometro_motor"),("(GE-03) Asunción QAS 550","horometro_motor"),("(GE-04) Asunción MV 560","horometro_motor"),("(GE-05) Asunción QAS 500","horometro_motor"),("(GE-06) Asunción QAS 85","horometro_motor"),("(GE-07) Nivel 0 MV 560","horometro_motor"),("(GE-08) Rampa 220 MV 560","horometro_motor")]),
            ("Jumbos", "Trackless", [("Jumbo Komatsu ZJ21 (JM-01)","horometro_jumbo"),("Jumbo Muki N° 01 (JM-02)","horometro_jumbo"),("Jumbo Muki N° 02 (JM-03)","horometro_jumbo")]),
            ("Locomotoras", "Trackless", [(f"Locomotora N° {i:02d} (LOC-{i:02d})", "fin") for i in range(1, 11)]),
            ("Scooptrams", "Trackless", [("Scoop Komatsu WX07 (WX-07)","horometro_motor"),("Scoop Epiroc ST2G (ST2G)","horometro_motor"),("Scoop XCMG 1.5 YD (SD-03)","horometro_motor"),("Scoop XCMG 2.6 YD (SD-04)","horometro_motor")]),
            ("Retroexcavadora (REX-01)", "Convencional", [("Retroexcavadora (REX-01)", "horometro_motor")]),
            ("Palas Neumáticas", "Trackless", [(f"Pala N° {i:02d} (PALA-{i:02d})", "fin") for i in range(1, 11)]),
            ("Eq. Diamantina", "Trackless", [("Diamantina (PACKSAC)", "fin")]),
            ("Plataforma", "Trackless", [("Plataforma", "fin")]),
            ("Tableros", "Convencional", [("Tableros", "fin")]),
            ("Tendido de Cable", "Convencional", [("Tendido de Cable", "fin")]),
            ("Ventilador Eléctrico", "Trackless", [(f"Ventilador {'Centrífugo' if i%2 else 'Axial'} (V.{i:02d}-P)", "fin") for i in range(1, 35)]),
            ("Volquetes 4 Tn", "Convencional", [("Volquete 1 (VCI-946)","kilometraje"),("Volquete 2 (VCJ-739)","kilometraje"),("Volquete 3 (VDB-833)","kilometraje"),("Volquete 4 (VDJ-905)","kilometraje"),("Volquete 5 (VDM-742)","kilometraje")]),
            ("Volquetes - FMX", "Convencional", [("Volquete FMX 1 (BNK-709)","horometro_volquetes,kilometraje"),("Volquete FMX 2 (BDE-738)","horometro_volquetes,kilometraje"),("Volquete FMX 3 (VDJ-869)","horometro_volquetes,kilometraje"),("Volquete FMX 4 (VDJ-906)","horometro_volquetes,kilometraje"),("Volquete FMX 5 (VDF-703)","horometro_volquetes,kilometraje"),("Volquete FMX 6 (VDF-791)","horometro_volquetes,kilometraje"),("Volquete FMX 7 (CJB-903)","horometro_volquetes,kilometraje"),("Volquete FMX 8 (CJB-930)","horometro_volquetes,kilometraje"),("Volquete Shacman (CAR-839)","horometro_volquetes,kilometraje"),("Volquete Shacman (CAS-772)","horometro_volquetes,kilometraje")]),
            ("Winches Eléctricos", "Trackless", [(f"Winche Eléctrico N°{i:02d} (WE.{i:02d}-P)", "fin") for i in range(1, 5)]),
        ]
        for pos, (cat_name, act_grp, subs) in enumerate(equipos_data):
            cat = EquipmentCategory(name=cat_name, action_group=act_grp, position=pos)
            db.add(cat)
            db.flush()
            for spos, (sname, smeters) in enumerate(subs):
                db.add(EquipmentSubitem(category_id=cat.id, name=sname, meters=smeters, position=spos))
        db.commit()
        print("[OK] Hardcoded seed applied")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Hardcoded seed: {e}")
    finally:
        db.close()

# ─── Apply config_seed.json (only if tables empty) ────────────────────
import json as _json
_CONFIG_SEED = os.path.join(BASE_DIR, "config_seed.json")

def _apply_seed_from_json():
    if not os.path.exists(_CONFIG_SEED):
        return
    try:
        _sd = SessionLocal()
        if _sd.query(Turno).count() > 0:
            _sd.close()
            return
        with open(_CONFIG_SEED, "r", encoding="utf-8") as _f:
            _s = _json.load(_f)

        for i, t in enumerate(_s.get("turnos", [])):
            _sd.add(Turno(name=t["name"], position=i))
        for i, n in enumerate(_s.get("niveles", [])):
            _sd.add(Nivel(name=n["name"], position=i))
        for c in _s.get("colaboradores", []):
            _sd.add(Collaborator(group_name=c["group_name"], name=c["name"], position=c.get("position", 0)))
        for m in _s.get("macroprocesos", []):
            _sd.add(Macroprocess(group_key=m["group_key"], name=m["name"], position=m.get("position", 0)))
        for w in _s.get("tipos_trabajo", []):
            _sd.add(WorkType(type_key=w["type_key"], name=w["name"], default_action=w.get("default_action", ""), position=w.get("position", 0)))
        for a in _s.get("acciones", []):
            _sd.add(Action(group_key=a["group_key"], name=a["name"], position=a.get("position", 0)))
        for eq in _s.get("equipos", []):
            _cat = EquipmentCategory(name=eq["name"], action_group=eq.get("action_group", ""), position=eq.get("position", 0))
            _sd.add(_cat)
            _sd.flush()
            for j, sub in enumerate(eq.get("subitems", [])):
                _sd.add(EquipmentSubitem(category_id=_cat.id, name=sub["name"], meters=sub.get("meters", "fin"), position=j))
        _sd.commit()
        total = sum(len(v) for v in _s.values())
        print(f"[OK] Seed applied from config_seed.json ({total} records)")
    except Exception as _e:
        _sd.rollback()
        print(f"[WARN] Could not apply config_seed.json: {_e}")
    finally:
        _sd.close()

# JSON seed first (primary), hardcoded seed second (fallback if no JSON)
_apply_seed_from_json()
_seed_hardcoded()

# ─── Ensure schema columns exist ─────────────────────────────────────────
_try_alter = lambda sql, msg: (_d := SessionLocal(), _d.execute(_st(sql)), _d.commit(), _d.close(), print(msg)) if None else None
try:
    _d = SessionLocal(); _d.execute(_st('ALTER TABLE work_types ADD COLUMN default_action VARCHAR(200)')); _d.commit(); _d.close(); print("[MIGRACION] Columna default_action agregada a work_types")
except: _d.rollback(); _d.close()
try:
    _d = SessionLocal(); _d.execute(_st('ALTER TABLE job_entries ADD COLUMN collaborators TEXT')); _d.commit(); _d.close(); print("[MIGRACION] Columna collaborators agregada a job_entries")
except: _d.rollback(); _d.close()

# ─── Create indexes ─────────────────────────────────────────────────────
for _sql in [
    "CREATE INDEX IF NOT EXISTS ix_reports_date_id ON reports(date, id)",
    "CREATE INDEX IF NOT EXISTS ix_reports_group_shift_date ON reports(group_name, shift, date)",
    "CREATE INDEX IF NOT EXISTS ix_reports_created_at_id ON reports(created_at, id)",
    "CREATE INDEX IF NOT EXISTS ix_job_entries_report_id ON job_entries(report_id)",
]:
    try:
        _d = SessionLocal(); _d.execute(_st(_sql)); _d.commit(); _d.close()
    except: _d.rollback(); _d.close()
print("[OK] Indices verificados")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

app = FastAPI(title="Reporte Diario de Mantenimiento", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def parse_time(value):
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            parts = value.strip().split(":")
            if len(parts) == 2:
                return time(int(parts[0]), int(parts[1]))
            elif len(parts) == 3:
                return time(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            continue
    return None


def parse_date(value):
    if not value:
        return date.today()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/workers", response_model=List[WorkerResponse])
def list_workers(db: Session = Depends(get_db)):
    return db.query(Worker).order_by(Worker.name).all()


@app.post("/api/workers")
def create_worker(name: str = Form(...), email: str = Form(...), group_name: str = Form(""), db: Session = Depends(get_db)):
    worker = Worker(name=name, email=email, group_name=group_name)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@app.post("/api/reports", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(
        Worker.name == report.worker_name,
        Worker.email == report.worker_email
    ).first()
    if not worker:
        worker = Worker(name=report.worker_name, email=report.worker_email)
        db.add(worker)
        db.flush()

    # Populate report-level collaborator fields from entries (backward compat)
    all_colabs = {
        g: [] for g in ["Trackless", "Convencional", "Electrico"]
    }
    for entry_data in report.entries:
        if entry_data.collaborators:
            g_key = "Trackless" if "Trackless" in (report.group_name or "") else "Convencional" if "Convencional" in (report.group_name or "") else "Electrico"
            all_colabs[g_key].append(entry_data.collaborators)

    db_report = Report(
        worker_id=worker.id,
        date=parse_date(report.date),
        shift=report.shift,
        group_name=report.group_name,
        start_time=parse_time(report.start_time),
        end_time=parse_time(report.end_time),
        collaborators_trackless=", ".join(all_colabs["Trackless"]) or report.collaborators_trackless,
        collaborators_convencional=", ".join(all_colabs["Convencional"]) or report.collaborators_convencional,
        collaborators_electrico=", ".join(all_colabs["Electrico"]) or report.collaborators_electrico,
    )
    db.add(db_report)
    db.flush()

    for entry_data in report.entries:
        db_entry = JobEntry(
            report_id=db_report.id,
            macroprocess=entry_data.macroprocess,
            work_type=entry_data.work_type,
            work_subtype=entry_data.work_subtype,
            action=entry_data.action,
            description=entry_data.description,
            level=entry_data.level,
            location=entry_data.location,
            start_time_int=parse_time(entry_data.start_time_int),
            end_time_int=parse_time(entry_data.end_time_int),
            duration=entry_data.duration,
            equipment=entry_data.equipment,
            horometer_motor=entry_data.horometer_motor,
            horometer_motor_jumbo=entry_data.horometer_motor_jumbo,
            horometer_motor_volquetes=entry_data.horometer_motor_volquetes,
            horometer_electric=entry_data.horometer_electric,
            horometer_percussion=entry_data.horometer_percussion,
            kilometer=entry_data.kilometer,
            blanco=entry_data.blanco,
            collaborators=entry_data.collaborators,
        )
        db.add(db_entry)
    db.commit()
    db.refresh(db_report)
    return db_report


@app.get("/api/reports")
def list_reports(
    cursor_id: int = Query(None, alias="cursor"),
    cursor_date: str = Query(None, alias="cursor_date"),
    limit: int = Query(50),
    worker_name: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    db: Session = Depends(get_db),
):
    try:
        q = db.query(Report).options(joinedload(Report.worker))
        if worker_name:
            q = q.join(Worker).filter(Worker.name.ilike(f"%{worker_name}%"))
        if date_from:
            q = q.filter(Report.date >= parse_date(date_from))
        if date_to:
            q = q.filter(Report.date <= parse_date(date_to))
        # Keyset pagination: (created_at, id) < (cursor_date, cursor_id)
        if cursor_id is not None and cursor_date is not None:
            try:
                dt = datetime.fromisoformat(cursor_date)
            except Exception:
                dt = None
            if dt is not None:
                q = q.filter(Report.created_at < dt).filter(Report.id < cursor_id)
        reports = q.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit + 1).all()
        has_more = len(reports) > limit
        reports = reports[:limit]
        result = []
        for rp in reports:
            d = {
                "id": rp.id,
                "worker_id": rp.worker_id,
                "worker_name": rp.worker.name if rp.worker else f"ID {rp.worker_id}",
                "date": rp.date,
                "shift": rp.shift,
                "group_name": rp.group_name,
                "start_time": rp.start_time,
                "end_time": rp.end_time,
                "collaborators_trackless": rp.collaborators_trackless,
                "collaborators_convencional": rp.collaborators_convencional,
                "collaborators_electrico": rp.collaborators_electrico,
                "created_at": rp.created_at.isoformat() if rp.created_at else None,
                "entries": [{
                    "id": e.id,
                    "report_id": e.report_id,
                    "macroprocess": e.macroprocess,
                    "work_type": e.work_type,
                    "work_subtype": e.work_subtype,
                    "action": e.action,
                    "description": e.description,
                    "level": e.level,
                    "location": e.location,
                    "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
                    "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
                    "duration": e.duration,
                    "equipment": e.equipment,
                    "horometer_motor": e.horometer_motor,
                    "horometer_motor_jumbo": e.horometer_motor_jumbo,
                    "horometer_motor_volquetes": e.horometer_motor_volquetes,
                    "horometer_electric": e.horometer_electric,
                    "horometer_percussion": e.horometer_percussion,
                    "kilometer": e.kilometer,
                    "blanco": e.blanco,
                    "collaborators": e.collaborators,
                    "images": [{"id": img.id, "filename": img.filename, "original_name": img.original_name} for img in e.images],
                } for e in rp.entries],
            }
            result.append(d)
        last_item = reports[-1] if reports else None
        return {
            "data": result,
            "next_cursor": (last_item.id, last_item.created_at.isoformat()) if last_item and has_more else None,
            "has_more": has_more,
        }
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error al listar reportes: {exc}")


@app.get("/api/reports/export/excel")
def export_reports_excel(
    date_from: str = Query(None),
    date_to: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Report).options(joinedload(Report.worker)).options(joinedload(Report.entries).joinedload(JobEntry.images))
    if date_from:
        q = q.filter(Report.date >= parse_date(date_from))
    if date_to:
        q = q.filter(Report.date <= parse_date(date_to))
    reports = q.order_by(Report.created_at.asc()).all()

    data = []
    for rp in reports:
        d = {
            "id": rp.id,
            "worker_id": rp.worker_id,
            "worker_name": rp.worker.name if rp.worker else None,
            "date": rp.date,
            "shift": rp.shift,
            "group_name": rp.group_name,
            "start_time": rp.start_time,
            "end_time": rp.end_time,
            "collaborators_trackless": rp.collaborators_trackless,
            "collaborators_convencional": rp.collaborators_convencional,
            "collaborators_electrico": rp.collaborators_electrico,
            "created_at": rp.created_at,
            "entries": [{
                "id": e.id,
                "macroprocess": e.macroprocess,
                "work_type": e.work_type,
                "work_subtype": e.work_subtype,
                "action": e.action,
                "description": e.description,
                "level": e.level,
                "location": e.location,
                "start_time_int": e.start_time_int,
                "end_time_int": e.end_time_int,
                "duration": e.duration,
                "equipment": e.equipment,
                "horometer_motor": e.horometer_motor,
                "horometer_motor_jumbo": e.horometer_motor_jumbo,
                "horometer_motor_volquetes": e.horometer_motor_volquetes,
                "horometer_electric": e.horometer_electric,
                "horometer_percussion": e.horometer_percussion,
                "kilometer": e.kilometer,
                "blanco": e.blanco,
                "collaborators": e.collaborators,
            } for e in rp.entries],
        }
        data.append(d)

    wb = build_excel(data)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_mantenimiento.xlsx"},
    )


@app.get("/api/reports/export/csv")
def export_reports_csv(
    date_from: str = Query(None),
    date_to: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Report).join(Worker)
    if date_from:
        q = q.filter(Report.date >= parse_date(date_from))
    if date_to:
        q = q.filter(Report.date <= parse_date(date_to))
    reports = q.order_by(Report.created_at.desc()).all()

    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID Reporte","Fecha","Turno","Grupo","Colaboradores del Trabajo",
                "Trabajo #","Macroproceso","Tipo Trabajo","Acción","Descripción","Equipo","Nivel","Lugar",
                "Inicio","Fin","Duración","Hor. Motor","Hor. Jumbo","Hor. Volquetes","Hor. Eléctrico","Hor. Percusión","Kilometraje"])

    for rp in reports:
        entries = rp.entries if hasattr(rp, 'entries') and rp.entries else [None]
        for entry in entries:
            colabs = entry.collaborators if entry and entry.collaborators else ""
            w.writerow([
                rp.id, rp.date, rp.shift, rp.group_name,
                colabs,
                entry.id if entry else "", entry.macroprocess if entry else "", entry.work_type if entry else "",
                entry.action if entry else "", entry.description if entry else "", entry.equipment if entry else "",
                entry.level if entry else "", entry.location if entry else "",
                entry.start_time_int if entry else "", entry.end_time_int if entry else "", entry.duration if entry else "",
                entry.horometer_motor if entry else "", entry.horometer_motor_jumbo if entry else "",
                entry.horometer_motor_volquetes if entry else "", entry.horometer_electric if entry else "",
                entry.horometer_percussion if entry else "", entry.kilometer if entry else "",
            ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=reportes.csv"})


# ─── Daily Report Endpoints ─────────────────────────────────────────────────

@app.get("/api/daily-reports")
def get_daily_reports():
    """List existing daily reports."""
    return list_daily_reports()


@app.post("/api/daily-reports/generate")
def generate_daily(target_date: str = Body("", embed=True), db: Session = Depends(get_db)):
    """Generate daily report for a given date (YYYY-MM-DD). Defaults to yesterday."""
    if target_date and target_date.strip():
        d = parse_date(target_date.strip())
    else:
        d = (datetime.now() - timedelta(days=1)).date()

    if d is None:
        raise HTTPException(400, "Fecha invalida")

    # Fetch all reports for this date, grouped by group_name and shift
    reports = db.query(Report).options(
        joinedload(Report.worker), joinedload(Report.entries)
    ).filter(Report.date == d).all()

    if not reports:
        raise HTTPException(404, f"No hay reportes para {d.isoformat()}")

    # Group data by group_name → shift
    grouped = {}
    for rp in reports:
        group = rp.group_name
        shift = rp.shift
        grouped.setdefault(group, {}).setdefault(shift, []).append({
            "id": rp.id,
            "date": rp.date,
            "shift": shift,
            "group_name": group,
            "collaborators_trackless": rp.collaborators_trackless,
            "collaborators_convencional": rp.collaborators_convencional,
            "collaborators_electrico": rp.collaborators_electrico,
            "entries": [{
                "macroprocess": e.macroprocess,
                "work_type": e.work_type,
                "work_subtype": e.work_subtype,
                "action": e.action,
                "description": e.description,
                "level": e.level,
                "location": e.location,
                "start_time_int": e.start_time_int,
                "end_time_int": e.end_time_int,
                "duration": e.duration,
                "equipment": e.equipment,
                "horometer_motor": e.horometer_motor,
                "horometer_motor_jumbo": e.horometer_motor_jumbo,
                "horometer_motor_volquetes": e.horometer_motor_volquetes,
                "horometer_electric": e.horometer_electric,
                "horometer_percussion": e.horometer_percussion,
                "kilometer": e.kilometer,
                "collaborators": e.collaborators,
            } for e in rp.entries],
        })

    filepath = generate_daily_report(d, grouped)
    fname = os.path.basename(filepath)
    return {"ok": True, "filename": fname, "path": f"/static/daily_reports/{fname}"}


@app.get("/api/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).options(joinedload(Report.worker)).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Reporte no encontrado")
    d = {
        "id": report.id,
        "worker_id": report.worker_id,
        "worker_name": report.worker.name if report.worker else f"ID {report.worker_id}",
        "date": report.date,
        "shift": report.shift,
        "group_name": report.group_name,
        "start_time": report.start_time,
        "end_time": report.end_time,
        "collaborators_trackless": report.collaborators_trackless,
        "collaborators_convencional": report.collaborators_convencional,
        "collaborators_electrico": report.collaborators_electrico,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "entries": [{
            "id": e.id,
            "report_id": e.report_id,
            "macroprocess": e.macroprocess,
            "work_type": e.work_type,
            "work_subtype": e.work_subtype,
            "action": e.action,
            "description": e.description,
            "level": e.level,
            "location": e.location,
            "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
            "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
            "duration": e.duration,
            "equipment": e.equipment,
            "horometer_motor": e.horometer_motor,
            "horometer_motor_jumbo": e.horometer_motor_jumbo,
            "horometer_motor_volquetes": e.horometer_motor_volquetes,
            "horometer_electric": e.horometer_electric,
            "horometer_percussion": e.horometer_percussion,
            "kilometer": e.kilometer,
            "blanco": e.blanco,
            "collaborators": e.collaborators,
            "images": [{"id": img.id, "filename": img.filename, "original_name": img.original_name} for img in e.images],
        } for e in report.entries],
    }
    return d


DELETE_REPORT_PASSWORD = "70212352"


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: int, password: str = Query(...), db: Session = Depends(get_db)):
    if password != DELETE_REPORT_PASSWORD:
        raise HTTPException(401, "Contraseña incorrecta")
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Reporte no encontrado")
    db.delete(report)
    db.commit()
    return {"ok": True, "deleted_id": report_id}


@app.post("/api/reports/batch-delete")
def batch_delete_reports(ids: list[int] = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    if password != DELETE_REPORT_PASSWORD:
        raise HTTPException(401, "Contraseña incorrecta")
    deleted = []
    for rid in ids:
        report = db.query(Report).filter(Report.id == rid).first()
        if report:
            db.delete(report)
            deleted.append(rid)
    db.commit()
    return {"ok": True, "deleted_ids": deleted}


@app.post("/api/reports/delete-verify")
def verify_delete_password(password: str = Body(..., embed=True)):
    if password == DELETE_REPORT_PASSWORD:
        return {"ok": True}
    raise HTTPException(401, "Contraseña incorrecta")


@app.put("/api/reports/{report_id}")
def update_report(report_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    if data.get("password") != DELETE_REPORT_PASSWORD:
        raise HTTPException(401, "Contraseña incorrecta")
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Reporte no encontrado")
    if "date" in data:
        report.date = parse_date(data["date"])
    if "shift" in data:
        report.shift = data["shift"]
    if "group_name" in data:
        report.group_name = data["group_name"]
    db.commit()
    db.refresh(report)
    return {"ok": True, "id": report.id}


@app.post("/api/reports/{entry_id}/images")
async def upload_image(entry_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    entry = db.query(JobEntry).filter(JobEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entrada de trabajo no encontrada")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Formato no permitido: {ext}. Use: jpg, png, gif, webp")

    content = await file.read()
    if len(content) > settings.max_image_size_mb * 1024 * 1024:
        raise HTTPException(400, f"Imagen muy grande. Máx: {settings.max_image_size_mb}MB")

    # Store in date-based folders to avoid 100k files in one dir
    today = datetime.now().strftime("%Y/%m/%d")
    rel_dir = today.replace("/", os.sep)
    dest_dir = os.path.join(UPLOAD_DIR, rel_dir)
    os.makedirs(dest_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join(rel_dir, unique_name)
    file_path = os.path.join(UPLOAD_DIR, rel_path)

    with open(file_path, "wb") as f:
        f.write(content)

    db_image = JobImage(
        entry_id=entry_id,
        filename=rel_path,
        original_name=file.filename,
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


@app.delete("/api/images/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(JobImage).filter(JobImage.id == image_id).first()
    if not image:
        raise HTTPException(404, "Imagen no encontrada")

    file_path = os.path.join(UPLOAD_DIR, image.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(image)
    db.commit()
    return {"ok": True}


@app.get("/api/equipment/{equipo}/last-reading")
def get_equipment_last_reading(equipo: str, db: Session = Depends(get_db)):
    """Return the last horometer/kilometer readings for a given piece of equipment."""
    entry = (
        db.query(JobEntry)
        .filter(JobEntry.equipment == equipo)
        .order_by(JobEntry.id.desc())
        .first()
    )
    if not entry:
        return {"found": False, "readings": {}}
    readings = {
        "horometer_motor": entry.horometer_motor,
        "horometer_motor_jumbo": entry.horometer_motor_jumbo,
        "horometer_motor_volquetes": entry.horometer_motor_volquetes,
        "horometer_electric": entry.horometer_electric,
        "horometer_percussion": entry.horometer_percussion,
        "kilometer": entry.kilometer,
    }
    return {"found": True, "readings": readings}


@app.get("/api/options")
def get_options(db: Session = Depends(get_db)):
    turnos = [t.name for t in db.query(Turno).order_by(Turno.position).all()]
    grupos = ["Mantt. Eq. Trackless", "Mantt. Eq. Convencional", "Mantt. Eq. Electrico"]

    colab = {}
    for c in db.query(Collaborator).order_by(Collaborator.position).all():
        colab.setdefault(c.group_name, []).append(c.name)

    macro = {}
    for m in db.query(Macroprocess).order_by(Macroprocess.position).all():
        macro.setdefault(m.group_key, []).append(m.name)

    wt = {}
    for w in db.query(WorkType).order_by(WorkType.position).all():
        wt.setdefault(w.type_key, []).append({"name": w.name, "default_action": w.default_action or ""})

    acc = {}
    for a in db.query(Action).order_by(Action.position).all():
        acc.setdefault(a.group_key, []).append(a.name)

    niveles = [n.name for n in db.query(Nivel).order_by(Nivel.position).all()]

    equipos = {}
    for cat in db.query(EquipmentCategory).order_by(EquipmentCategory.position).all():
        subs = []
        for sub in cat.subitems:
            subs.append({"nombre": sub.name, "mide": sub.meters})
        equipos[cat.name] = {"subequipos": subs, "accion_grupo": cat.action_group or ""}

    return {
        "turnos": turnos,
        "grupos": grupos,
        "colaboradores": colab,
        "colab_max_select": 4,
        "macroprocesos": macro,
        "tipos_trabajo": wt,
        "acciones": acc,
        "niveles": niveles,
        "equipos": equipos,
    }


# ─── Dashboard ────────────────────────────────────────────────────────────────

def _parse_duration_minutes(dur):
    if not dur:
        return None
    try:
        parts = dur.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _build_filtered_query(db, date_from, date_to, group):
    """Return a base query of JobEntry joined to Report with filters applied."""
    q = db.query(JobEntry).join(Report)
    if date_from:
        q = q.filter(Report.date >= parse_date(date_from))
    if date_to:
        q = q.filter(Report.date <= parse_date(date_to))
    if group:
        q = q.filter(Report.group_name == group)
    return q


def _compute_period_stats(db, date_from, date_to, group):
    """Compute all stats for a single period."""
    q_base = _build_filtered_query(db, date_from, date_to, group)

    # Total jobs
    total_jobs = q_base.with_entities(_sf.count(JobEntry.id)).scalar() or 0

    # Distinct workers
    workers = (
        db.query(Worker.id, Worker.name, Worker.group_name)
        .join(Report)
    )
    if date_from:
        workers = workers.filter(Report.date >= parse_date(date_from))
    if date_to:
        workers = workers.filter(Report.date <= parse_date(date_to))
    if group:
        workers = workers.filter(Report.group_name == group)
    workers = workers.distinct().all()
    worker_count = len(workers)

    # Distinct collaborators
    collab_q = q_base.with_entities(JobEntry.collaborators).filter(JobEntry.collaborators.isnot(None))
    collab_names = set()
    for (c,) in collab_q.all():
        for name in c.split(","):
            name = name.strip()
            if name:
                collab_names.add(name)

    # Total duration hours
    dur_q = q_base.with_entities(JobEntry.duration).filter(JobEntry.duration.isnot(None), JobEntry.duration != "")
    total_minutes = 0
    for (d,) in dur_q.all():
        m = _parse_duration_minutes(d)
        if m is not None:
            total_minutes += m
    total_hours = round(total_minutes / 60, 1) if total_minutes else 0

    # Average job duration
    avg_minutes = round(total_minutes / total_jobs, 1) if total_jobs else 0

    # Jobs by equipment
    equip_data = (
        q_base.with_entities(JobEntry.equipment, JobEntry.duration)
        .filter(JobEntry.equipment.isnot(None), JobEntry.equipment != "")
        .all()
    )
    from collections import defaultdict
    equip_durs = defaultdict(list)
    for equip, dur in equip_data:
        if dur:
            equip_durs[equip].append(dur)
    jobs_by_equipment = []
    for equip, durs in sorted(equip_durs.items(), key=lambda x: -len(x[1])):
        cnt = len(durs)
        mins = [_parse_duration_minutes(d) for d in durs]
        valid = [m for m in mins if m is not None]
        avg = round(sum(valid) / len(valid), 1) if valid else None
        equip_hours = round((sum(valid) / 60), 1) if valid else 0
        jobs_by_equipment.append({
            "equipment": equip, "count": cnt,
            "avg_duration_min": avg, "total_hours": equip_hours,
        })

    # Jobs by team
    team_q = (
        q_base.with_entities(Report.group_name, _sf.count(JobEntry.id))
        .group_by(Report.group_name)
        .order_by(_sf.count(JobEntry.id).desc())
        .all()
    )
    jobs_by_team = [{"team": g, "count": c} for g, c in team_q]

    # Avg duration by team
    team_dur_q = (
        q_base.with_entities(Report.group_name, JobEntry.duration)
        .filter(JobEntry.duration.isnot(None), JobEntry.duration != "")
        .all()
    )
    team_durs = defaultdict(list)
    for team, dur in team_dur_q:
        if dur:
            team_durs[team].append(dur)
    avg_dur_by_team = []
    for team, durs in team_durs.items():
        mins = [_parse_duration_minutes(d) for d in durs]
        valid = [m for m in mins if m is not None]
        avg = round(sum(valid) / len(valid), 1) if valid else 0
        avg_dur_by_team.append({"team": team, "avg_min": avg})

    # Jobs per day (trend)
    day_q = (
        q_base.with_entities(Report.date, _sf.count(JobEntry.id))
        .group_by(Report.date)
        .order_by(Report.date)
        .all()
    )
    jobs_per_day = [{"date": str(d), "count": c} for d, c in day_q]

    # Shift comparison
    shift_q = (
        q_base.with_entities(Report.shift, _sf.count(JobEntry.id))
        .group_by(Report.shift)
        .all()
    )
    shift_comparison = {s or "Sin turno": c for s, c in shift_q}

    # PM vs CM ratio (action-based: Preventivo ≈ PM, Correctivo ≈ CM)
    action_q = (
        q_base.with_entities(JobEntry.action, _sf.count(JobEntry.id))
        .filter(JobEntry.action.isnot(None), JobEntry.action != "")
        .group_by(JobEntry.action)
        .all()
    )
    pm_count = sum(c for a, c in action_q if "Preventivo" in (a or ""))
    cm_count = sum(c for a, c in action_q if "Correctivo" in (a or ""))
    pm_cm_ratio = {
        "pm": pm_count,
        "cm": cm_count,
        "other": total_jobs - pm_count - cm_count,
        "pm_pct": round(pm_count / total_jobs * 100, 1) if total_jobs else 0,
        "cm_pct": round(cm_count / total_jobs * 100, 1) if total_jobs else 0,
    }

    # Macroprocess distribution
    macro_q = (
        q_base.with_entities(JobEntry.macroprocess, _sf.count(JobEntry.id))
        .filter(JobEntry.macroprocess.isnot(None), JobEntry.macroprocess != "")
        .group_by(JobEntry.macroprocess)
        .order_by(_sf.count(JobEntry.id).desc())
        .all()
    )
    macroprocess_dist = [{"macroprocess": m or "Sin especificar", "count": c} for m, c in macro_q]

    # Top collaborators
    collab_counter = {}
    for (c,) in collab_q.all():
        for name in c.split(","):
            n = name.strip()
            if n:
                collab_counter[n] = collab_counter.get(n, 0) + 1
    top_collaborators = [{"name": k, "count": v} for k, v in
                         sorted(collab_counter.items(), key=lambda x: -x[1])[:15]]

    # Weekly summaries (ISO weeks within period)
    weeks = {}
    for d_str, cnt in day_q:
        d = d_str if isinstance(d_str, date) else parse_date(str(d_str))
        if d is None:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in weeks:
            # Find week start (Monday)
            monday = d - timedelta(days=d.weekday())
            weeks[week_key] = {"week": week_key, "start": str(monday), "count": 0, "by_team": {}}
        weeks[week_key]["count"] += cnt
    # Get team breakdown per week
    for week_key in weeks:
        ws = parse_date(weeks[week_key]["start"])
        we = ws + timedelta(days=6)
        wt_q = (
            q_base.with_entities(Report.group_name, _sf.count(JobEntry.id))
            .filter(Report.date >= ws, Report.date <= we)
            .group_by(Report.group_name)
            .all()
        )
        weeks[week_key]["by_team"] = {g or "Sin grupo": c for g, c in wt_q}
    weekly_summaries = sorted(weeks.values(), key=lambda x: x["week"])

    return {
        "kpis": {
            "total_jobs": total_jobs,
            "total_hours": total_hours,
            "worker_count": worker_count,
            "collaborator_count": len(collab_names),
            "avg_duration_min": avg_minutes,
            "pm_pct": pm_cm_ratio["pm_pct"],
            "cm_pct": pm_cm_ratio["cm_pct"],
        },
        "workers": [{"id": w.id, "name": w.name, "team": w.group_name} for w in workers],
        "jobs_by_equipment": jobs_by_equipment,
        "top_equipment": jobs_by_equipment[:10],
        "jobs_per_day": jobs_per_day,
        "jobs_by_team": jobs_by_team,
        "avg_duration_by_team": avg_dur_by_team,
        "shift_comparison": shift_comparison,
        "pm_cm_ratio": pm_cm_ratio,
        "macroprocess_dist": macroprocess_dist,
        "top_collaborators": top_collaborators,
        "weekly_summaries": weekly_summaries,
    }


def _compute_okrs(stats):
    """Generate OKR suggestions based on actual data."""
    pct = stats["pm_cm_ratio"]["pm_pct"]
    cm_pct = stats["pm_cm_ratio"]["cm_pct"]
    avg_min = stats["kpis"]["avg_duration_min"]
    total_jobs = stats["kpis"]["total_jobs"]
    total_hours = stats["kpis"]["total_hours"]
    workers = stats["kpis"]["worker_count"]
    collabs = stats["kpis"]["collaborator_count"]

    okrs = []

    # OKR 1: Maintenance quality
    okrs.append({
        "objective": "Mejorar la Calidad del Mantenimiento",
        "key_results": [
            {
                "kr": f"Aumentar mantenimiento preventivo de {pct}% a ≥70%",
                "current": f"{pct}%",
                "target": "≥70%",
                "progress": "on_track" if pct >= 50 else "needs_attention" if pct >= 30 else "critical",
            },
            {
                "kr": f"Reducir mantenimiento correctivo de {cm_pct}% a ≤30%",
                "current": f"{cm_pct}%",
                "target": "≤30%",
                "progress": "on_track" if cm_pct <= 30 else "needs_attention" if cm_pct <= 50 else "critical",
            },
            {
                "kr": f"Reducir tiempo promedio por trabajo de {avg_min} min a ≤60 min",
                "current": f"{avg_min} min",
                "target": "≤60 min",
                "progress": "on_track" if avg_min <= 60 else "needs_attention" if avg_min <= 90 else "critical",
            },
        ]
    })

    # OKR 2: Productivity
    jobs_per_worker = round(total_jobs / workers, 1) if workers else 0
    okrs.append({
        "objective": "Optimizar la Productividad del Equipo",
        "key_results": [
            {
                "kr": f"Mantener ≥4 trabajos por trabajador ({jobs_per_worker} actual)",
                "current": f"{jobs_per_worker}",
                "target": "≥4",
                "progress": "on_track" if jobs_per_worker >= 4 else "needs_attention" if jobs_per_worker >= 2.5 else "critical",
            },
            {
                "kr": f"Aumentar colaboradores activos de {collabs} a ≥{min(collabs + 5, 40)}",
                "current": f"{collabs}",
                "target": f"≥{min(collabs + 5, 40)}",
                "progress": "on_track" if collabs >= 15 else "needs_attention",
            },
        ]
    })

    # OKR 3: Data-driven
    okrs.append({
        "objective": "Fortalecer la Gestión Basada en Datos",
        "key_results": [
            {
                "kr": "Registrar 100% de trabajos en plataforma digital",
                "current": "Activo",
                "target": "100%",
                "progress": "on_track",
            },
            {
                "kr": f"Completar {total_jobs}+ registros en el período",
                "current": f"{total_jobs}",
                "target": "Creciente",
                "progress": "on_track" if total_jobs >= 20 else "needs_attention",
            },
            {
                "kr": f"Mantener {total_hours} horas hombre registradas con precisión",
                "current": f"{total_hours} hrs",
                "target": "≥100 hrs",
                "progress": "on_track" if total_hours >= 100 else "needs_attention",
            },
        ]
    })

    return okrs


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/dashboard/summary")
def dashboard_summary(
    date_from: str = Query(None),
    date_to: str = Query(None),
    group: str = Query(None),
    compare_from: str = Query(None),
    compare_to: str = Query(None),
    db: Session = Depends(get_db),
):
    try:
        today = date.today()
        if not date_from or not date_to:
            if today.day >= 26:
                period_start = today.replace(day=26)
            else:
                period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=26)
            period_end = (period_start + timedelta(days=32)).replace(day=25)
            if not date_from:
                date_from = period_start.isoformat()
            if not date_to:
                date_to = period_end.isoformat()

        period_label = f"{parse_date(date_from).strftime('%d/%m/%Y')} – {parse_date(date_to).strftime('%d/%m/%Y')}"

        current = _compute_period_stats(db, date_from, date_to, group)
        current["label"] = period_label
        current["date_from"] = date_from
        current["date_to"] = date_to

        result = {
            "current": current,
            "comparison": None,
            "okrs": _compute_okrs(current),
        }

        if compare_from and compare_to:
            comp = _compute_period_stats(db, compare_from, compare_to, group)
            comp["label"] = f"{parse_date(compare_from).strftime('%d/%m/%Y')} – {parse_date(compare_to).strftime('%d/%m/%Y')}"
            comp["date_from"] = compare_from
            comp["date_to"] = compare_to
            result["comparison"] = comp

        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error generando dashboard: {exc}")


# ─── Admin routes ─────────────────────────────────────────────────────────────

ADMIN_MODELS = {
    "turnos": Turno,
    "niveles": Nivel,
    "colaboradores": Collaborator,
    "macroprocesos": Macroprocess,
    "tipos_trabajo": WorkType,
    "acciones": Action,
    "equipos": EquipmentCategory,
    "subequipos": EquipmentSubitem,
}


ADMIN_PASSWORD = "Mantt.1"


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/api/admin/verify")
def admin_verify(password: str = Body(..., embed=True)):
    if password == ADMIN_PASSWORD:
        return {"ok": True}
    raise HTTPException(401, "Contraseña incorrecta")


@app.get("/api/admin/{entity}")
def admin_list(entity: str, db: Session = Depends(get_db)):
    if entity == "equipos":
        cats = db.query(EquipmentCategory).order_by(EquipmentCategory.position).all()
        return [{"id": c.id, "name": c.name, "action_group": c.action_group, "subitems": [{"id": s.id, "name": s.name, "meters": s.meters} for s in c.subitems]} for c in cats]
    if entity == "subequipos":
        return db.query(EquipmentSubitem).order_by(EquipmentSubitem.position).all()
    model = ADMIN_MODELS.get(entity)
    if not model:
        raise HTTPException(400, "Entidad no valida")
    return db.query(model).order_by(model.position).all()


@app.post("/api/admin/{entity}")
def admin_create(entity: str, data: dict, db: Session = Depends(get_db)):
    if entity == "turnos":
        obj = Turno(name=data["name"], position=db.query(Turno).count())
    elif entity == "niveles":
        obj = Nivel(name=data["name"], position=db.query(Nivel).count())
    elif entity == "colaboradores":
        obj = Collaborator(group_name=data["group_name"], name=data["name"], position=db.query(Collaborator).count())
    elif entity == "macroprocesos":
        obj = Macroprocess(group_key=data["group_key"], name=data["name"], position=db.query(Macroprocess).count())
    elif entity == "tipos_trabajo":
        obj = WorkType(type_key=data["type_key"], name=data["name"], position=db.query(WorkType).count(), default_action=data.get("default_action", ""))
    elif entity == "acciones":
        obj = Action(group_key=data["group_key"], name=data["name"], position=db.query(Action).count())
    elif entity == "equipos":
        obj = EquipmentCategory(name=data["name"], action_group=data.get("action_group", ""), position=db.query(EquipmentCategory).count())
        db.add(obj)
        db.flush()
        if "subitems" in data:
            for i, s in enumerate(data["subitems"]):
                db.add(EquipmentSubitem(category_id=obj.id, name=s["name"], meters=s.get("meters", "fin"), position=i))
    elif entity == "subequipos":
        obj = EquipmentSubitem(category_id=data["category_id"], name=data["name"], meters=data.get("meters", "fin"), position=db.query(EquipmentSubitem).count())
    else:
        raise HTTPException(400, "Entidad no valida")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.put("/api/admin/{entity}/{item_id}")
def admin_update(entity: str, item_id: int, data: dict, db: Session = Depends(get_db)):
    if entity == "equipos":
        obj = db.query(EquipmentCategory).filter(EquipmentCategory.id == item_id).first()
        if not obj: raise HTTPException(404)
        if "name" in data: obj.name = data["name"]
        if "action_group" in data: obj.action_group = data["action_group"]
        if "subitems" in data:
            db.query(EquipmentSubitem).filter(EquipmentSubitem.category_id == obj.id).delete()
            for i, s in enumerate(data["subitems"]):
                db.add(EquipmentSubitem(category_id=obj.id, name=s["name"], meters=s.get("meters", "fin"), position=i))
    elif entity == "subequipos":
        obj = db.query(EquipmentSubitem).filter(EquipmentSubitem.id == item_id).first()
        if not obj: raise HTTPException(404)
        if "name" in data: obj.name = data["name"]
        if "meters" in data: obj.meters = data["meters"]
    else:
        model = ADMIN_MODELS.get(entity)
        if not model: raise HTTPException(400)
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj: raise HTTPException(404)
        for key, val in data.items():
            if hasattr(obj, key) and key not in ("id", "position"):
                setattr(obj, key, val)
    db.commit()
    db.refresh(obj)
    return obj


@app.put("/api/admin/{entity}/reorder/{item_id}")
def admin_reorder(entity: str, item_id: int, direction: str = "up", db: Session = Depends(get_db)):
    """Move an item up or down in position ordering."""
    import math

    if entity == "equipos":
        model_cls = EquipmentCategory
    elif entity == "subequipos":
        model_cls = EquipmentSubitem
    else:
        model_cls = ADMIN_MODELS.get(entity)
    if not model_cls:
        raise HTTPException(400, "Entidad no valida")

    item = db.query(model_cls).filter(model_cls.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item no encontrado")

    all_items = db.query(model_cls).order_by(model_cls.position, model_cls.id).all()

    idx = None
    for i, obj in enumerate(all_items):
        if obj.id == item_id:
            idx = i
            break
    if idx is None:
        raise HTTPException(404)

    swap_idx = idx - 1 if direction == "up" else idx + 1
    if swap_idx < 0 or swap_idx >= len(all_items):
        raise HTTPException(400, "Ya está al extremo")

    # Swap positions
    item.position, all_items[swap_idx].position = all_items[swap_idx].position, item.position
    db.commit()
    return {"ok": True}


@app.delete("/api/admin/{entity}/{item_id}")
def admin_delete(entity: str, item_id: int, db: Session = Depends(get_db)):
    if entity == "equipos":
        obj = db.query(EquipmentCategory).filter(EquipmentCategory.id == item_id).first()
    elif entity == "subequipos":
        obj = db.query(EquipmentSubitem).filter(EquipmentSubitem.id == item_id).first()
    else:
        model = ADMIN_MODELS.get(entity)
        if not model: raise HTTPException(400)
        obj = db.query(model).filter(model.id == item_id).first()
    if not obj: raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ─── Auto-scheduler for daily reports ──────────────────────────────────────
#
# Uncomment the start_scheduler() call below and set reload=False in run.py
# to enable automatic daily report generation at SCHEDULE_HOUR:00.
#
# import threading
# import time as time_module
#
# SCHEDULE_HOUR = 6  # 6:00 AM
# SCHEDULE_MINUTE = 0
#
#
# def _get_db_session():
#     from .database import SessionLocal as SL
#     return SL()
#
#
# def _auto_generate():
#     from datetime import timedelta
#     yesterday = (datetime.now() - timedelta(days=1)).date()
#     fname = f"Reporte_Diario_{yesterday.isoformat()}.xlsx"
#     fpath = os.path.join(REPORTS_DIR, fname)
#     if os.path.exists(fpath):
#         return
#     db = _get_db_session()
#     try:
#         reports = db.query(Report).options(
#             joinedload(Report.worker), joinedload(Report.entries)
#         ).filter(Report.date == yesterday).all()
#         if not reports:
#             return
#         grouped = {}
#         for rp in reports:
#             group = rp.group_name
#             shift = rp.shift
#             grouped.setdefault(group, {}).setdefault(shift, []).append({
#                 "id": rp.id, "date": rp.date, "shift": shift, "group_name": group,
#                 "collaborators_trackless": rp.collaborators_trackless,
#                 "collaborators_convencional": rp.collaborators_convencional,
#                 "collaborators_electrico": rp.collaborators_electrico,
#                 "entries": [{"macroprocess": e.macroprocess, "work_type": e.work_type, "work_subtype": e.work_subtype, "action": e.action, "description": e.description, "level": e.level, "location": e.location, "start_time_int": e.start_time_int, "end_time_int": e.end_time_int, "duration": e.duration, "equipment": e.equipment, "horometer_motor": e.horometer_motor, "horometer_motor_jumbo": e.horometer_motor_jumbo, "horometer_motor_volquetes": e.horometer_motor_volquetes, "horometer_electric": e.horometer_electric, "horometer_percussion": e.horometer_percussion, "kilometer": e.kilometer} for e in rp.entries],
#             })
#         generate_daily_report(yesterday, grouped)
#     except Exception as exc:
#         print(f"[Scheduler] Error generating daily report: {exc}")
#     finally:
#         db.close()
#
#
# def _scheduler_loop():
#     while True:
#         now = datetime.now()
#         if now.hour == SCHEDULE_HOUR and now.minute == SCHEDULE_MINUTE:
#             _auto_generate()
#             time_module.sleep(61)
#         time_module.sleep(55)
#
#
# def start_scheduler():
#     t = threading.Thread(target=_scheduler_loop, daemon=True)
#     t.start()
#
#
# # To enable auto-scheduling, uncomment the next line and set reload=False in run.py:
# # start_scheduler()
